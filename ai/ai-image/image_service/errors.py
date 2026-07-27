from __future__ import annotations

from enum import StrEnum


class ImageAiErrorCode(StrEnum):
    IMAGE_NOT_FOUND = "IMAGE_NOT_FOUND"
    UNSUPPORTED_IMAGE = "UNSUPPORTED_IMAGE"
    IMAGE_TOO_LARGE = "IMAGE_TOO_LARGE"
    IMAGE_DECODE_FAILED = "IMAGE_DECODE_FAILED"
    OLLAMA_UNAVAILABLE = "OLLAMA_UNAVAILABLE"
    MODEL_NOT_INSTALLED = "MODEL_NOT_INSTALLED"
    MODEL_TIMEOUT = "MODEL_TIMEOUT"
    EMPTY_MODEL_RESPONSE = "EMPTY_MODEL_RESPONSE"
    INVALID_MODEL_RESPONSE = "INVALID_MODEL_RESPONSE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ImageAiError(RuntimeError):
    def __init__(
        self,
        code: ImageAiErrorCode,
        message: str,
        *,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable

