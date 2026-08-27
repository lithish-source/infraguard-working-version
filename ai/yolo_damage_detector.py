"""YOLO-based road damage detector.

Uses a YOLOv12-small model fine-tuned on the Road Damage Dataset 2022 (RDD2022)
for detecting road surface damage in citizen-uploaded photos.

Classes:
  D00 — Longitudinal Crack
  D10 — Transverse Crack
  D20 — Alligator Crack
  D40 — Pothole
  Repair — Repaired Area

The detector runs inference on an image and returns structured results including
bounding boxes, confidence scores, and a damage summary that feeds into the
severity classification pipeline.
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

import numpy as np

# YOLO damage classes → human-readable labels and severity hints
YOLO_DAMAGE_CLASSES = {
    0: {"code": "D00", "name": "Longitudinal Crack", "severity_hint": "Moderate"},
    1: {"code": "D10", "name": "Transverse Crack", "severity_hint": "Moderate"},
    2: {"code": "D20", "name": "Alligator Crack", "severity_hint": "High"},
    3: {"code": "D40", "name": "Pothole", "severity_hint": "High"},
    4: {"code": "Repair", "name": "Repaired Area", "severity_hint": "Low"},
}

# Mapping from YOLO damage type to InfraGuard damage type
DAMAGE_TYPE_MAP = {
    "D00": "Surface Crack",
    "D10": "Surface Crack",
    "D20": "Structural Damage",
    "D40": "Pothole",
    "Repair": "Repaired Area",
}

# Severity escalation: how each YOLO class shifts the final severity
SEVERITY_SHIFT = {
    "D00": 0,    # no shift — cracks are moderate by default
    "D10": 0,
    "D20": +1,   # alligator cracks push severity up
    "D40": +1,   # potholes push severity up
    "Repair": -1, # repaired areas push severity down
}

# Severity levels for shift computation
_SEVERITY_ORDER = ["Low", "Moderate", "High", "Critical"]


class YOLODamageDetector:
    """Run YOLOv12 inference for road damage detection."""

    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.model_path = model_path
        self._available = False

        if model_path and os.path.exists(model_path):
            try:
                from ultralytics import YOLO
                self.model = YOLO(model_path)
                self._available = True
                print(f"[yolo] Road damage detector loaded from {model_path}")
            except Exception as e:
                print(f"[yolo] Failed to load model: {e}")
                self.model = None

    @property
    def is_available(self) -> bool:
        return self._available and self.model is not None

    def detect(self, image_source, confidence_threshold: float = 0.25) -> Dict:
        """Run damage detection on an image.

        Args:
            image_source: File path (str), numpy array, or PIL Image.
            confidence_threshold: Minimum confidence to include a detection.

        Returns:
            {
                "detections": [...],           # list of individual detections
                "damage_types": [...],         # unique damage type names found
                "max_severity_hint": str,      # highest severity among detections
                "detection_count": int,        # total number of detections
                "damage_area_ratio": float,    # fraction of image area covered by damage
                "suggested_damage_type": str,  # best overall damage type label
                "severity_shift": int,         # how much to shift severity (-1, 0, +1)
                "confidence_avg": float,       # average confidence of detections
            }
        """
        if not self.is_available:
            return self._empty_result()

        try:
            results = self.model(image_source, conf=confidence_threshold, verbose=False)
        except Exception as e:
            print(f"[yolo] Inference failed: {e}")
            return self._empty_result()

        detections = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                cls_info = YOLO_DAMAGE_CLASSES.get(cls_id, {"code": "Unknown", "name": "Unknown"})
                detections.append({
                    "class_id": cls_id,
                    "class_code": cls_info["code"],
                    "class_name": cls_info["name"],
                    "confidence": round(conf, 4),
                    "bbox": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
                    "area_pixels": round((x2 - x1) * (y2 - y1), 1),
                })

        if not detections:
            return self._empty_result()

        # Compute summary stats
        damage_types = list({d["class_code"] for d in detections})
        confidences = [d["confidence"] for d in detections]
        areas = [d["area_pixels"] for d in detections]

        # Pick the most severe damage type
        severity_rank = {"Low": 0, "Moderate": 1, "High": 2, "Critical": 3}
        max_hint = "Low"
        for d in detections:
            hint = YOLO_DAMAGE_CLASSES.get(d["class_id"], {}).get("severity_hint", "Low")
            if severity_rank.get(hint, 0) > severity_rank.get(max_hint, 0):
                max_hint = hint

        # Compute severity shift
        shift = 0
        for code in damage_types:
            s = SEVERITY_SHIFT.get(code, 0)
            if s > shift:
                shift = s
            elif s < shift:
                shift = s

        # Suggested damage type: pick the most confident non-repair detection
        non_repair = [d for d in detections if d["class_code"] != "Repair"]
        if non_repair:
            best = max(non_repair, key=lambda d: d["confidence"])
            suggested_type = DAMAGE_TYPE_MAP.get(best["class_code"], "Structural Damage")
        else:
            suggested_type = "Repaired Area"

        # Total image area (estimate from largest bbox)
        img_area = max(d["area_pixels"] for d in detections) * 4 if detections else 1
        total_damage_area = sum(areas)
        damage_area_ratio = min(1.0, total_damage_area / max(img_area, 1))

        return {
            "detections": detections,
            "damage_types": damage_types,
            "max_severity_hint": max_hint,
            "detection_count": len(detections),
            "damage_area_ratio": round(damage_area_ratio, 4),
            "suggested_damage_type": suggested_type,
            "severity_shift": shift,
            "confidence_avg": round(sum(confidences) / len(confidences), 4),
        }

    @staticmethod
    def _empty_result() -> Dict:
        return {
            "detections": [],
            "damage_types": [],
            "max_severity_hint": None,
            "detection_count": 0,
            "damage_area_ratio": 0.0,
            "suggested_damage_type": None,
            "severity_shift": 0,
            "confidence_avg": 0.0,
        }

    def apply_severity_shift(self, base_severity: str, shift: int) -> str:
        """Shift a severity level up or down by `shift` steps."""
        if not base_severity or shift == 0:
            return base_severity
        idx = _SEVERITY_ORDER.index(base_severity) if base_severity in _SEVERITY_ORDER else 1
        new_idx = max(0, min(len(_SEVERITY_ORDER) - 1, idx + shift))
        return _SEVERITY_ORDER[new_idx]


# Singleton accessor
_detector = None


def get_yolo_detector(model_path: Optional[str] = None) -> YOLODamageDetector:
    """Lazy singleton for the YOLO damage detector."""
    global _detector
    if _detector is None:
        if model_path is None:
            model_path = os.path.join(
                os.path.dirname(__file__), "models", "road_damage_yolo.pt"
            )
        _detector = YOLODamageDetector(model_path=model_path)
    return _detector
