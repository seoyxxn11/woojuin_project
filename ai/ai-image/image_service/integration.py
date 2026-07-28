from __future__ import annotations

from typing import Any

from .models import ImageAnalysisResult


def build_classification_text(result: ImageAnalysisResult) -> str:
    """이미지 추출 결과를 공통 텍스트 분류 입력으로 변환한다."""
    sections = [
        ("이미지 설명", result.description),
        ("OCR 텍스트", result.ocr_text),
        ("태그", ", ".join(result.tags)),
        ("주요 객체", ", ".join(result.objects)),
    ]
    return "\n".join(
        f"{label}: {value}"
        for label, value in sections
        if value.strip()
    )


def build_ai_analysis_request(
    result: ImageAnalysisResult,
    candidate_categories: list[str],
) -> dict[str, Any]:
    """백엔드 AiAnalysisRequest(title, text, candidateCategories)와 맞춘다."""
    categories = [
        category.strip()
        for category in candidate_categories
        if isinstance(category, str) and category.strip()
    ]
    return {
        "title": result.title,
        "text": build_classification_text(result),
        "candidateCategories": list(dict.fromkeys(categories)),
    }
