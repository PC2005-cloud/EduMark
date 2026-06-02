import json
import logging
from dataclasses import dataclass

from alibabacloud_ocr_api20210707.client import Client
from alibabacloud_ocr_api20210707 import models as ocr_models
from alibabacloud_tea_openapi.models import Config
from alibabacloud_tea_util.models import RuntimeOptions

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class PaperQuestion:
    question_no: str
    x1: int
    y1: int
    x2: int
    y2: int
    text: str | None


@dataclass
class QuestionOcrResult:
    question_text: str
    student_answer: str
    question_type: str


class AliyunOCRClient:
    def __init__(self):
        self._config = Config(
            access_key_id=settings.ALIYUN_ACCESS_KEY_ID,
            access_key_secret=settings.ALIYUN_ACCESS_KEY_SECRET,
            endpoint=settings.ALIYUN_ENDPOINT,
            region_id="cn-hangzhou",
        )
        self._client = Client(self._config)
        self._runtime = RuntimeOptions()
        self._runtime.read_timeout = 60000
        self._runtime.connect_timeout = 30000
        logger.info("阿里云OCR客户端初始化: endpoint=%s", settings.ALIYUN_ENDPOINT)

    def cut_paper(self, image_bytes: bytes, cut_type: str = "question",
                  image_type: str = "photo", subject: str = "default") -> list[PaperQuestion]:
        logger.info("试卷切题: cut_type=%s image_type=%s subject=%s size=%d",
                     cut_type, image_type, subject, len(image_bytes))
        request = ocr_models.RecognizeEduPaperCutRequest(
            cut_type=cut_type,
            image_type=image_type,
            subject=subject,
            body=image_bytes,
        )
        response = self._client.recognize_edu_paper_cut_with_options(request, self._runtime)
        data = self._parse_response_data(response)
        if not data:
            logger.warning("切题未检测到题目")
            return []
        questions = self._extract_questions(data)
        logger.info("切题完成: %d 道题", len(questions))
        return questions

    def recognize_question(self, image_bytes: bytes, need_rotate: bool = True) -> QuestionOcrResult:
        logger.info("题目OCR: need_rotate=%s size=%d", need_rotate, len(image_bytes))
        request = ocr_models.RecognizeEduQuestionOcrRequest(
            need_rotate=need_rotate,
            body=image_bytes,
        )
        response = self._client.recognize_edu_question_ocr_with_options(request, self._runtime)
        data = self._parse_response_data(response)
        if not data:
            logger.warning("题目OCR未识别到内容")
            return QuestionOcrResult(question_text="", student_answer="", question_type="")
        result = self._extract_question_text(data)
        logger.info("题目OCR完成: type=%s text_length=%d", result.question_type, len(result.question_text))
        return result

    # ==================== 内部 ====================

    @staticmethod
    def _parse_response_data(response) -> dict | None:
        if not response or not response.body:
            logger.error("API 返回空响应")
            return None
        body = response.body
        code = getattr(body, "code", None)
        if code is not None and code != "OK":
            logger.error("API 返回错误: code=%s msg=%s", code, getattr(body, "message", ""))
            return None
        data = getattr(body, "data", None) or getattr(vars(body), "Data", None)
        if not data:
            logger.error("API 返回空数据")
            return None
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        if isinstance(data, str):
            data = json.loads(data)
        return data

    @staticmethod
    def _extract_questions(data: dict) -> list[PaperQuestion]:
        questions = []
        page_list = data.get("page_list", [])
        logger.debug("切题原始数据: %d 页", len(page_list))
        for page_idx, page in enumerate(page_list):
            subject_list = page.get("subject_list", [])
            for idx, subject in enumerate(subject_list, 1):
                x = subject.get("x", 0)
                y = subject.get("y", 0)
                width = subject.get("width", 0)
                height = subject.get("height", 0)

                if x == 0 and y == 0 and width == 0 and height == 0:
                    content_list = subject.get("content_list_info", [])
                    if content_list:
                        pos = content_list[0].get("pos", [])
                        if len(pos) >= 4:
                            xs = [p.get("x", 0) for p in pos]
                            ys = [p.get("y", 0) for p in pos]
                            if xs and ys:
                                x = min(xs)
                                y = min(ys)
                                width = max(xs) - x
                                height = max(ys) - y

                text = subject.get("text", "")
                if not text:
                    words = subject.get("prism_wordsInfo", [])
                    text = " ".join(w.get("word", "") for w in words if isinstance(w, dict))

                if x >= 0 and y >= 0 and width > 0 and height > 0:
                    questions.append(PaperQuestion(
                        question_no=str(page_idx * 100 + idx),
                        x1=int(x), y1=int(y),
                        x2=int(x + width), y2=int(y + height),
                        text=text.strip() or None,
                    ))
        return questions

    @staticmethod
    def _extract_question_text(data: dict) -> QuestionOcrResult:
        question_text = (data.get("QuestionText") or data.get("text") or data.get("content", ""))
        student_answer = (data.get("AnswerText") or data.get("answer") or data.get("StudentAnswer", ""))

        prism_words = data.get("prism_wordsInfo", [])
        if isinstance(prism_words, list):
            words = [w.get("word", "") for w in prism_words if isinstance(w, dict)]
            text_from_words = " ".join(words)
            if not question_text:
                question_text = text_from_words
            if not student_answer:
                handwritten = [w.get("word", "") for w in prism_words
                               if isinstance(w, dict) and w.get("recClassify") == 2]
                if handwritten:
                    student_answer = " ".join(handwritten)

        question_type = (data.get("QuestionType") or data.get("question_type") or "")
        if not question_type:
            question_type = AliyunOCRClient._detect_question_type(question_text)

        logger.debug("OCR结果: text_length=%d answer_length=%d type=%s",
                     len(question_text), len(student_answer), question_type)
        return QuestionOcrResult(
            question_text=question_text.strip(),
            student_answer=student_answer.strip(),
            question_type=question_type,
        )

    @staticmethod
    def _detect_question_type(text: str) -> str:
        if not text:
            return "解答题"
        if text.find("A.") >= 0 or text.find("B.") >= 0:
            return "选择题"
        if any(kw in text for kw in ("正确", "错误", "对 ", "错 ")):
            return "判断题"
        if "__" in text or "（  ）" in text or "（ ）" in text or "____" in text:
            return "填空题"
        if any(kw in text for kw in ("计算", "化简", "求值", "解方程")):
            return "计算题"
        return "解答题"


aliyun_ocr = AliyunOCRClient()
