import json

import pytest

from woojuin_ai.config import Settings
from woojuin_ai.models import (
    CategoryClassificationInput,
    CategoryDescriptionInput,
    EmbeddingInput,
    ImageAiSource,
    MemoAiSource,
    QueryEmbeddingInput,
    UrlAiSource,
)
from woojuin_ai.service import (
    AiMixService,
    InvalidModelResponse,
    build_embedding_text,
)


class FakeClient:
    def __init__(self, chat_results=None):
        self.chat_results = list(chat_results or [])
        self.messages = []
        self.texts = []

    def chat_json(self, **kwargs):
        self.messages.append(kwargs["messages"])
        return self.chat_results.pop(0)

    def create_embeddings(self, texts):
        self.texts = texts
        return "openai/text-embedding-3-small", [
            [float(index), 0.5, -0.5]
            for index, _text in enumerate(texts, start=1)
        ]


def settings(**overrides) -> Settings:
    defaults = {
        "api_key": "test-key",
        "category_score_threshold": 0.65,
        "category_max_results": 2,
    }
    defaults.update(overrides)
    return Settings(**defaults)


@pytest.mark.parametrize(
    ("source_type", "source"),
    [
        ("memo", MemoAiSource(title="회의", text="검색 기능을 완료한다.")),
        (
            "url",
            UrlAiSource(
                title="Apple Music",
                content=None,
                description=None,
            ),
        ),
        (
            "image",
            ImageAiSource(
                visionTitle="소바",
                description="소바 국물면",
                ocrText=None,
                objects=["면"],
            ),
        ),
    ],
)
def test_title_summary_sources_are_independent(source_type, source):
    client = FakeClient([{"title": "최종 제목", "summary": "최종 요약이다."}])
    service = AiMixService(client, settings())
    result = service.create_title_summary(source_type, source)
    assert result.title == "최종 제목"
    assert result.summary == "최종 요약이다."


def classification_input() -> CategoryClassificationInput:
    return CategoryClassificationInput.model_validate(
        {
            "title": "소바",
            "summary": "참깨와 파가 올라간 국물 소바다.",
            "candidateCategories": [
                {
                    "categoryId": 5,
                    "name": "음식·맛집",
                    "description": "음식과 식당",
                },
                {
                    "categoryId": 6,
                    "name": "여행·장소",
                    "description": "여행과 장소",
                },
            ],
        }
    )


def test_category_classification_applies_threshold_and_order():
    client = FakeClient(
        [
            {
                "categories": [
                    {"categoryId": 6, "name": "여행·장소", "score": 0.7},
                    {"categoryId": 5, "name": "음식·맛집", "score": 0.95},
                ]
            }
        ]
    )
    result = AiMixService(client, settings()).classify_categories(
        classification_input()
    )
    assert [item.category_id for item in result.categories] == [5, 6]
    assert result.fallback_used is False


def test_category_classification_keeps_top_one_below_threshold():
    client = FakeClient(
        [
            {
                "categories": [
                    {"categoryId": 6, "name": "여행·장소", "score": 0.4},
                    {"categoryId": 5, "name": "음식·맛집", "score": 0.5},
                ]
            }
        ]
    )
    result = AiMixService(client, settings()).classify_categories(
        classification_input()
    )
    assert [item.category_id for item in result.categories] == [5]
    assert result.fallback_used is True


def test_category_classification_rejects_unknown_candidate():
    client = FakeClient(
        [
            {
                "categories": [
                    {"categoryId": 999, "name": "새 카테고리", "score": 0.9}
                ]
            }
        ]
    )
    with pytest.raises(InvalidModelResponse, match="후보에 없는"):
        AiMixService(client, settings()).classify_categories(
            classification_input()
        )


def embedding_input(item_id=101) -> EmbeddingInput:
    return EmbeddingInput.model_validate(
        {
            "itemId": item_id,
            "title": "소바 국물면",
            "summary": "참깨와 파가 올라간 국물 소바다.",
            "categories": [
                {"categoryId": 6, "name": "여행·장소"},
                {"categoryId": 5, "name": "음식·맛집"},
            ],
        }
    )


def test_embedding_text_is_category_title_summary_and_sorted():
    assert build_embedding_text(embedding_input()) == (
        "카테고리: 음식·맛집, 여행·장소\n"
        "제목: 소바 국물면\n"
        "요약: 참깨와 파가 올라간 국물 소바다."
    )


def test_embedding_batch_calls_api_once_and_returns_hashes():
    client = FakeClient()
    result = AiMixService(client, settings()).create_embeddings(
        [embedding_input(101), embedding_input(102)]
    )
    assert len(client.texts) == 2
    assert [item.item_id for item in result.items] == [101, 102]
    assert result.items[0].dimensions == 3
    assert result.items[0].input_hash.startswith("sha256:")


def test_query_embedding_sends_raw_text():
    client = FakeClient()
    result = AiMixService(client, settings()).embed_query(
        QueryEmbeddingInput(text="일식 코스 요리")
    )
    # 아이템 임베딩과 달리 "카테고리:/제목:/요약:" 틀 없이 검색어 원문 그대로 보낸다.
    assert client.texts == ["일식 코스 요리"]
    assert result.embedding_model == "openai/text-embedding-3-small"
    assert result.dimensions == 3
    assert result.embedding == [1.0, 0.5, -0.5]


def test_category_description_supports_empty_samples():
    client = FakeClient([{"description": "음식과 식당 정보를 모아두는 범주"}])
    value = CategoryDescriptionInput(
        categoryId=5,
        categoryName="음식·맛집",
        samples=[],
    )
    result = AiMixService(client, settings()).create_category_description(value)
    assert result.category_id == 5
    assert result.sample_count == 0


def test_url_thumbnail_is_not_sent_to_chat_model():
    client = FakeClient([{"title": "제목", "summary": "요약"}])
    source = UrlAiSource(
        title="제목",
        content=None,
        description=None,
        thumbnailUrl="https://example.com/secret.jpg",
    )
    AiMixService(client, settings()).create_title_summary("url", source)
    serialized = json.dumps(client.messages, ensure_ascii=False)
    assert "secret.jpg" not in serialized
