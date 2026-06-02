import json
import logging
from enum import Enum
from io import BytesIO
from typing import Optional
from zipfile import ZipFile

import httpx
from pypdf import PdfReader, PdfWriter

from app.core.config import settings
from app.clients.bailian import bailian

logger = logging.getLogger(__name__)

MAX_PAGE = 200
MAX_SIZE = 200 * 1024 * 1024
BLOCK_MIN_SIZE = 500
BLOCK_MAX_SIZE = 2000

SUPPORTED_TYPES = [
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
]


# ==================== 数据类 ====================

class TaskState(Enum):
    WAITING_FILE = ("waiting-file", "等待文件上传")
    PENDING = ("pending", "排队中")
    RUNNING = ("running", "正在解析")
    CONVERTING = ("converting", "格式转换中")
    DONE = ("done", "完成")
    FAILED = ("failed", "失败")
    UNKNOWN = ("unknown", "未知")

    def __init__(self, code: str, msg: str):
        self.code = code
        self.msg = msg

    @staticmethod
    def from_code(code: str) -> "TaskState":
        for s in TaskState:
            if s.code == code:
                return s
        return TaskState.UNKNOWN


class ContentType(Enum):
    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"
    HEADER = "header"
    PAGE_NUMBER = "page_number"
    LIST = "list"
    EQUATION = "equation"


class ContentItem:
    def __init__(self):
        self.type: ContentType = ContentType.TEXT
        self.text: Optional[str] = None
        self.text_level: Optional[int] = None
        self.bbox: list[int] = []
        self.page_idx: int = 0
        self.img_path: Optional[str] = None
        self.image_caption: list[str] = []
        self.image_footnote: list[str] = []
        self.sub_type: Optional[str] = None
        self.list_items: list[str] = []
        self.text_format: Optional[str] = None
        self.table_caption: list[str] = []
        self.table_footnote: list[str] = []
        self.table_body: Optional[str] = None

    @staticmethod
    def from_dict(d: dict) -> "ContentItem":
        item = ContentItem()
        raw_type = d.get("type", "text")
        try:
            item.type = ContentType(raw_type)
        except ValueError:
            item.type = ContentType.TEXT
        item.text = d.get("text")
        item.text_level = d.get("text_level")
        item.bbox = d.get("bbox", [])
        item.page_idx = d.get("page_idx", 0)
        item.img_path = d.get("img_path")
        item.image_caption = d.get("image_caption", [])
        item.image_footnote = d.get("image_footnote", [])
        item.sub_type = d.get("sub_type")
        item.list_items = d.get("list_items", [])
        item.text_format = d.get("text_format")
        item.table_caption = d.get("table_caption", [])
        item.table_footnote = d.get("table_footnote", [])
        item.table_body = d.get("table_body")
        return item

    @staticmethod
    def copy_to_text(item: "ContentItem") -> "ContentItem":
        new_item = ContentItem()
        new_item.type = ContentType.TEXT
        new_item.bbox = item.bbox
        new_item.page_idx = item.page_idx
        return new_item


class PollingResult:
    def __init__(self):
        self.success: bool = False
        self.info: str = ""
        self.zip_urls: list[str] = []


# ==================== 客户端 ====================

class MineruClient:
    def __init__(self):
        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.MINERU_KEY}",
        }
        self._base = settings.MINERU_URL.rstrip("/")
        self._file_urls_url = f"{self._base}/file-urls/batch"
        self._extract_results_url = f"{self._base}/extract-results/batch"
        logger.info("MinerU 客户端初始化: base=%s", self._base)

    def upload_and_parse(self, file_data: bytes, filename: str,
                         content_type: str | None = None) -> str:
        logger.info("上传并解析: filename=%s size=%d", filename, len(file_data))
        files = self._validate_and_split(file_data, filename, content_type)
        batch_id, upload_urls = self._apply_upload_urls(files)
        self._upload_files(files, upload_urls)
        logger.info("上传解析完成: batch_id=%s 文件数=%d", batch_id, len(files))
        return batch_id

    def get_zip_urls(self, batch_id: str) -> PollingResult:
        logger.info("查询解析结果: batch_id=%s", batch_id)
        url = f"{self._extract_results_url}/{batch_id}"
        resp = httpx.get(url, headers=self._headers, timeout=30)
        resp.raise_for_status()
        body = resp.json()
        if body.get("code") != 0:
            logger.error("查询解析结果失败: code=%s msg=%s", body.get("code"), body.get("msg"))
            raise RuntimeError(f"查询解析结果失败: {body.get('msg')}")

        data = body.get("data", {})
        extract_result = data.get("extract_result", [])

        lines = []
        states = []
        for item in extract_result:
            state = item.get("state")
            file_name = item.get("file_name", "")
            progress = item.get("extract_progress")
            msg = TaskState.from_code(state).msg if state else "未知"
            if progress:
                msg += f" --- {progress.get('total_pages', '?')}/{progress.get('extracted_pages', '?')}"
            lines.append(f"{file_name}: {msg}")
            states.append(TaskState.from_code(state) if state else TaskState.FAILED)

        result = PollingResult()
        result.info = "\n".join(lines)

        for s in states:
            if s == TaskState.FAILED:
                logger.error("解析失败: batch_id=%s", batch_id)
                raise RuntimeError(f"解析失败: {data}")
            if s != TaskState.DONE:
                result.success = False
                logger.debug("解析进行中: batch_id=%s info=%s", batch_id, result.info)
                return result

        result.success = True
        result.zip_urls = [item.get("full_zip_url") for item in extract_result if item.get("full_zip_url")]
        logger.info("解析完成: batch_id=%s zip_urls=%s", batch_id, result.zip_urls)
        return result

    def handle_parse_result(self, zip_urls: list[str],
                            process_images: bool = True) -> list[ContentItem]:
        logger.info("处理解析结果: %d 个 zip, process_images=%s", len(zip_urls), process_images)
        all_content = []
        all_pictures = {}

        for i, zip_url in enumerate(zip_urls):
            logger.debug("下载处理 ZIP[%d]: %s", i, zip_url)
            zip_data = self._download_zip(zip_url)
            content = self._parse_content_list(zip_data)
            pictures = self._parse_images(zip_data)

            for item in content:
                item.page_idx = item.page_idx + 1 + i * MAX_PAGE

            logger.debug("ZIP[%d] 内容: %d 项, %d 张图片", i, len(content), len(pictures))
            all_content.extend(content)
            all_pictures.update(pictures)

        return self._handle_content(all_content, all_pictures, process_images)

    # ==================== 校验与分割 ====================

    def _get_pdf_page_count(self, file_data: bytes) -> int:
        reader = PdfReader(BytesIO(file_data))
        return len(reader.pages)

    def _split_pdf(self, file_data: bytes, filename: str) -> list[tuple[bytes, str]]:
        reader = PdfReader(BytesIO(file_data))
        total = len(reader.pages)
        logger.info("分割PDF: %s %d 页, 每 %d 页一份", filename, total, MAX_PAGE)

        name = filename.rsplit(".", 1)[0]
        suffix = filename.rsplit(".", 1)[1]
        files = []

        for i in range(0, total, MAX_PAGE):
            writer = PdfWriter()
            end = min(i + MAX_PAGE, total)
            for page_num in range(i, end):
                writer.add_page(reader.pages[page_num])
            buf = BytesIO()
            writer.write(buf)
            split_name = f"{name}(大文件分片)-{i // MAX_PAGE + 1}.{suffix}"
            files.append((buf.getvalue(), split_name))
            writer.close()
            logger.debug("分割块 %d: 页 %d-%d", i // MAX_PAGE + 1, i + 1, end)

        return files

    def _validate_and_split(self, file_data: bytes, filename: str,
                            content_type: str | None = None) -> list[tuple[bytes, str]]:
        size_mb = len(file_data) / 1024 / 1024
        logger.info("校验文件: %s size=%.1fMB", filename, size_mb)
        if len(file_data) > MAX_SIZE:
            logger.error("文件过大: %.1fMB > %dMB", size_mb, MAX_SIZE // 1024 // 1024)
            raise ValueError(f"文件大小超过 {MAX_SIZE // 1024 // 1024}MB")

        if filename.lower().endswith(".pdf"):
            pages = self._get_pdf_page_count(file_data)
            logger.info("PDF 页数: %d, 上限: %d 页", pages, MAX_PAGE)
            if pages > MAX_PAGE:
                logger.info("PDF 超过 %d 页, 开始分割", MAX_PAGE)
                return self._split_pdf(file_data, filename)
            logger.debug("PDF 未超过上限, 直接上传")
        else:
            logger.debug("非 PDF 文件, 跳过页数检查: %s", filename)

        return [(file_data, filename)]

    # ==================== 内容处理 ====================

    def _handle_content(self, content: list[ContentItem],
                        pictures: dict[str, bytes],
                        process_images: bool = True) -> list[ContentItem]:
        result = []
        pending_images = []
        filtered = 0

        for item in content:
            if item.type == ContentType.PAGE_NUMBER or item.type == ContentType.HEADER:
                filtered += 1
                continue

            if item.type == ContentType.IMAGE:
                pending_images.append(item)
                continue

            if item.type == ContentType.TEXT or item.type == ContentType.EQUATION:
                text = item.text or ""
                if len(text) > BLOCK_MAX_SIZE:
                    logger.debug("文本超长: %d 字, 分块处理", len(text))
                    for chunk in self._split_text(text):
                        new_item = ContentItem.copy_to_text(item)
                        new_item.text = chunk
                        result.append(new_item)
                else:
                    result.append(item)
                continue

            if item.type == ContentType.TABLE:
                body = item.table_body or ""
                if not body.strip():
                    logger.debug("表格内容为空, 跳过")
                    continue
                caption = ", ".join(item.table_caption)
                footnote = ", ".join(item.table_footnote)
                chunks = self._split_text(body)
                for chunk in chunks:
                    new_item = ContentItem.copy_to_text(item)
                    texts = []
                    if caption:
                        texts.append(f"表格标题:{caption}")
                    texts.append(f"表格内容:{chunk}")
                    if footnote:
                        texts.append(f"表格脚注:{footnote}")
                    new_item.text = "\n".join(texts)
                    result.append(new_item)
                logger.debug("表格处理: body=%d 字 → %d 块", len(body), len(chunks))
                continue

            if item.type == ContentType.LIST:
                join_text = "".join(item.list_items)
                if not join_text.strip():
                    logger.debug("列表内容为空, 跳过")
                    continue
                chunks = self._split_text(join_text)
                for chunk in chunks:
                    new_item = ContentItem.copy_to_text(item)
                    new_item.text = chunk
                    result.append(new_item)
                logger.debug("列表处理: %d 项 → %d 块", len(item.list_items), len(chunks))
                continue

            result.append(item)

        logger.debug("内容处理: 原始 %d 项, 过滤 %d 项(PAGE_NUMBER/HEADER), 剩余 %d 项, 待处理图片 %d 张",
                     len(content), filtered, len(result), len(pending_images))

        if process_images and pending_images:
            logger.info("开始处理图片: %d 张", len(pending_images))
            processed = self._process_images(pending_images, pictures)
            result.extend(processed)
        else:
            result.extend(pending_images)

        return self._merge_adjacent_text(result)

    def _split_text(self, text: str) -> list[str]:
        if len(text) <= BLOCK_MAX_SIZE:
            return [text]
        chunks = []
        for i in range(0, len(text), BLOCK_MAX_SIZE):
            chunks.append(text[i:i + BLOCK_MAX_SIZE])
        logger.debug("文本分块: %d 字 → %d 块 (上限 %d)", len(text), len(chunks), BLOCK_MAX_SIZE)
        return chunks

    def _merge_adjacent_text(self, items: list[ContentItem]) -> list[ContentItem]:
        merged = []
        merged_count = 0
        for item in items:
            if item.type != ContentType.TEXT:
                merged.append(item)
                continue
            if not merged or merged[-1].type != ContentType.TEXT or \
               merged[-1].page_idx != item.page_idx:
                merged.append(item)
                continue
            last = merged[-1]
            if len(last.text or "") < BLOCK_MIN_SIZE:
                old_len = len(last.text or "")
                last.text = (last.text or "") + (item.text or "")
                merged_count += 1
                logger.debug("合并文本: page=%d %d字 + %d字 = %d字",
                             item.page_idx, old_len, len(item.text or ""), len(last.text))
            else:
                merged.append(item)
        if merged_count:
            logger.info("相邻文本合并: %d 项合并为 %d 项", merged_count, len(merged))
        else:
            logger.debug("无需合并文本, 最终 %d 项", len(merged))
        return merged

    # ==================== 上传与下载 ====================

    def _apply_upload_urls(self, files: list[tuple[bytes, str]]) -> tuple[str, list[str]]:
        file_list = []
        for _, filename in files:
            name_parts = filename.rsplit(".", 1)
            file_list.append({
                "name": filename,
                "data_id": name_parts[0] if len(name_parts) > 1 else filename,
                "is_ocr": True,
            })

        payload = {"files": file_list, "model_version": "vlm"}
        logger.debug("申请上传地址: %d 个文件", len(file_list))
        resp = httpx.post(self._file_urls_url, headers=self._headers, json=payload, timeout=30)
        resp.raise_for_status()
        body = resp.json()
        if body.get("code") != 0:
            logger.error("申请上传地址失败: %s", body.get("msg"))
            raise RuntimeError(f"申请上传地址失败: {body.get('msg')}")

        data = body.get("data", {})
        logger.info("申请上传地址成功: batch_id=%s urls=%d", data.get("batch_id"), len(data.get("file_urls", [])))
        return data["batch_id"], data["file_urls"]

    def _upload_files(self, files: list[tuple[bytes, str]], upload_urls: list[str]):
        for (file_data, filename), upload_url in zip(files, upload_urls):
            logger.info("上传文件: %s size=%d", filename, len(file_data))
            resp = httpx.put(upload_url, content=file_data, timeout=120)
            resp.raise_for_status()
            logger.info("上传成功: %s", filename)

    def _download_zip(self, zip_url: str) -> bytes:
        logger.debug("下载 ZIP: %s", zip_url)
        resp = httpx.get(zip_url, timeout=120)
        resp.raise_for_status()
        logger.debug("ZIP 下载完成: %d bytes", len(resp.content))
        return resp.content

    def _parse_content_list(self, zip_data: bytes) -> list[ContentItem]:
        logger.debug("解析 content_list")
        with ZipFile(BytesIO(zip_data)) as z:
            for name in z.namelist():
                if name.endswith("_content_list.json"):
                    raw_list = json.loads(z.read(name))
                    items = [ContentItem.from_dict(item) for item in raw_list]
                    logger.debug("content_list 解析完成: %d 项", len(items))
                    return items
        raise FileNotFoundError("ZIP 中未找到 _content_list.json")

    def _parse_images(self, zip_data: bytes) -> dict[str, bytes]:
        pictures = {}
        with ZipFile(BytesIO(zip_data)) as z:
            for name in z.namelist():
                if name.startswith("images/") and not name.endswith("/"):
                    pictures[name] = z.read(name)
        logger.debug("图片提取完成: %d 张", len(pictures))
        return pictures

    def _process_images(self, images: list[ContentItem],
                        pictures: dict[str, bytes]) -> list[ContentItem]:
        logger.info("图片转描述: %d 张", len(images))
        result = []
        for i, item in enumerate(images):
            img_data = pictures.get(item.img_path or "")
            if not img_data:
                logger.warning("图片文件未找到: %s", item.img_path)
                text_item = ContentItem()
                text_item.type = ContentType.TEXT
                text_item.text = "[图片文件未找到]"
                text_item.page_idx = item.page_idx
                result.append(text_item)
                continue

            prompt = "请详细描述这张图片的内容，包括其中的文字、公式、图表等所有信息。"
            logger.info("图片描述[%d/%d]: %s", i + 1, len(images), item.img_path)
            try:
                desc = bailian.understand_image(img_data, prompt)
                text_item = ContentItem()
                text_item.type = ContentType.TEXT
                text_item.text = f"[图片描述] {desc}"
                text_item.page_idx = item.page_idx
                result.append(text_item)
                logger.info("图片描述完成[%d/%d]: %s", i + 1, len(images), item.img_path)
            except Exception as e:
                logger.error("图片描述失败[%d/%d]: %s %s", i + 1, len(images), item.img_path, e)
                text_item = ContentItem()
                text_item.type = ContentType.TEXT
                text_item.text = f"[图片描述失败: {e}]"
                text_item.page_idx = item.page_idx
                result.append(text_item)

        return result


mineru_client = MineruClient()
