"""Generate sample damage images + train the AI model.

This script is run once during project setup. It:
  1. Generates ~20 synthetic 'damage' images in sample_data/images/
  2. Trains the severity classifier and saves to ai/models/severity_classifier.joblib
"""
import os
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai.generate_sample_data import generate_sample_images, generate_samples
from ai.train import train
import numpy as np


def main():
    # 1. Generate sample images
    out_dir = ROOT / "sample_data" / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    generate_sample_images(str(out_dir), n_per_class=6)
    print(f"[setup] Sample images written to {out_dir}")

    # 2. Train classifier
    result = train(n_per_class=300)
    print(f"[setup] AI model trained. Accuracy: {result['accuracy']:.4f}")
    print(f"[setup] Model saved to {result['model_path']}")
    print("[setup] Done.")


if __name__ == "__main__":
    main()
