from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ImageAnalysisResult:
    title: str
    description: str
    tags: list[str]
    ocr_text: str
    objects: list[str]
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ImageAnalysisResponse:
    success: bool
    result: ImageAnalysisResult | None
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["result"] = self.result.to_dict() if self.result else None
        return payload

