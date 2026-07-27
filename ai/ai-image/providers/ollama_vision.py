from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .base import ImageModelProvider


RESULT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "ocr_text": {"type": "string"},
        "objects": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": [
        "title",
        "description",
        "tags",
        "ocr_text",
        "objects",
        "confidence",
    ],
    "additionalProperties": False,
}


class OllamaVisionProvider(ImageModelProvider):
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.base_url = str(config.get("base_url", "http://localhost:11434")).rstrip("/")
        self.timeout = int(config.get("timeout_seconds", 300))

    @property
    def model_id(self) -> str:
        return str(self.config["model_id"])

    def _request(self, endpoint: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{endpoint}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="GET" if payload is None else "POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"Ollama HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                "Ollama에 연결할 수 없습니다. Ollama 앱 또는 `ollama serve`를 실행하세요. "
                f"({exc.reason})"
            ) from exc

    def load(self) -> None:
        response = self._request("/api/tags")
        installed = {
            str(item.get("name", ""))
            for item in response.get("models", [])
            if isinstance(item, dict)
        }
        if self.model_id not in installed:
            raise RuntimeError(
                f"Ollama 모델이 설치되지 않았습니다: {self.model_id}\n"
                f"먼저 `ollama pull {self.model_id}`를 실행하세요."
            )

    def analyze(self, image_path: Path, prompt: str) -> tuple[str, dict[str, Any]]:
        raw_image = image_path.read_bytes()
        encoded_image = base64.b64encode(raw_image).decode("ascii")
        payload = {
            "model": self.model_id,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [encoded_image],
                }
            ],
            "stream": False,
            "format": RESULT_SCHEMA,
            "options": {
                "temperature": float(self.config.get("temperature", 0.0)),
                "seed": int(self.config.get("seed", 42)),
                "num_ctx": int(self.config.get("context_length", 4096)),
                "num_predict": int(self.config.get("max_new_tokens", 800)),
            },
            "keep_alive": self.config.get("keep_alive", "10m"),
        }
        started = time.perf_counter()
        response = self._request("/api/chat", payload)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        content = str(response.get("message", {}).get("content", "")).strip()
        if not content:
            raise RuntimeError("Ollama 모델 응답이 비어 있습니다.")
        input_tokens = response.get("prompt_eval_count")
        output_tokens = response.get("eval_count")
        return content, {
            "latency_ms": elapsed_ms,
            "input_tokens": int(input_tokens) if input_tokens is not None else None,
            "output_tokens": int(output_tokens) if output_tokens is not None else None,
            "quantization": self.config.get("quantization", "ollama-default"),
            "device_map": "ollama-auto",
            "load_duration_ms": round(float(response.get("load_duration", 0)) / 1_000_000, 2),
            "prompt_eval_duration_ms": round(
                float(response.get("prompt_eval_duration", 0)) / 1_000_000, 2
            ),
            "generation_duration_ms": round(
                float(response.get("eval_duration", 0)) / 1_000_000, 2
            ),
            "total_duration_ms": round(
                float(response.get("total_duration", 0)) / 1_000_000, 2
            ),
            "tokens_per_second": round(
                int(output_tokens or 0)
                / max(float(response.get("eval_duration", 0)) / 1_000_000_000, 1e-9),
                2,
            ),
            "original_image_bytes": len(raw_image),
            "sent_image_bytes": len(raw_image),
            "image_resized": False,
            "image_resize_policy": "original",
        }
