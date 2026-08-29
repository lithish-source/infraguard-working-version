"""LLM service: optional integration with an OpenAI-compatible LLM API
(such as Llama 3.3 via Groq, Together AI, or any OpenAI-compatible endpoint).

This module is OPTIONAL. If LLM_API_KEY is not set in the environment,
all calls to `analyze_image_with_llm` return None and the system falls
back to the rule-based + scikit-learn classifier.

Setup (Llama 3.3 70B via Groq — free tier, 30 req/min):
  1. Get a free API key at https://console.groq.com
  2. Set in backend/.env:
       LLM_API_KEY=gsk_your_key_here
       LLM_API_BASE_URL=https://api.groq.com/openai/v1
       LLM_VISION_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
       # or use a vision-capable model if available

Other OpenAI-compatible providers also work:
  - Together AI:   LLM_API_BASE_URL=https://api.together.xyz/v1
  - OpenAI:        LLM_API_BASE_URL=https://api.openai.com/v1
                   LLM_VISION_MODEL=gpt-4o-mini
  - Local Ollama:  LLM_API_BASE_URL=http://localhost:11434/v1
                   LLM_API_KEY=ollama (ignored)
                   LLM_VISION_MODEL=llama3.2-vision
"""
from __future__ import annotations

import base64
import json
import os
from typing import Dict, Optional

import httpx

from app.core.config import settings


SEVERITY_PROMPT = """You are an infrastructure damage assessor. Analyze the photo and return STRICT JSON only.

Output format (no markdown, no explanation, just JSON):
{
  "severity": "Low" | "Moderate" | "High" | "Critical",
  "damage_type": "<one of: Surface Crack, Pothole, Structural Damage, Corrosion, Water Logging, Broken Component, Erosion, Vegetation Overgrowth, Subsidence, Faulty Wiring>",
  "confidence": <float between 0.0 and 1.0>,
  "description": "<one-sentence description of the visible damage>",
  "reasoning": "<one-sentence justification for the severity level>"
}

Severity guidelines:
- Low: Minor cosmetic damage, no safety risk (small cracks, faded paint, single streetlight out)
- Moderate: Functional impairment, moderate safety risk (medium pothole, partial blockage, several lights out)
- High: Significant damage, high safety risk (large pothole, structural crack, burst pipe)
- Critical: Severe damage, immediate safety hazard (bridge crack, major water main break, signal failure at intersection)

Return ONLY the JSON object."""


def is_llm_enabled() -> bool:
    """Check if LLM API integration is enabled (key is set)."""
    return bool(getattr(settings, "LLM_API_KEY", None))


def _encode_image_b64(image_path: str) -> str:
    """Read image file and return base64-encoded string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _get_mime_type(image_path: str) -> str:
    ext = os.path.splitext(image_path)[1].lower()
    return {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")


def analyze_image_with_llm(image_path: str) -> Optional[Dict]:
    """Send image to LLM vision model or feature reasoning model for severity assessment."""
    if not is_llm_enabled():
        return None

    api_key = settings.LLM_API_KEY
    base_url = getattr(settings, "LLM_API_BASE_URL", "https://api.groq.com/openai/v1")
    model = getattr(settings, "LLM_VISION_MODEL", "qwen/qwen3.6-27b")

    if not model or model == "llama-3.2-11b-vision-preview":
        model = "qwen/qwen3.6-27b"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    url = f"{base_url.rstrip('/')}/chat/completions"

    # Extract computer vision features
    from ai.feature_extraction import extract_features
    from ai.preprocessing import ImagePreprocessor
    prep = ImagePreprocessor(target_size=(256, 256))
    views = prep.process(image_path)
    feats = extract_features(views["enhanced"], views["gray"], views["edges"])

    text_prompt = f"""You are a senior civil & structural engineering damage assessor.
An infrastructure damage report photo was analyzed with the following computer vision metrics:
- Dark Pixel Cavity Ratio: {feats['dark_pixel_ratio']:.3f} (Values > 0.15 indicate deep potholes, road craters or hollow cavities)
- Edge Fracture Density: {feats['edge_density']:.3f} (Values > 0.12 indicate extensive surface fracturing)
- Crack Length: {feats['crack_length']:.1f} px
- Damage Area Ratio: {feats['damage_area_ratio']:.3f}
- Texture Variance: {feats['texture_variance']:.1f}

Respond ONLY with valid JSON:
{{
  "severity": "Low" | "Moderate" | "High" | "Critical",
  "damage_type": "Pothole" | "Structural Damage" | "Surface Crack" | "Water Logging" | "Corrosion",
  "confidence": 0.94,
  "description": "<one-sentence description of the damage>",
  "reasoning": "<one-sentence engineering justification for severity>"
}}
"""

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a civil engineering damage assessment system. Output valid JSON."},
            {"role": "user", "content": text_prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 1024,
    }

    try:
        with httpx.Client(timeout=25.0) as client:
            resp = client.post(url, json=payload, headers=headers)

        if resp.status_code != 200:
            print(f"[llm_service] API returned {resp.status_code}: {resp.text[:200]}")
            return None

        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        # Clean thinking tokens (<think>...</think>) and markdown
        import re
        content_clean = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        json_match = re.search(r"\{.*\}", content_clean, re.DOTALL)
        if not json_match:
            print(f"[llm_service] Could not locate JSON in response: {content_clean[:150]}")
            return None

        parsed = json.loads(json_match.group(0))

        severity = parsed.get("severity", "").strip().title()
        if severity not in ("Low", "Moderate", "High", "Critical"):
            severity = "Critical" if feats.get("dark_pixel_ratio", 0) > 0.2 else "Moderate"

        confidence = float(parsed.get("confidence", 0.92))
        confidence = max(0.65, min(0.98, confidence))

        return {
            "severity": severity,
            "damage_type": parsed.get("damage_type", "Pothole"),
            "confidence": round(confidence, 3),
            "description": parsed.get("description", "Infrastructure damage detected."),
            "reasoning": parsed.get("reasoning", "Assessed by LLM engineering model."),
            "model": model,
        }

    except Exception as e:
        print(f"[llm_service] Error during LLM assessment: {e}")
        return None


def get_llm_status() -> Dict:
    """Return status info for /health endpoint and admin UI."""
    return {
        "enabled": is_llm_enabled(),
        "api_base_url": getattr(settings, "LLM_API_BASE_URL", "https://api.groq.com/openai/v1"),
        "vision_model": getattr(settings, "LLM_VISION_MODEL", None),
    }
