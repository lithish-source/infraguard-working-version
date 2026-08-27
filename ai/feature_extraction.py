"""Hand-crafted feature extraction from infrastructure damage images.

Features extracted:
  - Edge density (crack pattern indicator)
  - Mean / std of grayscale (brightness & contrast)
  - Dark pixel ratio (shadow / damage patches)
  - Texture features (LBP-like, simple variance)
  - Color-based features (mean R, G, B; saturation)
  - Contour-based crack length proxy
  - Damage area ratio (thresholded)
"""
from __future__ import annotations

from typing import Dict

import cv2
import numpy as np

from ai.preprocessing import to_grayscale, detect_edges


def _edge_density(edges: np.ndarray) -> float:
    return float(np.count_nonzero(edges)) / float(edges.size + 1e-9)


def _dark_pixel_ratio(gray: np.ndarray, threshold: int = 70) -> float:
    return float(np.count_nonzero(gray < threshold)) / float(gray.size + 1e-9)


def _texture_variance(gray: np.ndarray) -> float:
    return float(np.var(gray))


def _crack_length_proxy(edges: np.ndarray) -> float:
    """Approximate crack length via skeletonized edge count."""
    skeleton = cv2.ximgproc.thinning(edges) if hasattr(cv2, "ximgproc") else edges
    return float(np.count_nonzero(skeleton))


def _damage_area_ratio(gray: np.ndarray, threshold: int = 90) -> float:
    """Ratio of pixels darker than threshold (proxy for damage patches)."""
    return _dark_pixel_ratio(gray, threshold)


def _color_stats(rgb: np.ndarray) -> Dict[str, float]:
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    return {
        "mean_r": float(np.mean(r)),
        "mean_g": float(np.mean(g)),
        "mean_b": float(np.mean(b)),
        "std_r": float(np.std(r)),
        "std_g": float(np.std(g)),
        "std_b": float(np.std(b)),
        "mean_saturation": float(np.mean(hsv[:, :, 1])),
        "mean_value": float(np.mean(hsv[:, :, 2])),
    }


def extract_features(
    rgb: np.ndarray,
    gray: np.ndarray = None,
    edges: np.ndarray = None,
) -> Dict[str, float]:
    """Extract a dictionary of numeric features for severity classification."""
    if gray is None:
        gray = to_grayscale(rgb)
    if edges is None:
        edges = detect_edges(gray)

    feats = {
        "edge_density": _edge_density(edges),
        "dark_pixel_ratio": _dark_pixel_ratio(gray),
        "texture_variance": _texture_variance(gray),
        "crack_length": _crack_length_proxy(edges),
        "damage_area_ratio": _damage_area_ratio(gray),
    }
    feats.update(_color_stats(rgb))
    return feats


FEATURE_NAMES = [
    "edge_density",
    "dark_pixel_ratio",
    "texture_variance",
    "crack_length",
    "damage_area_ratio",
    "mean_r",
    "mean_g",
    "mean_b",
    "std_r",
    "std_g",
    "std_b",
    "mean_saturation",
    "mean_value",
]


def features_to_vector(features: Dict[str, float]) -> np.ndarray:
    return np.array([features.get(name, 0.0) for name in FEATURE_NAMES], dtype=np.float32)
