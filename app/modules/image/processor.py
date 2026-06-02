import logging
from typing import Callable

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def _order_points(pts: np.ndarray) -> np.ndarray:
    """将四个点按 左上、右上、右下、左下 排序"""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def correct_perspective(img: np.ndarray) -> np.ndarray:
    """自动检测纸张边缘，透视变换校正倾斜"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 150)

    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        logger.warning("未检测到纸张边缘")
        return img

    largest = max(contours, key=cv2.contourArea)
    peri = cv2.arcLength(largest, True)
    approx = cv2.approxPolyDP(largest, 0.02 * peri, True)

    if len(approx) != 4:
        logger.debug("检测到 %d 个角点，跳过透视校正", len(approx))
        return img

    pts = approx.reshape(4, 2).astype(np.float32)
    rect = _order_points(pts)

    (tl, tr, br, bl) = rect
    w = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
    h = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))

    dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(rect, dst)
    result = cv2.warpPerspective(img, matrix, (w, h))
    logger.info("透视校正完成: %dx%d -> %dx%d", img.shape[1], img.shape[0], w, h)
    return result


def enhance_light(img: np.ndarray) -> np.ndarray:
    """自适应直方图均衡化 + 去阴影"""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    enhanced = cv2.merge([l, a, b])
    result = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

    gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    dilated = cv2.dilate(gray, kernel)
    blurred_bg = cv2.medianBlur(dilated, 21)
    shadow_free = cv2.absdiff(blurred_bg, gray)
    shadow_free = cv2.normalize(shadow_free, None, 0, 255, cv2.NORM_MINMAX)

    result = cv2.cvtColor(shadow_free, cv2.COLOR_GRAY2BGR)
    logger.debug("光照增强完成")
    return result


def binarize(img: np.ndarray) -> np.ndarray:
    """Otsu 二值化"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    result = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
    logger.debug("二值化完成")
    return result


def denoise(img: np.ndarray) -> np.ndarray:
    """中值滤波 + 形态学开闭运算去噪"""
    result = cv2.medianBlur(img, 3)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    result = cv2.morphologyEx(result, cv2.MORPH_OPEN, kernel)
    result = cv2.morphologyEx(result, cv2.MORPH_CLOSE, kernel)
    logger.debug("去噪完成")
    return result


# ==================== 编排 ====================

_ALL_STEPS = [correct_perspective, enhance_light, binarize, denoise]


def preprocess(image_bytes: bytes,
               steps: list[Callable[[np.ndarray], np.ndarray]] | None = None) -> bytes:
    """图像预处理管线

    :param image_bytes: 原始图片字节
    :param steps: 要应用的步骤函数列表，默认全部
    """
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("图片解码失败")

    steps = steps or _ALL_STEPS
    logger.info("预处理开始: size=%dx%d steps=%d", img.shape[1], img.shape[0], len(steps))

    for fn in steps:
        img = fn(img)

    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    result = buf.tobytes()
    logger.info("预处理完成: %d bytes", len(result))
    return result
