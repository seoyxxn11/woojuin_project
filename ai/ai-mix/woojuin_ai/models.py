from __future__ import annotations

import math
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class StrictModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


T = TypeVar("T")


class ApiResponse(StrictModel, Generic[T]):
    status: int
    message: str
    data: T


class MemoAiSource(StrictModel):
    title: str | None = Field(default=None, max_length=300)
    text: str = Field(min_length=1, max_length=50_000)


class UrlAiSource(StrictModel):
    title: str | None = Field(default=None, max_length=1_000)
    content: str | None = Field(default=None, max_length=50_000)
    description: str | None = Field(default=None, max_length=5_000)
    thumbnail_url: str | None = Field(default=None, max_length=4_000)

    @model_validator(mode="after")
    def has_text_signal(self) -> "UrlAiSource":
        if not any((self.title, self.content, self.description)):
            raise ValueError("title, content, description 중 하나는 필요합니다")
        return self


class ImageAiSource(StrictModel):
    vision_title: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=5_000)
    ocr_text: str | None = Field(default=None, max_length=50_000)
    objects: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("objects")
    @classmethod
    def valid_objects(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values if value.strip()]
        if len(set(normalized)) != len(normalized):
            raise ValueError("objects에는 중복 값을 넣을 수 없습니다")
        if any(len(value) > 100 for value in normalized):
            raise ValueError("objects 항목은 100자를 넘을 수 없습니다")
        return normalized

    @model_validator(mode="after")
    def has_signal(self) -> "ImageAiSource":
        if not any((self.vision_title, self.description, self.ocr_text, self.objects)):
            raise ValueError("이미지 분석 결과가 하나 이상 필요합니다")
        return self


class TitleSummaryOutput(StrictModel):
    title: str = Field(min_length=1, max_length=100)
    summary: str = Field(min_length=1, max_length=500)


class CandidateCategory(StrictModel):
    category_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=500)


class CategoryClassificationInput(StrictModel):
    title: str = Field(min_length=1, max_length=100)
    summary: str = Field(min_length=1, max_length=1_000)
    candidate_categories: list[CandidateCategory] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_categories(self) -> "CategoryClassificationInput":
        ids = [item.category_id for item in self.candidate_categories]
        names = [item.name for item in self.candidate_categories]
        if len(set(ids)) != len(ids):
            raise ValueError("candidateCategories의 categoryId는 중복될 수 없습니다")
        if len(set(names)) != len(names):
            raise ValueError("candidateCategories의 name은 중복될 수 없습니다")
        return self


class ClassifiedCategory(StrictModel):
    category_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=100)
    score: float = Field(ge=0, le=1)


class CategoryClassificationOutput(StrictModel):
    categories: list[ClassifiedCategory]
    threshold: float = Field(ge=0, le=1)
    fallback_used: bool


class _RawCategoryResult(StrictModel):
    categories: list[ClassifiedCategory] = Field(min_length=1, max_length=10)


class EmbeddingCategory(StrictModel):
    category_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=100)


class EmbeddingInput(StrictModel):
    item_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=100)
    summary: str = Field(min_length=1, max_length=1_000)
    categories: list[EmbeddingCategory] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def unique_categories(self) -> "EmbeddingInput":
        ids = [item.category_id for item in self.categories]
        if len(set(ids)) != len(ids):
            raise ValueError("categories의 categoryId는 중복될 수 없습니다")
        return self


class EmbeddingOutput(StrictModel):
    item_id: int
    embedding_model: str
    embedding_text_version: str
    input_hash: str
    dimensions: int = Field(gt=0)
    embedding: list[float]


class EmbeddingBatchInput(StrictModel):
    items: list[EmbeddingInput] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_items(self) -> "EmbeddingBatchInput":
        item_ids = [item.item_id for item in self.items]
        if len(set(item_ids)) != len(item_ids):
            raise ValueError("items의 itemId는 중복될 수 없습니다")
        return self


class EmbeddingBatchOutput(StrictModel):
    items: list[EmbeddingOutput]


class QueryEmbeddingInput(StrictModel):
    """검색어 임베딩 입력. 아이템(카테고리·제목·요약)과 달리 생 문장 그대로 임베딩한다 —
    사용자 검색어에는 그런 구조가 없고, 같은 모델이면 같은 벡터 공간에 떨어진다."""

    text: str = Field(min_length=1, max_length=500)


class QueryEmbeddingOutput(StrictModel):
    embedding_model: str
    dimensions: int = Field(gt=0)
    embedding: list[float]


class CoordinateEmbedding(StrictModel):
    item_id: int = Field(gt=0)
    embedding: list[float] = Field(min_length=1)

    @field_validator("embedding")
    @classmethod
    def finite_embedding(cls, values: list[float]) -> list[float]:
        if any(not math.isfinite(value) for value in values):
            raise ValueError("embedding에는 유한한 숫자만 사용할 수 있습니다")
        return values


class CoordinateReductionInput(StrictModel):
    items: list[CoordinateEmbedding] = Field(min_length=1)
    method: Literal["pca", "umap"] = "umap"
    n_neighbors: int = Field(default=15, ge=2, le=200)
    min_dist: float = Field(default=0.1, ge=0, le=1)
    random_state: int = 42
    target_radius: float = Field(default=25.0, gt=0, le=10_000)

    @model_validator(mode="after")
    def consistent_items(self) -> "CoordinateReductionInput":
        item_ids = [item.item_id for item in self.items]
        if len(set(item_ids)) != len(item_ids):
            raise ValueError("items의 itemId는 중복될 수 없습니다")
        dimensions = {len(item.embedding) for item in self.items}
        if len(dimensions) != 1:
            raise ValueError("모든 embedding의 차원은 같아야 합니다")
        return self


class ItemCoordinate(StrictModel):
    item_id: int
    x: float
    y: float
    z: float


class CoordinateReductionOutput(StrictModel):
    requested_method: Literal["pca", "umap"]
    method: Literal["pca", "umap"]
    coordinate_version: str
    item_count: int
    embedding_dimensions: int
    target_radius: float
    coordinates: list[ItemCoordinate]
    warnings: list[str]


class CategorySample(StrictModel):
    title: str = Field(min_length=1, max_length=100)
    summary: str = Field(min_length=1, max_length=1_000)


class CategoryDescriptionInput(StrictModel):
    category_id: int = Field(gt=0)
    category_name: str = Field(min_length=1, max_length=100)
    samples: list[CategorySample] = Field(default_factory=list, max_length=30)


class CategoryDescriptionOutput(StrictModel):
    category_id: int
    category_name: str
    description: str = Field(min_length=1, max_length=500)
    sample_count: int = Field(ge=0)


class _RawCategoryDescription(StrictModel):
    description: str = Field(min_length=1, max_length=500)


class HealthOutput(StrictModel):
    status: Literal["UP"]
    api_key_configured: bool
    chat_model: str
    embedding_model: str


RawCategoryResult = _RawCategoryResult
RawCategoryDescription = _RawCategoryDescription
