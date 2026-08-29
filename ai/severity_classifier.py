"""Severity classifier for infrastructure damage images.

Combines (in priority order):
  1. Optional LLM API (Llama 3 / GPT-4o Vision) — best accuracy when configured
  2. YOLOv12 road damage detector (real-world damage recognition from RDD2022)
  3. Optional ML classifier (RandomForest trained on synthetic data)
  4. Rule-based heuristics (always available, transparent)

Severity levels: Low, Moderate, High, Critical
"""
from __future__ import annotations

import json
import os
from typing import Dict, Optional, Tuple

import numpy as np
import joblib

from ai.preprocessing import ImagePreprocessor
from ai.feature_extraction import extract_features, features_to_vector, FEATURE_NAMES


SEVERITY_LEVELS = ["Low", "Moderate", "High", "Critical"]
SEVERITY_WEIGHTS = {"Low": 1.0, "Moderate": 2.5, "High": 4.0, "Critical": 5.0}


def __getattr__(name):
    """Lazy import to avoid circular dependency."""
    if name == "PriorityEngine":
        from ai.priority_engine import PriorityEngine
        return PriorityEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# Plausible damage types per category — used as labels from the rule-based branch
DAMAGE_TYPES = [
    "Surface Crack",
    "Pothole",
    "Structural Damage",
    "Corrosion",
    "Water Logging",
    "Broken Component",
    "Erosion",
    "Vegetation Overgrowth",
    "Subsidence",
    "Faulty Wiring",
]


def _rule_based_severity(features: Dict[str, float]) -> Tuple[str, float, str]:
    """Transparent rule-based severity estimate.

    Returns: (severity_label, confidence_in_[0,1], damage_type)
    """
    edge_density = features["edge_density"]
    dark_ratio = features["dark_pixel_ratio"]
    crack_len = features["crack_length"]
    damage_area = features["damage_area_ratio"]
    texture_var = features["texture_variance"]

    score = 0.0
    score += min(edge_density * 12.0, 2.5)
    score += min(dark_ratio * 6.0, 2.0)
    score += min(crack_len / 1500.0, 2.0)
    score += min(damage_area * 5.0, 2.0)
    score += min(texture_var / 1500.0, 1.5)

    if score >= 7.5:
        severity = "Critical"
    elif score >= 5.0:
        severity = "High"
    elif score >= 2.5:
        severity = "Moderate"
    else:
        severity = "Low"

    confidence = max(0.55, min(0.95, 0.55 + score * 0.04))

    if edge_density > 0.20 and crack_len > 800:
        damage_type = "Surface Crack"
    elif dark_ratio > 0.30:
        damage_type = "Pothole"
    elif features["mean_saturation"] < 35 and damage_area > 0.25:
        damage_type = "Corrosion"
    elif features["mean_b"] > features["mean_r"] and dark_ratio > 0.15:
        damage_type = "Water Logging"
    elif edge_density < 0.05 and texture_var < 400:
        damage_type = "Vegetation Overgrowth"
    else:
        damage_type = "Structural Damage"

    return severity, round(confidence, 3), damage_type


class SeverityAnalyzer:
    """Combines rule-based + optional ML + optional LLM classifier.

    Priority: LLM (if configured) > ML (if model loaded) > rule-based (always).
    """

    def __init__(self, model_path: Optional[str] = None, use_ml: bool = True, use_yolo: bool = True):
        self.preprocessor = ImagePreprocessor(target_size=(256, 256))
        self.model_path = model_path
        self.use_ml = use_ml
        self.clf = None
        self.scaler = None
        if use_ml:
            if model_path and os.path.exists(model_path):
                try:
                    bundle = joblib.load(model_path)
                    self.clf = bundle.get("model")
                    self.scaler = bundle.get("scaler")
                except Exception as e:
                    print(f"[ai] Pickle mismatch, auto-training severity classifier: {e}")
                    self.clf = None
            if self.clf is None:
                try:
                    from ai.train import train_severity_model
                    self.clf, self.scaler = train_severity_model(save_path=model_path)
                    print(f"[ai] Freshly trained and loaded severity classifier model")
                except Exception as e2:
                    print(f"[ai] Auto-training fallback error: {e2}")

        # YOLO road damage detector
        self.yolo = None
        if use_yolo:
            try:
                from ai.yolo_damage_detector import get_yolo_detector
                self.yolo = get_yolo_detector()
            except Exception as e:
                print(f"[ai] YOLO detector init failed: {e}")
                self.yolo = None

        # Lazy LLM check — import inside method to avoid hard dependency
        # on app.core.config when this module is used standalone (e.g. in tests)
        self._llm_checked = False
        self._llm_enabled = False

    def _check_llm(self) -> bool:
        """Check if LLM API is enabled (cached)."""
        if not self._llm_checked:
            try:
                from app.services.llm_service import is_llm_enabled
                self._llm_enabled = is_llm_enabled()
            except ImportError:
                # Standalone mode (no FastAPI app context) — LLM unavailable
                self._llm_enabled = False
            except Exception:
                self._llm_enabled = False
            self._llm_checked = True
        return self._llm_enabled

    def analyze_image(self, image_source) -> Dict:
        """Run full pipeline and return severity assessment.

        Priority: LLM > ML > rule-based. Each branch's output is preserved
        in the result for auditability.
        """
        views = self.preprocessor.process(image_source)
        features = extract_features(views["enhanced"], views["gray"], views["edges"])

        rule_severity, rule_conf, rule_damage_type = _rule_based_severity(features)

        ml_severity = None
        ml_conf = None
        if self.clf is not None and self.scaler is not None:
            try:
                X = features_to_vector(features).reshape(1, -1)
                Xs = self.scaler.transform(X)
                proba = self.clf.predict_proba(Xs)[0]
                idx = int(np.argmax(proba))
                ml_severity = SEVERITY_LEVELS[idx]
                ml_conf = float(proba[idx])
            except Exception as e:
                print(f"[ai] ML inference failed, falling back to rules: {e}")
                ml_severity = None
                ml_conf = None

        # Try LLM if enabled (only for file paths — needs to read bytes)
        llm_result = None
        if self._check_llm() and isinstance(image_source, str) and os.path.exists(image_source):
            try:
                from app.services.llm_service import analyze_image_with_llm
                llm_result = analyze_image_with_llm(image_source)
            except Exception as e:
                print(f"[ai] LLM inference failed: {e}")
                llm_result = None

        # YOLO road damage detection
        yolo_result = None
        if self.yolo is not None and self.yolo.is_available:
            try:
                yolo_result = self.yolo.detect(image_source)
            except Exception as e:
                print(f"[ai] YOLO detection failed: {e}")
                yolo_result = None

        # Decide base severity + confidence
        # Priority: LLM > ML > rule-based
        if llm_result is not None:
            base_severity = llm_result["severity"]
            base_conf = round(
                (llm_result["confidence"] + rule_conf) / 2.0, 3
            )
            base_damage_type = llm_result["damage_type"]
        elif ml_severity is not None:
            base_severity = ml_severity
            base_conf = round((ml_conf + rule_conf) / 2.0, 3)
            base_damage_type = rule_damage_type
        else:
            base_severity = rule_severity
            base_conf = rule_conf
            base_damage_type = rule_damage_type

        # Apply YOLO refinements
        final_severity = base_severity
        final_conf = base_conf
        damage_type = base_damage_type

        if yolo_result is not None and yolo_result["detection_count"] > 0:
            # Override damage type with YOLO's more accurate classification
            if yolo_result["suggested_damage_type"]:
                damage_type = yolo_result["suggested_damage_type"]

            # Apply severity shift based on damage type detected by YOLO
            shift = yolo_result["severity_shift"]
            if shift != 0:
                final_severity = self.yolo.apply_severity_shift(base_severity, shift)

            # Boost confidence when YOLO agrees with other methods
            yolo_conf = yolo_result["confidence_avg"]
            if yolo_conf > 0.5:
                final_conf = round(min(0.98, (final_conf + yolo_conf) / 2.0 + 0.05), 3)

        return {
            "severity": final_severity,
            "confidence": final_conf,
            "damage_type": damage_type,
            "rule_based_severity": rule_severity,
            "ml_severity": ml_severity,
            "ml_confidence": ml_conf,
            "yolo_severity_shift": yolo_result["severity_shift"] if yolo_result else 0,
            "yolo_damage_types": yolo_result["damage_types"] if yolo_result else [],
            "yolo_detection_count": yolo_result["detection_count"] if yolo_result else 0,
            "yolo_detections": yolo_result["detections"] if yolo_result else [],
            "yolo_confidence_avg": yolo_result["confidence_avg"] if yolo_result else 0.0,
            "llm_severity": llm_result["severity"] if llm_result else None,
            "llm_confidence": llm_result["confidence"] if llm_result else None,
            "llm_description": llm_result["description"] if llm_result else None,
            "llm_reasoning": llm_result["reasoning"] if llm_result else None,
            "llm_model": llm_result["model"] if llm_result else None,
            "features": features,
            "feature_vector": features_to_vector(features).tolist(),
            "image_shape": views["shape"],
            "explainability": {
                "edge_density": features["edge_density"],
                "dark_pixel_ratio": features["dark_pixel_ratio"],
                "crack_length": features["crack_length"],
                "damage_area_ratio": features["damage_area_ratio"],
                "texture_variance": features["texture_variance"],
                "weighted_score_used_for_rules": round(
                    min(features["edge_density"] * 12.0, 2.5)
                    + min(features["dark_pixel_ratio"] * 6.0, 2.0)
                    + min(features["crack_length"] / 1500.0, 2.0)
                    + min(features["damage_area_ratio"] * 5.0, 2.0)
                    + min(features["texture_variance"] / 1500.0, 1.5),
                    3,
                ),
            },
        }

    def is_ready(self) -> bool:
        """True if any of the classifier branches is available."""
        return self.clf is not None or self._check_llm() or (self.yolo is not None and self.yolo.is_available)
