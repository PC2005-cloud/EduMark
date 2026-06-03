import base64
import logging
from dataclasses import dataclass

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class RecognizeResult:
    question: str = ""
    answer: str = ""
    type: str = ""
    bbox: list[float] | None = None


@dataclass
class GradeResult:
    text: str
    score: str | None = None
    result: str | None = None
    comment: str | None = None
    analysis: str | None = None


class BailianClient:
    def __init__(self):
        self._api_key = settings.BAILIAN_API_KEY
        self._base = settings.BAILIAN_API_BASE.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        logger.info("百炼客户端初始化: base=%s", self._base)

    def recognize_question(self, images: list[bytes], model: str = "qwen-vl-plus") -> list[RecognizeResult]:
        logger.info("视觉模型识别题目: model=%s 图片数=%d", model, len(images))
        all_items = []
        for img_bytes in images:
            b64 = base64.b64encode(img_bytes).decode()
            messages = [{
    "role": "user",
    "content": [
        {"image": f"data:image/jpeg;base64,{b64}"},
        {"text": "请识别这张作业图片中的所有题目。要求：\n1. 每道题必须包含：题目文本（选择题需包含所有选项）、学生答案、题型（选择题/填空题/计算题/解答题）、以及该题在图片中的位置信息。\n2. 位置信息用矩形边界框表示，格式为 [x1, y1, x2, y2]，取值范围 0~1000（相对于图片宽度和高度的千分比）。\n3. 对于一道题内有多个填空的情况，请合并为一道题输出，不要拆分成多道。\n4. 按以下 JSON 格式返回，不要包含任何额外解释或标记：\n[{\"question\": \"<题目文本>\", \"answer\": \"<学生答案>\", \"type\": \"选择题/填空题/计算题/解答题\", \"bbox\": [x1, y1, x2, y2]}]"},
    ],
}]
            text = self._call_multimodal(messages, model)
            logger.info("百炼原始返回: %s", text)
            items = self._parse_recognize(text)
            all_items.extend(items)
        logger.info("题目识别完成: 题目数=%d", len(all_items))
        return all_items

    def grade_question(self, question: str, student_answer: str,
                       knowledge_chunks: list[str] | None = None,
                       model: str = "qwen-plus") -> GradeResult:
        logger.info("批改题目: model=%s question=%s answer=%s chunks=%d",
                     model, question[:30], student_answer[:20],
                     len(knowledge_chunks) if knowledge_chunks else 0)
        system_prompt = (
            "你是作业批改老师。满分10分，结果：correct/wrong/partial。\n"
            "输出格式：得分：\n结果：\n评语：\n解题分析：\n\n"
            "评语：只点评学生答案（对错、亮点、错误点），不写完整解法。\n"
            "解题分析：仅当结果≠correct时，写出正确解答过程；结果=correct时留空。"
        )
        user_content = f"题目：{question}\n学生答案：{student_answer}"
        if knowledge_chunks:
            ctx = "\n".join(f"{i+1}. {c}" for i, c in enumerate(knowledge_chunks))
            user_content = f"参考知识：\n{ctx}\n{user_content}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        text = self._call_text(messages, model)
        result = self._parse_grade(text)
        logger.info("批改完成: score=%s result=%s", result.score, result.result)
        return result

    def embed(self, texts: list[str], model: str | None = None,
              dimensions: int = 1536) -> list[list[float]]:
        model = model or settings.BAILIAN_EMBED
        logger.info("向量化: model=%s texts=%d条 dimensions=%d", model, len(texts), dimensions)
        batch_size = 25
        url = f"{self._base}/services/embeddings/text-embedding/text-embedding"
        all_vecs = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            body = {"model": model, "input": {"texts": batch}}
            if dimensions:
                body["parameters"] = {"dimension": dimensions}
            logger.debug("向量化批次: %d/%d size=%d", i // batch_size + 1,
                         (len(texts) + batch_size - 1) // batch_size, len(batch))
            resp = httpx.post(url, headers=self._headers, json=body, timeout=30)
            resp.raise_for_status()
            body = resp.json()
            all_vecs.extend(item["embedding"] for item in body["output"]["embeddings"])
        logger.info("向量化完成: %d条 维度=%d", len(all_vecs), len(all_vecs[0]) if all_vecs else 0)
        return all_vecs

    def understand_image(self, image_bytes: bytes, prompt: str = "请详细描述这张图片的内容",
                         model: str = "qwen-vl-plus") -> str:
        logger.info("图片理解: model=%s size=%d", model, len(image_bytes))
        b64 = base64.b64encode(image_bytes).decode()
        messages = [{
            "role": "user",
            "content": [
                {"image": f"data:image/jpeg;base64,{b64}"},
                {"text": prompt},
            ],
        }]
        text = self._call_multimodal(messages, model)
        logger.info("图片理解完成: length=%d", len(text))
        return text

    # ==================== 内部 ====================

    def _call_text(self, messages: list, model: str) -> str:
        url = f"{self._base}/services/aigc/text-generation/generation"
        body = {
            "model": model,
            "input": {"messages": messages},
            "parameters": {"result_format": "message"},
        }
        resp = httpx.post(url, headers=self._headers, json=body, timeout=120)
        resp.raise_for_status()
        result = resp.json()
        text = result["output"]["choices"][0]["message"]["content"]
        logger.debug("百炼文本返回: length=%d preview=%s", len(text), text[:100])
        return text

    def _call_multimodal(self, messages: list, model: str) -> str:
        url = f"{self._base}/services/aigc/multimodal-generation/generation"
        body = {
            "model": model,
            "input": {"messages": messages},
            "parameters": {"result_format": "message"},
        }
        resp = httpx.post(url, headers=self._headers, json=body, timeout=120)
        resp.raise_for_status()
        result = resp.json()
        content = result["output"]["choices"][0]["message"]["content"]
        content = content[0]["text"] if isinstance(content, list) else content
        logger.debug("百炼多模态返回: length=%d", len(content))
        return content

    @staticmethod
    def _parse_recognize(text: str) -> list[RecognizeResult]:
        import json
        text = text.strip()
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            text = text[start:end + 1]
        try:
            raw = json.loads(text)
            items = []
            for r in raw if isinstance(raw, list) else [raw]:
                items.append(RecognizeResult(
                    question=r.get("question", r.get("题目", "")),
                    answer=r.get("answer", r.get("学生答案", "")),
                    type=r.get("type", r.get("题目类型", "")),
                    bbox=r.get("bbox"),
                ))
            logger.debug("解析识别结果: %d 题", len(items))
            return items
        except json.JSONDecodeError as e:
            logger.warning("JSON 解析失败: %s", e)
            return []

    @staticmethod
    def _parse_grade(text: str) -> GradeResult:
        result = GradeResult(text=text)
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("得分") and "：" in line:
                result.score = line.split("：")[-1].strip()
            elif line.startswith("结果") and "：" in line:
                result.result = line.split("：")[-1].strip()
            elif line.startswith("评语") and "：" in line:
                result.comment = line.split("：")[-1].strip()
            elif line.startswith("解题分析") and "：" in line:
                result.analysis = line.split("：")[-1].strip()
        logger.debug("解析批改结果: score=%s result=%s", result.score, result.result)
        return result


bailian = BailianClient()
