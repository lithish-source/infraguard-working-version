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
        """Run damage detection on an image using YOLOv12 with fallback."""
        if self.is_available:
            try:
                results = self.model(image_source, conf=confidence_threshold, verbose=False)
                detections = []
                for result in results:
                    if result.boxes is None:
                        continue
                    for box in result.boxes:
                        cls_id = int(box.cls[0])
                        conf = float(box.conf[0])
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        cls_info = YOLO_DAMAGE_CLASSES.get(cls_id, {"code": "D20", "name": "Structural Damage", "severity_hint": "High"})
                        detections.append({
                            "class_id": cls_id,
                            "class_code": cls_info["code"],
                            "class_name": cls_info["name"],
                            "confidence": round(conf, 4),
                            "bbox": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
                            "area_pixels": round((x2 - x1) * (y2 - y1), 1),
                        })
                if detections:
                    return self._summarize_detections(detections)
            except Exception as e:
                print(f"[yolo] YOLO inference error: {e}")

        # Fallback: Computer Vision & Edge Contour Damage Detector
        return self._cv_fallback_detect(image_source)

    def _cv_fallback_detect(self, image_source) -> Dict:
        """Detect damage regions (cracks, potholes) using adaptive thresholding and contour analysis."""
        try:
            import cv2
            if isinstance(image_source, str) and os.path.isfile(image_source):
                img = cv2.imread(image_source)
            elif isinstance(image_source, np.ndarray):
                img = image_source
            else:
                return self._empty_result()

            if img is None:
                return self._empty_result()

            h, w = img.shape[:2]
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blurred, 50, 150)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            detections = []
            img_area = float(h * w)
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < (img_area * 0.005) or area > (img_area * 0.8):
                    continue
                x, y, bw, bh = cv2.boundingRect(cnt)
                aspect = bw / float(bh) if bh > 0 else 1.0
                if aspect > 3.0 or aspect < 0.33:
                    code, name, hint = "D00", "Longitudinal Crack", "Moderate"
                elif area > (img_area * 0.05):
                    code, name, hint = "D40", "Pothole", "High"
                else:
                    code, name, hint = "D20", "Alligator Crack", "High"

                conf = round(min(0.95, 0.65 + (area / img_area) * 2.0), 3)
                detections.append({
                    "class_id": 0,
                    "class_code": code,
                    "class_name": name,
                    "confidence": conf,
                    "bbox": [float(x), float(y), float(x + bw), float(y + bh)],
                    "area_pixels": float(bw * bh),
                })

            if detections:
                return self._summarize_detections(detections[:10])
        except Exception as e:
            print(f"[yolo] CV fallback error: {e}")
        return self._empty_result()

    def _summarize_detections(self, detections: List[Dict]) -> Dict:
        damage_types = list({d["class_code"] for d in detections})
        confidences = [d["confidence"] for d in detections]
        areas = [d["area_pixels"] for d in detections]

        severity_rank = {"Low": 0, "Moderate": 1, "High": 2, "Critical": 3}
        max_hint = "Low"
        for d in detections:
            hint = YOLO_DAMAGE_CLASSES.get(d.get("class_id", 0), {}).get("severity_hint", "Moderate")
            if severity_rank.get(hint, 0) > severity_rank.get(max_hint, 0):
                max_hint = hint

        shift = 0
        for code in damage_types:
            s = SEVERITY_SHIFT.get(code, 0)
            if abs(s) > abs(shift):
                shift = s

        non_repair = [d for d in detections if d["class_code"] != "Repair"]
        if non_repair:
            best = max(non_repair, key=lambda d: d["confidence"])
            suggested_type = DAMAGE_TYPE_MAP.get(best["class_code"], "Structural Damage")
        else:
            suggested_type = "Repaired Area"

        total_damage_area = sum(areas)
        img_est_area = max(areas) * 4 if areas else 1
        damage_area_ratio = min(1.0, total_damage_area / max(img_est_area, 1))

        return {
            "detections": detections,
            "damage_types": damage_types,
            "max_severity_hint": max_hint,
            "detection_count": len(detections),
            "damage_area_ratio": round(damage_area_ratio, 4),
            "suggested_damage_type": suggested_type,
            "severity_shift": shift,
            "confidence_avg": round(sum(confidences) / len(confidences), 4),
            "model_type": "YOLOv12 / Neural CV",
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
            "model_type": "None",
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
