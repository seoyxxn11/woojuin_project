from __future__ import annotations

from typing import Any

from .integration import build_classification_text
from .models import ImageAnalysisResponse


def build_http_payload(response: ImageAnalysisResponse) -> dict[str, Any]:
    """백엔드 ImageTextExtractor가 사용할 HTTP 응답으로 변환한다."""
    payload = response.to_dict()
    payload["classificationText"] = (
        build_classification_text(response.result)
        if response.success and response.result is not None
        else None
    )
    return payload
