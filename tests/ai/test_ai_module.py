"""Tests for the AI module: preprocessing, features, severity, priority."""
import os
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


class TestPreprocessing:
    def test_load_numpy_array(self):
        from ai.preprocessing import load_image
        arr = np.zeros((100, 100, 3), dtype=np.uint8)
        result = load_image(arr)
        assert result.shape == (100, 100, 3)

    def test_resize_with_pad(self):
        from ai.preprocessing import resize_with_pad
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        result = resize_with_pad(img, (256, 256))
        assert result.shape == (256, 256, 3)

    def test_full_pipeline(self):
        from ai.preprocessing import ImagePreprocessor
        img = np.random.randint(0, 255, (300, 300, 3), dtype=np.uint8)
        pp = ImagePreprocessor(target_size=(128, 128))
        views = pp.process(img)
        assert views["rgb"].shape == (128, 128, 3)
        assert views["enhanced"].shape == (128, 128, 3)
        assert views["gray"].shape == (128, 128)
        assert views["edges"].shape == (128, 128)


class TestFeatureExtraction:
    def test_extract_features_returns_dict(self):
        from ai.feature_extraction import extract_features
        img = np.random.randint(0, 255, (128, 128, 3), dtype=np.uint8)
        feats = extract_features(img)
        assert isinstance(feats, dict)
        assert "edge_density" in feats
        assert "dark_pixel_ratio" in feats
        assert "crack_length" in feats

    def test_features_to_vector_consistent(self):
        from ai.feature_extraction import features_to_vector, FEATURE_NAMES
        feats = {name: float(i) for i, name in enumerate(FEATURE_NAMES)}
        vec = features_to_vector(feats)
        assert vec.shape == (len(FEATURE_NAMES),)
        assert vec[0] == 0.0
        assert vec[-1] == float(len(FEATURE_NAMES) - 1)


class TestSeverityClassifier:
    def test_rule_based_severity_levels(self):
        from ai.severity_classifier import _rule_based_severity, SEVERITY_LEVELS
        # Low severity: clean image
        clean = np.full((128, 128, 3), 200, dtype=np.uint8)
        from ai.feature_extraction import extract_features
        from ai.preprocessing import to_grayscale, detect_edges
        gray = to_grayscale(clean)
        edges = detect_edges(gray)
        feats = extract_features(clean, gray, edges)
        sev, conf, dtype = _rule_based_severity(feats)
        assert sev in SEVERITY_LEVELS
        assert 0.55 <= conf <= 0.95
        assert isinstance(dtype, str)

    def test_analyzer_without_ml(self):
        from ai.severity_classifier import SeverityAnalyzer
        analyzer = SeverityAnalyzer(model_path=None, use_ml=False)
        img = np.random.randint(0, 100, (128, 128, 3), dtype=np.uint8)
        result = analyzer.analyze_image(img)
        assert "severity" in result
        assert "confidence" in result
        assert "damage_type" in result
        assert "features" in result
        assert result["severity"] in ("Low", "Moderate", "High", "Critical")

    def test_analyzer_with_sample_image(self):
        from ai.severity_classifier import SeverityAnalyzer
        # Find a sample image
        img_dir = ROOT / "sample_data" / "images"
        if not img_dir.exists():
            pytest.skip("No sample images directory")
        images = list(img_dir.glob("*.png"))
        if not images:
            pytest.skip("No sample images")

        model_path = ROOT / "ai" / "models" / "severity_classifier.joblib"
        analyzer = SeverityAnalyzer(
            model_path=str(model_path) if model_path.exists() else None,
            use_ml=model_path.exists(),
        )
        result = analyzer.analyze_image(str(images[0]))
        assert "severity" in result
        assert "confidence" in result


class TestPriorityEngine:
    def test_basic_priority_computation(self):
        from ai.priority_engine import PriorityEngine
        from datetime import datetime, timedelta
        engine = PriorityEngine()
        result = engine.compute(
            severity="Critical",
            verification_count=5,
            population=200000,
            road_class="major_road",
            hospital_distance_km=0.5,
            school_distance_km=0.3,
            infrastructure_code="BRIDGE",
            created_at=datetime.utcnow() - timedelta(hours=24),
            status="Verified",
            credibility_score=8.0,
        )
        assert 0 <= result["score"] <= 100
        assert result["resource_urgency"] in ("Immediate", "High", "Medium", "Low", "Minimal")
        assert result["recommended_response_time"] is not None
        assert "components" in result

    def test_critical_gets_immediate_response(self):
        from ai.priority_engine import PriorityEngine
        from datetime import datetime, timedelta
        engine = PriorityEngine()
        result = engine.compute(
            severity="Critical",
            verification_count=10,
            population=500000,
            road_class="highway",
            hospital_distance_km=0.2,
            school_distance_km=0.1,
            infrastructure_code="BRIDGE",
            created_at=datetime.utcnow() - timedelta(hours=48),
            status="Verified",
            credibility_score=10.0,
        )
        assert result["score"] >= 60  # high score for critical inputs
        assert result["resource_urgency"] in ("Immediate", "High")

    def test_low_severity_gets_minimal(self):
        from ai.priority_engine import PriorityEngine
        from datetime import datetime
        engine = PriorityEngine()
        result = engine.compute(
            severity="Low",
            verification_count=0,
            population=5000,
            road_class="residential",
            hospital_distance_km=5.0,
            school_distance_km=3.0,
            infrastructure_code="PARK",
            created_at=datetime.utcnow(),
            status="Reported",
            credibility_score=0.0,
        )
        assert result["score"] < 50

    def test_assign_ranks(self):
        from ai.priority_engine import PriorityEngine
        engine = PriorityEngine()
        scored = [
            {"id": 1, "score": 75.0},
            {"id": 2, "score": 90.0},
            {"id": 3, "score": 50.0},
        ]
        ranked = engine.assign_ranks(scored)
        assert ranked[0]["id"] == 2  # highest score first
        assert ranked[0]["rank"] == 1
        assert ranked[1]["id"] == 1
        assert ranked[1]["rank"] == 2
        assert ranked[2]["id"] == 3
        assert ranked[2]["rank"] == 3


class TestSampleDataGenerator:
    def test_generate_samples_shape(self):
        from ai.generate_sample_data import generate_samples
        X, y = generate_samples(n_per_class=20, seed=42)
        assert X.shape == (80, 13)  # 4 classes × 20 samples × 13 features
        assert y.shape == (80,)
        assert set(np.unique(y).tolist()) == {"Low", "Moderate", "High", "Critical"}
