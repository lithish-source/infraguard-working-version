"""AI analyzer singleton accessor.

Separated from app.main to avoid circular imports.
"""
import os

_ai_analyzer = None


def get_ai_analyzer():
    """Lazy accessor for the singleton SeverityAnalyzer."""
    global _ai_analyzer
    if _ai_analyzer is None:
        try:
            from ai.severity_classifier import SeverityAnalyzer
            from app.core.config import settings
            model_path = settings.AI_MODEL_PATH
            _ai_analyzer = SeverityAnalyzer(
                model_path=model_path if os.path.exists(model_path) else None,
                use_ml=True,
                use_yolo=True,
            )
        except Exception as e:
            print(f"[ai_runtime] AI analyzer init failed (will use rule-based fallback): {e}")
            try:
                from ai.severity_classifier import SeverityAnalyzer
                _ai_analyzer = SeverityAnalyzer(model_path=None, use_ml=False)
            except Exception as e2:
                print(f"[ai_runtime] Rule-based fallback also failed: {e2}")
                _ai_analyzer = None
    return _ai_analyzer
