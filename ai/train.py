"""Train the severity classifier on the synthetic dataset.

Saves a joblib bundle: {model, scaler, feature_names, labels}.
"""
from __future__ import annotations

import os
import sys
from typing import Tuple

import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix

from ai.feature_extraction import FEATURE_NAMES
from ai.severity_classifier import SEVERITY_LEVELS
from ai.generate_sample_data import generate_samples


def train(
    n_per_class: int = 300,
    test_size: float = 0.2,
    seed: int = 42,
    output_path: str = None,
) -> dict:
    X, y = generate_samples(n_per_class=n_per_class, seed=seed)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, stratify=y, random_state=seed
    )

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=12,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=seed,
        n_jobs=-1,
    )
    clf.fit(X_train_s, y_train)

    y_pred = clf.predict(X_test_s)
    acc = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_test, y_pred, labels=SEVERITY_LEVELS).tolist()

    print(f"[train] Accuracy: {acc:.4f}")
    print(classification_report(y_test, y_pred, zero_division=0))

    output_path = output_path or os.path.join(
        os.path.dirname(__file__), "models", "severity_classifier.joblib"
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    joblib.dump(
        {
            "model": clf,
            "scaler": scaler,
            "feature_names": FEATURE_NAMES,
            "labels": SEVERITY_LEVELS,
            "metrics": {"accuracy": float(acc), "report": report, "confusion_matrix": cm},
        },
        output_path,
    )
    # Also train Priority ML model
    from ai.priority_ml_model import train_priority_model
    priority_res = train_priority_model()

    return {
        "accuracy": float(acc),
        "report": report,
        "confusion_matrix": cm,
        "model_path": output_path,
        "priority_ml": priority_res,
    }


if __name__ == "__main__":
    train()
