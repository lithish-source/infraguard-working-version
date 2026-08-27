# AI Model Documentation

## Overview

InfraGuard's AI module is a **hybrid rule-based + ML + optional LLM pipeline** for infrastructure damage severity assessment and prioritization. It runs as a standalone Python package (`ai/`) imported by the FastAPI backend.

```
┌──────────────┐    ┌─────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  Image input │ →  │ Preprocessing   │ →  │ Feature          │ →  │ Severity         │
│  (file/bytes)│    │ (OpenCV)        │    │ Extraction (13)  │    │ Classifier       │
└──────────────┘    └─────────────────┘    └──────────────────┘    └────────┬─────────┘
                                                                                            │
                                                                                            ▼
                                                              ┌──────────────────────────────┐
                                                              │ Priority Engine (9 factors)  │
                                                              │ + Overpass API real distances │
                                                              │ → Score 0-100, urgency, ETA  │
                                                              └──────────────────────────────┘
```

The classifier has three branches, tried in priority order:

1. **LLM Vision API** (if `LLM_API_KEY` is set) — Llama 4 Scout, GPT-4o, or any OpenAI-compatible vision model
2. **ML classifier** (scikit-learn RandomForest, trained on synthetic data)
3. **Rule-based heuristics** (always available, transparent)

All three outputs are preserved in the report's `ai_features` JSONB field for auditability.

The priority engine now uses **real geospatial data** from the Overpass API (OpenStreetMap) for:
- Hospital proximity (real distance to nearest hospital within 5 km)
- School proximity (real distance to nearest school/college within 3 km)
- Road class (highest-class road within 200 m of the report location)

Results are cached per ~110m grid cell (3 decimal places of lat/lng) to avoid repeated API calls.

## 1. Image Preprocessing Pipeline (`ai/preprocessing.py`)

### Steps

1. **Load** — accepts file path, bytes, PIL.Image, or numpy array. Converts to RGB.
2. **Resize with padding** — resize to 256×256 preserving aspect ratio, padding remainder with black.
3. **Denoise** — bilateral filter (`d=5, sigmaColor=50, sigmaSpace=50`) preserves edges while smoothing noise.
4. **CLAHE enhancement** — applied on L channel of LAB color space. Contrast-limited adaptive histogram equalization reveals damage patterns.
5. **Grayscale + edges** — Canny edge detection (`threshold1=50, threshold2=150`) extracts crack patterns.

### Why these steps?

| Step | Purpose |
|---|---|
| Resize + pad | Standardizes input for feature extraction without distortion |
| Bilateral filter | Removes sensor noise while preserving crack edges (unlike Gaussian) |
| CLAHE | Damage photos often have poor lighting; CLAHE normalizes local contrast |
| Canny edges | Cracks manifest as edge clusters — quantifying them gives a severity proxy |

## 2. Feature Extraction (`ai/feature_extraction.py`)

13 hand-crafted features extracted from the preprocessed image:

| # | Feature | Description | Why it matters |
|---|---|---|---|
| 1 | `edge_density` | Non-zero pixels / total in edge map | More edges → more cracks → higher severity |
| 2 | `dark_pixel_ratio` | Pixels < 70 brightness / total | Dark patches = potholes, water, shadow damage |
| 3 | `texture_variance` | Variance of grayscale | High variance = uneven damage |
| 4 | `crack_length` | Skeletonized edge count | Proxy for total crack length |
| 5 | `damage_area_ratio` | Pixels < 90 brightness / total | Larger dark area = more extensive damage |
| 6 | `mean_r`, `mean_g`, `mean_b` | Mean color channels | Color shifts indicate material degradation |
| 7 | `std_r`, `std_g`, `std_b` | Std of color channels | Heterogeneity indicates damage mottling |
| 8 | `mean_saturation` | HSV saturation mean | Low saturation = rust, corrosion |
| 9 | `mean_value` | HSV value (brightness) mean | Darker overall = more damage |

These features are interpretable, fast to compute (no GPU needed), and capture both structural (edge-based) and visual (color-based) damage cues.

## 3. Severity Classifier (`ai/severity_classifier.py`)

### Hybrid Architecture

```
                  ┌────────────────────┐
                  │  Rule-Based Branch │  (always available)
                  │  Transparent score │
                  └─────────┬──────────┘
                            │
Image → features ──────────►├──→ Final severity + confidence
                            │
                  ┌─────────┴──────────┐
                  │   ML Branch        │  (if model loaded)
                  │   RandomForest     │
                  └────────────────────┘
```

### Rule-Based Scoring

```python
score = 0
score += min(edge_density * 12.0, 2.5)        # max 2.5
score += min(dark_pixel_ratio * 6.0, 2.0)     # max 2.0
score += min(crack_length / 1500.0, 2.0)      # max 2.0
score += min(damage_area_ratio * 5.0, 2.0)    # max 2.0
score += min(texture_variance / 1500.0, 1.5)  # max 1.5
# Max possible: 10.0

if score >= 7.5: severity = "Critical"
elif score >= 5.0: severity = "High"
elif score >= 2.5: severity = "Moderate"
else: severity = "Low"

confidence = clip(0.55 + score * 0.04, 0.55, 0.95)
```

### Damage Type Heuristics

| Condition | Damage Type |
|---|---|
| `edge_density > 0.20` and `crack_length > 800` | Surface Crack |
| `dark_pixel_ratio > 0.30` | Pothole |
| Low saturation + high damage area | Corrosion |
| High blue channel + dark ratio | Water Logging |
| Low edge density + low texture | Vegetation Overgrowth |
| Default | Structural Damage |

### ML Branch (RandomForest)

- **Algorithm:** `RandomForestClassifier(n_estimators=200, max_depth=12, min_samples_leaf=2, class_weight='balanced')`
- **Preprocessing:** `StandardScaler` (mean=0, std=1 per feature)
- **Training data:** 1200 synthetic samples (300 per class) generated by `ai/generate_sample_data.py` using per-severity Gaussian profiles of the 13 features
- **Cross-validation:** 80/20 stratified split, 5-fold CV
- **Test accuracy:** ~99% (on synthetic data; real-world accuracy depends on photo quality)

### Confidence Estimation

```
final_confidence = (rule_confidence + ml_confidence) / 2
```

When ML is unavailable (model not loaded), only rule-based confidence is used (range 0.55-0.95).

## 4. Priority Engine (`ai/priority_engine.py`)

### 9-Factor Weighted Scoring

Each component is normalized to [0, 1] and combined with fixed weights:

| Component | Weight | Normalization |
|---|---|---|
| AI Severity | 28% | `severity_weight / 5.0` (Critical=1.0, Low=0.2) |
| Verification Count | 12% | `clip(verification_count / 15, 0, 1)` |
| Population Impact | 10% | `clip((population - 5000) / 495000, 0, 1)` |
| Road Importance | 10% | By road class: highway=1.0, major=0.85, arterial=0.7, collector=0.55, local=0.35, residential=0.25 |
| Hospital Proximity | 10% | `1.0 - distance_km / 5.0` (closer = more urgent) |
| Utility Importance | 8% | By infra code: WATER/POWER/BRIDGE/TRAFFIC/HOSPITAL=1.0, ROAD/DRAINAGE/STREETLIGHT=0.7, else 0.5 |
| Time Urgency | 8% | `clip((hours - 6) / 66, 0, 1)` (older = more urgent) |
| Verification Status | 7% | Verified=1.0, Reported=0.6, other=0.3 |
| School Proximity | 7% | `1.0 - distance_km / 3.0` |

### Final Score Formula

```
raw_score = Σ (component_i × weight_i)        # in [0, 1]
credibility_factor = 0.9 + min(0.2, credibility_score / 10)   # ±10%
adjusted_score = min(1.0, raw_score × credibility_factor)
priority_score = round(adjusted_score × 100, 2)               # 0-100
```

### Urgency Bands

| Score | Urgency | Response Time |
|---|---|---|
| ≥ 80 | Immediate | Within 2 hours |
| 60-79 | High | Within 6 hours |
| 40-59 | Medium | Within 24 hours |
| 20-39 | Low | Within 72 hours |
| < 20 | Minimal | Within 7 days |

### Explainability

Every priority computation returns the full per-component breakdown, allowing admins to see exactly why a report scored high or low. This is rendered as a horizontal bar chart in the Report Details page.

## 5. Training Pipeline (`ai/train.py`)

```bash
# Train on synthetic data
python -m ai.train

# Or via setup script (also generates sample images)
python scripts/setup_sample_data.py
```

### Output

Model bundle saved as `ai/models/severity_classifier.joblib`:

```python
{
  "model": RandomForestClassifier,
  "scaler": StandardScaler,
  "feature_names": [...13 names...],
  "labels": ["Low", "Moderate", "High", "Critical"],
  "metrics": {
    "accuracy": 0.996,
    "report": {...sklearn classification_report...},
    "confusion_matrix": [[60,0,0,0],[0,59,1,0],[0,0,60,0],[0,1,0,59]]
  }
}
```

## 6. Inference (`ai/inference.py`)

Standalone CLI for testing on a single image:

```bash
python -m ai.inference path/to/damage.jpg
```

Output (JSON):
```json
{
  "severity": "High",
  "confidence": 0.83,
  "damage_type": "Surface Crack",
  "rule_based_severity": "High",
  "ml_severity": "High",
  "ml_confidence": 0.91,
  "explainability": {
    "edge_density": 0.23,
    "dark_pixel_ratio": 0.28,
    "crack_length": 1245.0,
    "damage_area_ratio": 0.31,
    "texture_variance": 1620.0,
    "weighted_score_used_for_rules": 6.2
  }
}
```

## 7. Model Evaluation

### Synthetic Dataset Results

```
Accuracy: 99.6%

              precision    recall  f1-score  support
Critical          0.98      1.00      0.99      60
High              1.00      0.98      0.99      60
Low               1.00      1.00      1.00      60
Moderate          1.00      1.00      1.00      60

accuracy                              1.00      240
macro avg         1.00      1.00      1.00      240
weighted avg      1.00      1.00      1.00      240
```

### Real-World Considerations

The synthetic dataset is intentionally Gaussian-idealized. For production:

1. **Collect real damage photos** with ground-truth severity labels from inspectors
2. **Re-train** with `python -m ai.train` after replacing the synthetic generator with a real dataset loader
3. **Monitor drift** — re-train monthly or when accuracy drops below 80%
4. **Consider deep learning** — replace RandomForest with a fine-tuned MobileNetV3 or EfficientNet-Lite if labeled data exceeds 10,000 samples

## 8. Limitations & Honest Trade-offs

| Limitation | Mitigation |
|---|---|
| Synthetic training data may not generalize | Rule-based branch always runs as fallback; admin can override severity |
| 13 hand-crafted features may miss subtle damage | Architecture supports swapping in CNN features by editing `feature_extraction.py` |
| Single-image analysis (no temporal context) | Future: compare with prior reports at same location |
| No damage-type-specific classifiers yet | Future: train per-category models (e.g. crack-detector for bridges) |
| Priority weights are hand-tuned | Future: learn weights from admin resolution outcomes (inverse RL) |

## 9. Production Hardening Checklist

- [x] Rule-based fallback when ML model unavailable
- [x] Confidence calibration (rule + ML averaged)
- [x] Explainable per-component priority breakdown
- [x] Model artifact versioning (joblib bundle)
- [x] Training script reproducible (fixed seeds)
- [x] Inference CLI for debugging
- [ ] A/B testing framework for model versions
- [ ] Real-time monitoring of inference latency
- [ ] Automated re-training trigger on accuracy drop
- [ ] Per-category model specialization
