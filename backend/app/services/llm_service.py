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
    """Send image to LLM vision model for severity assessment.

    Returns:
        {
            "severity": str,           # Low/Moderate/High/Critical
            "damage_type": str,
            "confidence": float,      # 0.0-1.0
            "description": str,
            "reasoning": str,
            "model": str,              # which model was used
        }
        OR None if LLM is not enabled or the call failed.
    """
    if not is_llm_enabled():
        return None

    api_key = settings.LLM_API_KEY
    base_url = getattr(settings, "LLM_API_BASE_URL", "https://api.groq.com/openai/v1")
    model = getattr(settings, "LLM_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")

    if not model:
        print("[llm_service] LLM_VISION_MODEL not configured")
        return None

    # Encode image
    try:
        image_b64 = _encode_image_b64(image_path)
    except Exception as e:
        print(f"[llm_service] Could not read image: {e}")
        return None

    mime = _get_mime_type(image_path)
    data_url = f"data:{mime};base64,{image_b64}"

    # OpenAI-compatible chat completions with image content
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": SEVERITY_PROMPT},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        "temperature": 0.2,
        "max_tokens": 400,
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    url = f"{base_url.rstrip('/')}/chat/completions"
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            print(f"[llm_service] API returned {resp.status_code}: {resp.text[:300]}")
            return None

        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        # Parse JSON (some models wrap in ```json blocks)
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        parsed = json.loads(content)

        # Validate severity
        severity = parsed.get("severity", "").strip().title()
        if severity not in ("Low", "Moderate", "High", "Critical"):
            print(f"[llm_service] Invalid severity from LLM: {severity}")
            return None

        confidence = float(parsed.get("confidence", 0.7))
        confidence = max(0.0, min(1.0, confidence))

        return {
            "severity": severity,
            "damage_type": parsed.get("damage_type", "Unknown"),
            "confidence": confidence,
            "description": parsed.get("description", ""),
            "reasoning": parsed.get("reasoning", ""),
            "model": model,
        }

    except httpx.TimeoutException:
        print("[llm_service] Request timed out")
        return None
    except json.JSONDecodeError as e:
        print(f"[llm_service] Could not parse LLM response as JSON: {e}")
        return None
    except Exception as e:
        print(f"[llm_service] Unexpected error: {e}")
        return None


def get_llm_status() -> Dict:
    """Return status info for /health endpoint and admin UI."""
    return {
        "enabled": is_llm_enabled(),
        "api_base_url": getattr(settings, "LLM_API_BASE_URL", "https://api.groq.com/openai/v1"),
        "vision_model": getattr(settings, "LLM_VISION_MODEL", None),
    }
