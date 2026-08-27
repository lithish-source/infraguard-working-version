"""Image preprocessing pipeline for damage photos.

Steps:
  1. Load image (file path / bytes / PIL.Image / numpy array)
  2. Convert to RGB
  3. Resize to a fixed working resolution while preserving aspect via padding
  4. Denoise (light bilateral filter)
  5. CLAHE contrast enhancement
  6. Optional grayscale / edge outputs for feature extraction
"""
from __future__ import annotations

import io
from typing import Optional, Tuple, Union

import cv2
import numpy as np
from PIL import Image

ImageInput = Union[str, bytes, Image.Image, np.ndarray]


def load_image(source: ImageInput) -> np.ndarray:
    """Load image from path, bytes, PIL.Image or numpy array."""
    if isinstance(source, np.ndarray):
        return source.copy()
    if isinstance(source, Image.Image):
        return np.array(source.convert("RGB"))
    if isinstance(source, (bytes, bytearray)):
        arr = np.frombuffer(source, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Cannot decode image bytes")
        return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    if isinstance(source, str):
        img = cv2.imread(source, cv2.IMREAD_COLOR)
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {source}")
        return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    raise TypeError(f"Unsupported image source type: {type(source)}")


def resize_with_pad(
    image: np.ndarray,
    target_size: Tuple[int, int] = (256, 256),
    pad_color: Tuple[int, int, int] = (0, 0, 0),
) -> np.ndarray:
    """Resize while keeping aspect ratio, padding the remainder."""
    th, tw = target_size
    h, w = image.shape[:2]
    scale = min(tw / w, th / h)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    canvas = np.full((th, tw, 3), pad_color, dtype=np.uint8)
    x_off = (tw - new_w) // 2
    y_off = (th - new_h) // 2
    canvas[y_off:y_off + new_h, x_off:x_off + new_w] = resized
    return canvas


def denoise(image: np.ndarray) -> np.ndarray:
    """Light bilateral filtering — preserves edges."""
    return cv2.bilateralFilter(image, d=5, sigmaColor=50, sigmaSpace=50)


def clahe_enhance(image: np.ndarray, clip_limit: float = 2.0, tile: int = 8) -> np.ndarray:
    """Apply CLAHE on the L channel of LAB."""
    lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile, tile))
    l = clahe.apply(l)
    merged = cv2.merge((l, a, b))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2RGB)


def to_grayscale(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)


def detect_edges(gray: np.ndarray) -> np.ndarray:
    return cv2.Canny(gray, 50, 150)


class ImagePreprocessor:
    """End-to-end preprocessing pipeline producing multiple views."""

    def __init__(self, target_size: Tuple[int, int] = (256, 256)):
        self.target_size = target_size

    def process(self, source: ImageInput) -> dict:
        raw = load_image(source)
        rgb = resize_with_pad(raw, self.target_size)
        denoised = denoise(rgb)
        enhanced = clahe_enhance(denoised)
        gray = to_grayscale(enhanced)
        edges = detect_edges(gray)

        return {
            "rgb": rgb,
            "enhanced": enhanced,
            "gray": gray,
            "edges": edges,
            "shape": rgb.shape[:2],
        }

    def process_to_bytes(self, source: ImageInput, fmt: str = "PNG") -> bytes:
        """Return processed RGB image as encoded bytes (for storage/debugging)."""
        views = self.process(source)
        img = Image.fromarray(views["enhanced"])
        buf = io.BytesIO()
        img.save(buf, format=fmt)
        return buf.getvalue()
