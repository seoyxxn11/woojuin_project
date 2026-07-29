import pytest
from pydantic import ValidationError

from woojuin_ai.models import (
    CategoryClassificationInput,
    CoordinateReductionInput,
    ImageAiSource,
    UrlAiSource,
)


def test_url_requires_at_least_one_text_signal():
    with pytest.raises(ValidationError, match="하나는 필요"):
        UrlAiSource(title=None, content=None, description=None)


def test_image_requires_analysis_signal():
    with pytest.raises(ValidationError, match="하나 이상"):
        ImageAiSource(
            visionTitle=None,
            description=None,
            ocrText=None,
            objects=[],
        )


def test_category_candidates_require_unique_ids():
    with pytest.raises(ValidationError, match="categoryId"):
        CategoryClassificationInput.model_validate(
            {
                "title": "소바",
                "summary": "국물 소바",
                "candidateCategories": [
                    {"categoryId": 5, "name": "음식", "description": "음식"},
                    {"categoryId": 5, "name": "여행", "description": "여행"},
                ],
            }
        )


def test_coordinates_require_equal_embedding_dimensions():
    with pytest.raises(ValidationError, match="차원"):
        CoordinateReductionInput.model_validate(
            {
                "items": [
                    {"itemId": 1, "embedding": [1, 2]},
                    {"itemId": 2, "embedding": [1, 2, 3]},
                ]
            }
        )
