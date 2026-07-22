from types import SimpleNamespace

import numpy as np
import pytest

import run_embedding_umap as runner
from src.embedding_pipeline import (
    build_coordinate_rows,
    build_embedding_text,
    extract_embedding_vectors,
    reduce_embeddings_to_3d,
)


def memo(title: str = "Redis 공부") -> dict:
    return {
        "testId": "TEXT-001",
        "title": title,
        "sourcePath": "학습·지식/001-Redis 공부.txt",
        "input": "Redis Streams의 소비자 그룹을 정리한다.",
        "expected": {"categories": ["학습·지식"]},
    }


def test_embedding_text_uses_meaningful_title_and_body():
    assert build_embedding_text(memo()) == (
        "제목: Redis 공부\n본문: Redis Streams의 소비자 그룹을 정리한다."
    )


def test_embedding_text_ignores_automatic_title():
    assert build_embedding_text(memo("텍스트-2026.07.20-1220")) == (
        "Redis Streams의 소비자 그룹을 정리한다."
    )


def test_embedding_response_is_sorted_by_index():
    response = SimpleNamespace(data=[
        SimpleNamespace(index=1, embedding=[3, 4]),
        SimpleNamespace(index=0, embedding=[1, 2]),
    ])
    assert extract_embedding_vectors(response, 2) == [[1.0, 2.0], [3.0, 4.0]]


def test_embedding_response_rejects_missing_item():
    response = SimpleNamespace(data=[SimpleNamespace(index=0, embedding=[1, 2])])
    with pytest.raises(ValueError, match="응답 개수"):
        extract_embedding_vectors(response, 2)


def test_umap_reduction_requests_three_dimensions_and_adjusts_neighbors():
    captured = {}

    class FakeReducer:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def fit_transform(self, matrix):
            captured["shape"] = matrix.shape
            return np.asarray([
                [index, index + 0.1, index + 0.2]
                for index in range(len(matrix))
            ])

    coordinates, effective_neighbors = reduce_embeddings_to_3d(
        [[1, 0], [0, 1], [1, 1]],
        n_neighbors=15,
        reducer_factory=FakeReducer,
    )
    assert captured["n_components"] == 3
    assert captured["metric"] == "cosine"
    assert captured["shape"] == (3, 2)
    assert effective_neighbors == 2
    assert coordinates[1] == pytest.approx([1.0, 1.1, 1.2])


def test_coordinate_rows_keep_category_and_source_metadata():
    rows = build_coordinate_rows([memo()], [[0.1, 0.2, 0.3]])
    assert rows == [{
        "testId": "TEXT-001",
        "title": "Redis 공부",
        "category": "학습·지식",
        "sourcePath": "학습·지식/001-Redis 공부.txt",
        "x": 0.1,
        "y": 0.2,
        "z": 0.3,
    }]


def test_request_embeddings_uses_openai_embeddings_endpoint():
    captured = {}

    class Embeddings:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                data=[SimpleNamespace(index=0, embedding=[0.1, 0.2])],
                usage=SimpleNamespace(prompt_tokens=3, total_tokens=3),
                _request_id="req-test",
            )

    client = SimpleNamespace(embeddings=Embeddings())
    vectors, usage, request_id = runner.request_embeddings(
        client,
        model="text-embedding-3-small",
        texts=["테스트 메모"],
        dimensions=None,
    )
    assert captured == {
        "model": "text-embedding-3-small",
        "input": ["테스트 메모"],
        "encoding_format": "float",
    }
    assert vectors == [[0.1, 0.2]]
    assert usage == {"promptTokens": 3, "totalTokens": 3}
    assert request_id == "req-test"


def test_dry_run_does_not_create_client_or_call_api(monkeypatch, capsys):
    monkeypatch.setattr(
        runner,
        "create_client",
        lambda _: pytest.fail("dry-run에서 API 클라이언트를 만들면 안 됩니다"),
    )
    assert runner.main(["--dry-run", "--limit", "3"]) == 0
    output = capsys.readouterr().out
    assert "메모: 3개" in output
    assert "API를 호출하지 않았" in output
