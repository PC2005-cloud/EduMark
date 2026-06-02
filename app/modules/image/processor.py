import logging
from io import BytesIO
from PIL import Image, ImageEnhance

logger = logging.getLogger(__name__)

def preprocess(image_bytes: bytes, jpeg_quality: int = 85) -> bytes:
    """
    轻度增强图像用于 OCR 识别，同时保持原始格式并控制输出体积

    Args:
        image_bytes: 原始图片字节
        jpeg_quality: 当原始格式为 JPEG 时的保存质量 (1-100)，默认 85

    Returns:
        处理后的图片字节（格式与原始图片相同，JPEG 会按指定质量压缩）
    """
    try:
        # 打开图片
        img = Image.open(BytesIO(image_bytes))
        original_format = img.format  # 例如 'JPEG', 'PNG', 'GIF'

        # 轻度增强
        img = ImageEnhance.Contrast(img).enhance(1.2)
        img = ImageEnhance.Sharpness(img).enhance(1.1)

        # 准备输出缓冲区
        buf = BytesIO()

        # 根据原始格式决定保存参数
        if original_format and original_format.upper() in ('JPEG', 'JPG'):
            # JPEG: 使用指定质量并优化
            img.save(buf, format='JPEG', quality=jpeg_quality, optimize=True)
            logger.info(
                "图片增强完成: %d -> %d bytes (JPEG, quality=%d)",
                len(image_bytes), buf.tell(), jpeg_quality
            )
        else:
            # PNG / GIF / BMP 等：保持原格式（可能体积较大）
            # 如果担心体积过大，可以统一转为 JPEG（但会丢失透明度）
            # 例如: img.save(buf, format='JPEG', quality=85)
            img.save(buf, format=original_format or 'PNG')
            logger.info(
                "图片增强完成: %d -> %d bytes (format=%s)",
                len(image_bytes), buf.tell(), original_format
            )

        return buf.getvalue()

    except Exception as e:
        logger.warning("图片增强失败, 使用原图: %s", e)
        return image_bytes