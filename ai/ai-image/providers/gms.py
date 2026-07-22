from __future__ import annotations

import base64
import os
import time
from io import BytesIO
from pathlib import Path
from typing import Any

from openai import APIConnectionError, OpenAI
from dotenv import load_dotenv
from PIL import Image

from .base import ImageModelProvider


class GmsProvider(ImageModelProvider):
    """OpenAI-compatible GMS image analysis provider."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._client: OpenAI | None = None

    @property
    def model_id(self) -> str:
        return str(self._config["model_id"])

    def load(self) -> None:
        env_path = Path(__file__).resolve().parents[1] / ".env"
        load_dotenv(env_path, override=True)
        key_name = str(self._config.get("api_key_env", "GMS_API_KEY"))
        url_name = str(self._config.get("base_url_env", "GMS_BASE_URL"))
        api_key = os.getenv(key_name)
        base_url = self._config.get("base_url") or os.getenv(url_name)
        if not api_key:
            raise RuntimeError(f"환경변수 {key_name}가 설정되지 않았습니다.")
        api_key = api_key.strip()
        if not api_key:
            raise RuntimeError(f"환경변수 {key_name}에 키 값이 없습니다.")
        if not base_url:
            raise RuntimeError(
                f"GMS Base URL이 없습니다. 설정 파일의 base_url 또는 환경변수 {url_name}를 설정하세요."
            )
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def analyze(self, image_path: Path, prompt: str) -> tuple[str, dict[str, Any]]:
        if self._client is None:
            raise RuntimeError("GMS provider가 로드되지 않았습니다.")
        image_bytes, width, height = self._prepare_image(
            image_path,
            max_dimension=int(self._config.get("max_image_dimension", 1024)),
            max_bytes=int(self._config.get("max_image_bytes", 60_000)),
        )
        encoded = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:image/jpeg;base64,{encoded}"
        started_at = time.perf_counter()
        try:
            response = self._client.chat.completions.create(
                model=self.model_id,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": data_url,
                                "detail": str(self._config.get("image_detail", "auto")),
                            },
                        },
                    ],
                }],
                temperature=float(self._config.get("temperature", 0.0)),
                max_tokens=int(self._config.get("max_new_tokens", 512)),
            )
        except APIConnectionError as exc:
            cause = exc.__cause__
            details = f"{type(cause).__name__}: {cause}" if cause else str(exc)
            raise RuntimeError(f"GMS 연결 실패 ({details})") from exc
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        usage = response.usage
        return response.choices[0].message.content or "", {
            "latency_ms": latency_ms,
            "input_tokens": getattr(usage, "prompt_tokens", None),
            "output_tokens": getattr(usage, "completion_tokens", None),
            "original_image_bytes": image_path.stat().st_size,
            "sent_image_bytes": len(image_bytes),
            "sent_image_width": width,
            "sent_image_height": height,
            "image_detail": self._config.get("image_detail", "auto"),
        }

    @staticmethod
    def _prepare_image(
        image_path: Path,
        max_dimension: int = 1024,
        max_bytes: int = 60_000,
    ) -> tuple[bytes, int, int]:
        """Resize API payload without modifying the benchmark source image."""
        # The GMS proxy rejects larger base64 request bodies before it can read
        # the top-level model field. Keep the encoded request comfortably small.
        if max_dimension < 1 or max_bytes < 1:
            raise ValueError("Image size limits must be positive integers.")
        with Image.open(image_path) as source:
            image = source.convert("RGB")
            image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

            while True:
                for quality in (75, 65, 55, 45, 35, 25, 20):
                    buffer = BytesIO()
                    image.save(buffer, format="JPEG", quality=quality, optimize=True)
                    payload = buffer.getvalue()
                    if len(payload) <= max_bytes:
                        return payload, image.width, image.height

                if max(image.size) <= 512:
                    return payload, image.width, image.height
                next_size = tuple(max(1, int(value * 0.8)) for value in image.size)
                image = image.resize(next_size, Image.Resampling.LANCZOS)
