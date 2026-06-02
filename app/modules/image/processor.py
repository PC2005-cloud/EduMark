import logging
from io import BytesIO

from PIL import Image, ImageEnhance

logger = logging.getLogger(__name__)


def preprocess(image_bytes: bytes) -> bytes:
    """轻度增强图像用于 OCR 识别"""
    try:
        img = Image.open(BytesIO(image_bytes))
        img = ImageEnhance.Contrast(img).enhance(1.2)
        img = ImageEnhance.Sharpness(img).enhance(1.1)
        buf = BytesIO()
        img.save(buf, "PNG")
        result = buf.getvalue()
        logger.info("图片增强完成: %d -> %d bytes", len(image_bytes), len(result))
        return result
    except Exception as e:
        logger.warning("图片增强失败, 使用原图: %s", e)
        return image_bytes
