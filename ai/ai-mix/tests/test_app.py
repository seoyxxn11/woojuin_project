from fastapi.testclient import TestClient

import app as application
from woojuin_ai.config import Settings
from woojuin_ai.models import (
    EmbeddingBatchOutput,
    EmbeddingOutput,
    TitleSummaryOutput,
)


class FakeService:
    def create_title_summary(self, source_type, source):
        return TitleSummaryOutput(title="회의 메모", summary="검색 기능을 완료한다.")

    def create_embeddings(self, items):
        return EmbeddingBatchOutput(
            items=[
                EmbeddingOutput(
                    itemId=item.item_id,
                    embeddingModel="test-embedding",
                    embeddingTextVersion="v1",
                    inputHash="sha256:test",
                    dimensions=3,
                    embedding=[0.1, 0.2, 0.3],
                )
                for item in items
            ]
        )


application.app.dependency_overrides[application.get_service] = lambda: FakeService()
application.app.dependency_overrides[application.get_settings] = lambda: Settings(
    api_key=None
)
client = TestClient(application.app)


def test_health_uses_common_response_envelope():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == 200
    assert response.json()["data"]["apiKeyConfigured"] is False


def test_memo_endpoint_has_independent_contract():
    response = client.post(
        "/v1/title-summary/memo",
        json={"title": "회의 메모", "text": "검색 기능을 완료한다."},
    )
    assert response.status_code == 200
    assert response.json()["data"] == {
        "title": "회의 메모",
        "summary": "검색 기능을 완료한다.",
    }


def test_validation_error_uses_common_response_envelope():
    response = client.post(
        "/v1/title-summary/memo",
        json={"title": "빈 메모", "text": ""},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["status"] == 422
    assert body["data"] is None


def test_single_embedding_endpoint_unwraps_batch_result():
    response = client.post(
        "/v1/embeddings",
        json={
            "itemId": 101,
            "title": "소바",
            "summary": "국물 소바다.",
            "categories": [{"categoryId": 5, "name": "음식·맛집"}],
        },
    )
    assert response.status_code == 200
    assert response.json()["data"]["itemId"] == 101
