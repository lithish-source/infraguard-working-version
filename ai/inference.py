"""Standalone inference CLI: classify one image and print results."""
from __future__ import annotations

import argparse
import json
import os
import sys

# Allow `python ai/inference.py <img>` from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.severity_classifier import SeverityAnalyzer


def main():
    ap = argparse.ArgumentParser(description="InfraGuard severity inference")
    ap.add_argument("image", help="Path to image file")
    ap.add_argument("--model", default=None, help="Path to trained model .joblib")
    args = ap.parse_args()

    analyzer = SeverityAnalyzer(model_path=args.model)
    result = analyzer.analyze_image(args.image)
    result.pop("feature_vector", None)  # noise
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
