from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from typing import Any

import numpy as np

from .prompt_builder import DEFAULT_TITLE_PATTERN


def build_embedding_text(item: dict[str, Any]) -> str:
    """메모의 의미 있는 제목과 본문을 임베딩 입력 한 건으로 만든다."""
    body = str(item.get("input", "")).strip()
    if not body:
        raise ValueError(f"{item.get('testId', '?')}: 메모 본문이 비어 있습니다")
    title = str(item.get("title", "")).strip()
    category = str(item.get("categoryName", "")).strip()
    parts = []
    if title and not DEFAULT_TITLE_PATTERN.fullmatch(title):
        parts.append(f"제목: {title}")
    parts.append(f"원본 본문: {body}")
    if category:
        parts.append(f"카테고리: {category}")
    return "\n".join(parts)


def input_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_embedding_vectors(response: Any, expected_count: int) -> list[list[float]]:
    """OpenAI SDK 응답을 index 순서로 정렬하고 벡터 형태를 검증한다."""
    data = _value(response, "data") or []
    indexed: list[tuple[int, list[float]]] = []
    for position, item in enumerate(data):
        raw_index = _value(item, "index")
        index = position if raw_index is None else int(raw_index)
        raw_vector = _value(item, "embedding")
        if not isinstance(raw_vector, (list, tuple)) or not raw_vector:
            raise ValueError(f"임베딩 응답 {index}번 벡터가 비어 있습니다")
        indexed.append((index, [float(value) for value in raw_vector]))
    indexed.sort(key=lambda pair: pair[0])
    if len(indexed) != expected_count:
        raise ValueError(
            f"임베딩 응답 개수가 요청과 다릅니다: 요청 {expected_count}, 응답 {len(indexed)}"
        )
    if [index for index, _ in indexed] != list(range(expected_count)):
        raise ValueError("임베딩 응답 index가 연속적이지 않습니다")
    dimensions = {len(vector) for _, vector in indexed}
    if len(dimensions) != 1:
        raise ValueError("임베딩 벡터 차원이 서로 다릅니다")
    return [vector for _, vector in indexed]


def embedding_usage(response: Any) -> dict[str, int | None]:
    usage = _value(response, "usage")
    return {
        "promptTokens": _optional_int(_value(usage, "prompt_tokens")),
        "totalTokens": _optional_int(_value(usage, "total_tokens")),
    }


def reduce_embeddings_to_3d(
    vectors: Sequence[Sequence[float]],
    *,
    n_neighbors: int = 15,
    min_dist: float = 0.1,
    metric: str = "cosine",
    random_state: int = 42,
    reducer_factory: Callable[..., Any] | None = None,
) -> tuple[list[list[float]], int]:
    """고차원 벡터를 UMAP 3차원 좌표로 축소한다."""
    if len(vectors) < 3:
        raise ValueError("3차원 UMAP 변환에는 메모가 최소 3개 필요합니다")
    if n_neighbors < 2:
        raise ValueError("n_neighbors는 2 이상이어야 합니다")
    if not 0 <= min_dist <= 1:
        raise ValueError("min_dist는 0 이상 1 이하여야 합니다")
    matrix = np.asarray(vectors, dtype=np.float32)
    if matrix.ndim != 2 or matrix.shape[1] == 0:
        raise ValueError("임베딩 벡터는 동일한 길이의 2차원 배열이어야 합니다")
    if not np.isfinite(matrix).all():
        raise ValueError("임베딩 벡터에 NaN 또는 무한대가 포함되어 있습니다")

    if reducer_factory is None:
        try:
            from umap import UMAP
        except ImportError as exc:
            raise RuntimeError(
                "umap-learn이 설치되어 있지 않습니다. "
                "'.\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt'를 실행하세요."
            ) from exc
        reducer_factory = UMAP

    effective_neighbors = min(n_neighbors, len(vectors) - 1)
    reducer = reducer_factory(
        n_components=3,
        n_neighbors=effective_neighbors,
        min_dist=min_dist,
        metric=metric,
        random_state=random_state,
        transform_seed=random_state,
        init="random",
    )
    coordinates = np.asarray(reducer.fit_transform(matrix), dtype=float)
    if coordinates.shape != (len(vectors), 3):
        raise ValueError(f"UMAP 결과 형태가 올바르지 않습니다: {coordinates.shape}")
    return coordinates.tolist(), effective_neighbors


def build_coordinate_rows(
    items: Sequence[dict[str, Any]], coordinates: Sequence[Sequence[float]]
) -> list[dict[str, Any]]:
    if len(items) != len(coordinates):
        raise ValueError("메모와 UMAP 좌표 개수가 다릅니다")
    rows: list[dict[str, Any]] = []
    for item, coordinate in zip(items, coordinates, strict=True):
        if len(coordinate) != 3:
            raise ValueError(f"{item.get('testId', '?')}: 좌표가 3차원이 아닙니다")
        rows.append({
            "embeddingId": item.get("embeddingId", item["testId"]),
            "testId": item["testId"],
            "id": item.get("id"),
            "title": item.get("title", ""),
            "type": item.get("type", "MEMO"),
            "categoryId": item.get("categoryId", ""),
            "categoryName": item.get("categoryName", ""),
            "sourcePath": item.get("sourcePath", ""),
            "x": float(coordinate[0]),
            "y": float(coordinate[1]),
            "z": float(coordinate[2]),
        })
    return rows


def _value(value: Any, name: str) -> Any:
    if value is None:
        return None
    return value.get(name) if isinstance(value, dict) else getattr(value, name, None)


def _optional_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
