from __future__ import annotations

import json
import socket
import tempfile
import urllib.error
from pathlib import Path
from typing import Any

from providers.base import ImageModelProvider

from .errors import ImageAiError, ImageAiErrorCode
from .models import ImageAnalysisResponse
from .processing import extract_json_object, normalize_result, prepare_image


class ImageAnalysisService:
    def __init__(
        self,
        provider: ImageModelProvider,
        prompt: str,
        *,
        max_attempts: int = 2,
        max_dimension: int = 2048,
    ) -> None:
        self.provider = provider
        self.prompt = prompt
        self.max_attempts = max(1, max_attempts)
        self.max_dimension = max_dimension

    def validate_environment(self) -> None:
        try:
            self.provider.load()
        except RuntimeError as exc:
            message = str(exc)
            code = (
                ImageAiErrorCode.MODEL_NOT_INSTALLED
                if "설치되지 않았습니다" in message
                else ImageAiErrorCode.OLLAMA_UNAVAILABLE
            )
            raise ImageAiError(code, message, retryable=code == ImageAiErrorCode.OLLAMA_UNAVAILABLE) from exc

    def warmup(self) -> dict[str, Any]:
        try:
            return self.provider.warmup()
        except RuntimeError as exc:
            message = str(exc)
            code = (
                ImageAiErrorCode.MODEL_NOT_INSTALLED
                if "설치되지 않았습니다" in message
                else ImageAiErrorCode.OLLAMA_UNAVAILABLE
            )
            raise ImageAiError(
                code,
                message,
                retryable=code == ImageAiErrorCode.OLLAMA_UNAVAILABLE,
            ) from exc

    def analyze(self, image_path: Path) -> ImageAnalysisResponse:
        try:
            prepared, preprocessing = prepare_image(
                image_path,
                max_dimension=self.max_dimension,
            )
            last_error: ImageAiError | None = None
            for attempt in range(1, self.max_attempts + 1):
                try:
                    with tempfile.TemporaryDirectory() as directory:
                        prepared_path = Path(directory) / "prepared.jpg"
                        prepared_path.write_bytes(prepared)
                        raw, metadata = self.provider.analyze(prepared_path, self.prompt)
                    result = normalize_result(extract_json_object(raw))
                    return ImageAnalysisResponse(
                        success=True,
                        result=result,
                        metadata={
                            **metadata,
                            **preprocessing,
                            "attempts": attempt,
                            "model": self.provider.model_id,
                        },
                    )
                except ImageAiError as exc:
                    last_error = exc
                    if not exc.retryable or attempt >= self.max_attempts:
                        raise
                except (TimeoutError, socket.timeout) as exc:
                    last_error = ImageAiError(
                        ImageAiErrorCode.MODEL_TIMEOUT,
                        "이미지 모델 요청 시간이 초과되었습니다.",
                        retryable=True,
                    )
                    if attempt >= self.max_attempts:
                        raise last_error from exc
                except (urllib.error.URLError, ConnectionError) as exc:
                    last_error = ImageAiError(
                        ImageAiErrorCode.OLLAMA_UNAVAILABLE,
                        "Ollama에 연결할 수 없습니다.",
                        retryable=True,
                    )
                    if attempt >= self.max_attempts:
                        raise last_error from exc
                except RuntimeError as exc:
                    message = str(exc)
                    if "응답이 비어" in message:
                        last_error = ImageAiError(
                            ImageAiErrorCode.EMPTY_MODEL_RESPONSE,
                            message,
                            retryable=True,
                        )
                    elif "Ollama" in message:
                        last_error = ImageAiError(
                            ImageAiErrorCode.OLLAMA_UNAVAILABLE,
                            message,
                            retryable=True,
                        )
                    else:
                        raise
                    if attempt >= self.max_attempts:
                        raise last_error from exc
            raise last_error or ImageAiError(
                ImageAiErrorCode.INTERNAL_ERROR,
                "이미지 분석에 실패했습니다.",
            )
        except ImageAiError as exc:
            return ImageAnalysisResponse(
                success=False,
                result=None,
                error_code=exc.code.value,
                error_message=str(exc),
                retryable=exc.retryable,
            )
        except (json.JSONDecodeError, RuntimeError) as exc:
            return self._failure(ImageAiErrorCode.INTERNAL_ERROR, str(exc))

    @staticmethod
    def _failure(
        code: ImageAiErrorCode,
        message: str,
        *,
        retryable: bool = False,
    ) -> ImageAnalysisResponse:
        return ImageAnalysisResponse(
            success=False,
            result=None,
            error_code=code.value,
            error_message=message,
            retryable=retryable,
        )
