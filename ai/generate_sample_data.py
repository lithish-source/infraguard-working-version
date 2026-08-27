"""Generate a synthetic dataset for training the severity classifier.

Creates synthetic 'image' features that simulate damage characteristics
for each severity level, then trains a RandomForest classifier.
"""
from __future__ import annotations

import os
import random
from typing import Tuple

import numpy as np
import joblib

from ai.feature_extraction import FEATURE_NAMES


# Per-severity base characteristics (mean, std) for each feature
SEVERITY_PROFILES = {
    "Low": {
        "edge_density": (0.04, 0.02),
        "dark_pixel_ratio": (0.05, 0.03),
        "texture_variance": (400.0, 100.0),
        "crack_length": (100.0, 80.0),
        "damage_area_ratio": (0.04, 0.02),
        "mean_r": (160.0, 20.0),
        "mean_g": (160.0, 20.0),
        "mean_b": (160.0, 20.0),
        "std_r": (30.0, 10.0),
        "std_g": (30.0, 10.0),
        "std_b": (30.0, 10.0),
        "mean_saturation": (60.0, 20.0),
        "mean_value": (160.0, 20.0),
    },
    "Moderate": {
        "edge_density": (0.12, 0.04),
        "dark_pixel_ratio": (0.15, 0.05),
        "texture_variance": (900.0, 200.0),
        "crack_length": (500.0, 200.0),
        "damage_area_ratio": (0.15, 0.05),
        "mean_r": (140.0, 25.0),
        "mean_g": (130.0, 25.0),
        "mean_b": (120.0, 25.0),
        "std_r": (50.0, 15.0),
        "std_g": (50.0, 15.0),
        "std_b": (50.0, 15.0),
        "mean_saturation": (50.0, 20.0),
        "mean_value": (135.0, 25.0),
    },
    "High": {
        "edge_density": (0.22, 0.05),
        "dark_pixel_ratio": (0.30, 0.07),
        "texture_variance": (1500.0, 300.0),
        "crack_length": (1200.0, 400.0),
        "damage_area_ratio": (0.30, 0.07),
        "mean_r": (110.0, 30.0),
        "mean_g": (100.0, 30.0),
        "mean_b": (90.0, 30.0),
        "std_r": (70.0, 20.0),
        "std_g": (70.0, 20.0),
        "std_b": (70.0, 20.0),
        "mean_saturation": (40.0, 20.0),
        "mean_value": (105.0, 25.0),
    },
    "Critical": {
        "edge_density": (0.35, 0.07),
        "dark_pixel_ratio": (0.50, 0.08),
        "texture_variance": (2200.0, 400.0),
        "crack_length": (2200.0, 600.0),
        "damage_area_ratio": (0.45, 0.08),
        "mean_r": (80.0, 25.0),
        "mean_g": (70.0, 25.0),
        "mean_b": (60.0, 25.0),
        "std_r": (85.0, 20.0),
        "std_g": (85.0, 20.0),
        "std_b": (85.0, 20.0),
        "mean_saturation": (30.0, 15.0),
        "mean_value": (75.0, 25.0),
    },
}

LABELS = ["Low", "Moderate", "High", "Critical"]


def generate_samples(n_per_class: int = 200, seed: int = 42) -> Tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    X, y = [], []
    for label in LABELS:
        prof = SEVERITY_PROFILES[label]
        for _ in range(n_per_class):
            row = [max(0.0, rng.normal(mu, sd)) for mu, sd in (prof[k] for k in FEATURE_NAMES)]
            X.append(row)
            y.append(label)
    X = np.array(X, dtype=np.float32)
    y = np.array(y)
    # Shuffle
    idx = rng.permutation(len(X))
    return X[idx], y[idx]


def generate_sample_images(output_dir: str, n_per_class: int = 5, seed: int = 7) -> None:
    """Save synthetic 'damage' PNGs for demo purposes."""
    import cv2

    os.makedirs(output_dir, exist_ok=True)
    rng = np.random.default_rng(seed)
    for label in LABELS:
        prof = SEVERITY_PROFILES[label]
        for i in range(n_per_class):
            img = np.zeros((256, 256, 3), dtype=np.uint8)
            base_color = (
                int(max(0, min(255, rng.normal(prof["mean_b"][0], prof["mean_b"][1])))),
                int(max(0, min(255, rng.normal(prof["mean_g"][0], prof["mean_g"][1])))),
                int(max(0, min(255, rng.normal(prof["mean_r"][0], prof["mean_r"][1])))),
            )
            img[:] = base_color

            # Add random "cracks" — black lines
            n_cracks = int(rng.normal(prof["crack_length"][0] / 100.0, 5))
            n_cracks = max(1, n_cracks)
            for _ in range(n_cracks):
                pt1 = (int(rng.integers(0, 256)), int(rng.integers(0, 256)))
                pt2 = (pt1[0] + int(rng.integers(-50, 50)), pt1[1] + int(rng.integers(-50, 50)))
                cv2.line(img, pt1, pt2, (0, 0, 0), max(1, int(rng.integers(1, 4))))

            # Add dark patches
            n_patches = int(rng.normal(prof["damage_area_ratio"][0] * 20, 3))
            n_patches = max(0, n_patches)
            for _ in range(n_patches):
                cx, cy = int(rng.integers(20, 236)), int(rng.integers(20, 236))
                r = int(rng.integers(8, 30))
                cv2.circle(img, (cx, cy), r, (int(base_color[0] * 0.4),
                                              int(base_color[1] * 0.4),
                                              int(base_color[2] * 0.4)), -1)

            # Add noise
            noise = rng.normal(0, 25, img.shape).astype(np.int16)
            img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

            fname = f"{label.lower()}_{i:03d}.png"
            cv2.imwrite(os.path.join(output_dir, fname), img)
    print(f"[generate_sample_data] Wrote {n_per_class * len(LABELS)} sample images to {output_dir}")


if __name__ == "__main__":
    # When run as a script: generate images + dataset
    out_images = os.path.join(os.path.dirname(__file__), "data", "sample_images")
    generate_sample_images(out_images)
    X, y = generate_samples(n_per_class=300)
    np.savez(os.path.join(os.path.dirname(__file__), "data", "dataset.npz"), X=X, y=y)
    print(f"[generate_sample_data] Wrote dataset.npz with {len(X)} samples")
