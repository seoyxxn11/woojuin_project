from __future__ import annotations

import base64
import os
import time
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

from .base import ImageModelProvider
from .gms import GmsProvider


class GeminiGmsProvider(ImageModelProvider):
    """Gemini image analysis through the SSAFY GMS proxy."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._api_key: str | None = None

    @property
    def model_id(self) -> str:
        return str(self._config["model_id"])

    def load(self) -> None:
        load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)
        key_name = str(self._config.get("api_key_env", "GMS_API_KEY"))
        api_key = (os.getenv(key_name) or "").strip()
        if not api_key:
            raise RuntimeError(f"환경변수 {key_name}에 키 값이 없습니다.")
        self._api_key = api_key

    def analyze(self, image_path: Path, prompt: str) -> tuple[str, dict[str, Any]]:
        if self._api_key is None:
            raise RuntimeError("Gemini GMS provider가 로드되지 않았습니다.")

        image_bytes, width, height = GmsProvider._prepare_image(image_path)
        encoded = base64.b64encode(image_bytes).decode("ascii")
        endpoint = str(self._config["endpoint"]).format(model_id=self.model_id)
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": encoded,
                        }
                    },
                ]
            }],
            "generationConfig": {
                "maxOutputTokens": int(self._config.get("max_new_tokens", 300)),
                "responseMimeType": "application/json",
                "thinkingConfig": {
                    "thinkingLevel": "minimal",
                },
            },
        }

        started_at = time.perf_counter()
        response = httpx.post(
            endpoint,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self._api_key,
            },
            json=payload,
            timeout=float(self._config.get("timeout_seconds", 90)),
        )
        if response.is_error:
            raise RuntimeError(f"Gemini GMS HTTP {response.status_code}: {response.text}")
        body = response.json()
        try:
            text = body["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Gemini 응답에서 텍스트를 찾을 수 없습니다: {body}") from exc

        usage = body.get("usageMetadata", {})
        return text, {
            "latency_ms": round((time.perf_counter() - started_at) * 1000, 2),
            "input_tokens": usage.get("promptTokenCount"),
            "output_tokens": usage.get("candidatesTokenCount"),
            "original_image_bytes": image_path.stat().st_size,
            "sent_image_bytes": len(image_bytes),
            "sent_image_width": width,
            "sent_image_height": height,
        }
