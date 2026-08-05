from __future__ import annotations

import hashlib
from typing import Any, Literal

from pydantic import ValidationError

from .client import OpenRouterClient
from .config import Settings
from .models import (
    CategoryClassificationInput,
    CategoryClassificationOutput,
    CategoryDescriptionInput,
    CategoryDescriptionOutput,
    ClassifiedCategory,
    EmbeddingBatchOutput,
    EmbeddingInput,
    EmbeddingOutput,
    ImageAiSource,
    MemoAiSource,
    QueryEmbeddingInput,
    QueryEmbeddingOutput,
    RawCategoryDescription,
    RawCategoryResult,
    TitleSummaryOutput,
    UrlAiSource,
)
from .prompts import (
    category_classification_messages,
    category_description_messages,
    title_summary_messages,
)
from .reduction import reduce_to_3d


EMBEDDING_TEXT_VERSION = "title-summary-categories-v2"


class InvalidModelResponse(RuntimeError):
    """모델 응답이 애플리케이션 계약을 위반한 경우."""


class AiMixService:
    def __init__(self, client: OpenRouterClient, settings: Settings) -> None:
        self.client = client
        self.settings = settings

    def create_title_summary(
        self,
        source_type: Literal["memo", "url", "image"],
        source: MemoAiSource | UrlAiSource | ImageAiSource,
    ) -> TitleSummaryOutput:
        raw = self.client.chat_json(
            messages=title_summary_messages(source_type, source),
            schema=TitleSummaryOutput.model_json_schema(by_alias=True),
            schema_name=f"{source_type}_title_summary",
        )
        return self._validate(TitleSummaryOutput, raw)

    def classify_categories(
        self,
        value: CategoryClassificationInput,
    ) -> CategoryClassificationOutput:
        raw = self.client.chat_json(
            messages=category_classification_messages(value),
            schema=RawCategoryResult.model_json_schema(by_alias=True),
            schema_name="category_classification",
        )
        result = self._validate(RawCategoryResult, raw)
        candidates = {
            item.category_id: item
            for item in value.candidate_categories
        }
        unique: dict[int, ClassifiedCategory] = {}
        for prediction in result.categories:
            candidate = candidates.get(prediction.category_id)
            if candidate is None:
                raise InvalidModelResponse(
                    f"모델이 후보에 없는 categoryId를 반환했습니다: {prediction.category_id}"
                )
            if prediction.name != candidate.name:
                raise InvalidModelResponse(
                    f"모델의 categoryId와 name이 일치하지 않습니다: {prediction.category_id}"
                )
            previous = unique.get(prediction.category_id)
            if previous is None or prediction.score > previous.score:
                unique[prediction.category_id] = prediction

        ranked = sorted(unique.values(), key=lambda item: item.score, reverse=True)
        selected = [
            item
            for item in ranked
            if item.score >= self.settings.category_score_threshold
        ][: self.settings.category_max_results]
        fallback_used = False
        if not selected:
            if not ranked:
                raise InvalidModelResponse("모델이 카테고리 후보를 반환하지 않았습니다")
            selected = ranked[:1]
            fallback_used = True
        return CategoryClassificationOutput(
            categories=selected,
            threshold=self.settings.category_score_threshold,
            fallback_used=fallback_used,
        )

    def create_embeddings(
        self,
        items: list[EmbeddingInput],
    ) -> EmbeddingBatchOutput:
        texts = [build_embedding_text(item) for item in items]
        model, vectors = self.client.create_embeddings(texts)
        outputs = [
            EmbeddingOutput(
                item_id=item.item_id,
                embedding_model=model,
                embedding_text_version=EMBEDDING_TEXT_VERSION,
                input_hash=embedding_input_hash(text),
                dimensions=len(vector),
                embedding=vector,
            )
            for item, text, vector in zip(items, texts, vectors, strict=True)
        ]
        return EmbeddingBatchOutput(items=outputs)

    def embed_query(self, value: QueryEmbeddingInput) -> QueryEmbeddingOutput:
        model, vectors = self.client.create_embeddings([value.text])
        return QueryEmbeddingOutput(
            embedding_model=model,
            dimensions=len(vectors[0]),
            embedding=vectors[0],
        )

    @staticmethod
    def reduce_coordinates(value: Any):
        return reduce_to_3d(value)

    def create_category_description(
        self,
        value: CategoryDescriptionInput,
    ) -> CategoryDescriptionOutput:
        raw = self.client.chat_json(
            messages=category_description_messages(value),
            schema=RawCategoryDescription.model_json_schema(by_alias=True),
            schema_name="category_description",
        )
        result = self._validate(RawCategoryDescription, raw)
        return CategoryDescriptionOutput(
            category_id=value.category_id,
            category_name=value.category_name,
            description=result.description,
            sample_count=len(value.samples),
        )

    @staticmethod
    def _validate(model: type[Any], raw: dict[str, Any]):
        try:
            return model.model_validate(raw)
        except ValidationError as exc:
            raise InvalidModelResponse(
                "모델 응답이 약속된 JSON 스키마를 만족하지 않습니다"
            ) from exc


def build_embedding_text(value: EmbeddingInput) -> str:
    """검색어 임베딩(생 문장)과 같은 평문 형태로 조립한다.

    v1은 "카테고리:/제목:/요약:" 라벨을 붙였는데, 모든 아이템이 같은 보일러플레이트를
    공유해 서로 뭉치고 평문인 검색어와는 체계적으로 멀어졌다 — 실측에서 관련 쿼리
    0.50~0.70 vs 무관 쿼리 0.72~0.77로 변별 구간이 2%p까지 좁아진 원인. 카테고리명은
    단어 수준 검색어("맛집")와의 연결 신호라 라벨 없이 꼬리에만 남긴다.
    """
    category_names = [
        item.name
        for item in sorted(value.categories, key=lambda item: item.category_id)
    ]
    return f"{value.title}\n{value.summary}\n{', '.join(category_names)}"


def embedding_input_hash(text: str) -> str:
    payload = f"{EMBEDDING_TEXT_VERSION}\0{text}".encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()
