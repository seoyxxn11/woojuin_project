from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np

from .models import (
    CoordinateReductionInput,
    CoordinateReductionOutput,
    ItemCoordinate,
)


def reduce_to_3d(value: CoordinateReductionInput) -> CoordinateReductionOutput:
    matrix = np.asarray([item.embedding for item in value.items], dtype=np.float64)
    warnings: list[str] = []
    effective_method = value.method

    if value.method == "umap" and len(value.items) < 5:
        warnings.append("UMAP은 안정적인 3차원 축소에 표본이 부족해 PCA를 사용했습니다.")
        effective_method = "pca"

    if effective_method == "umap":
        try:
            coordinates = _umap_coordinates(
                matrix,
                n_neighbors=min(value.n_neighbors, len(value.items) - 1),
                min_dist=value.min_dist,
                random_state=value.random_state,
            )
        except ImportError:
            warnings.append("umap-learn이 설치되지 않아 PCA를 사용했습니다.")
            effective_method = "pca"
            coordinates = _pca_coordinates(matrix)
    else:
        coordinates = _pca_coordinates(matrix)

    coordinates = _center_and_scale(coordinates, value.target_radius)
    if not np.isfinite(coordinates).all():
        raise ValueError("3차원 좌표 계산 결과가 유한하지 않습니다")

    rows = [
        ItemCoordinate(
            item_id=item.item_id,
            x=float(point[0]),
            y=float(point[1]),
            z=float(point[2]),
        )
        for item, point in zip(value.items, coordinates, strict=True)
    ]
    return CoordinateReductionOutput(
        requested_method=value.method,
        method=effective_method,
        coordinate_version=_coordinate_version(value, effective_method),
        item_count=len(value.items),
        embedding_dimensions=matrix.shape[1],
        target_radius=value.target_radius,
        coordinates=rows,
        warnings=warnings,
    )


def _pca_coordinates(matrix: np.ndarray) -> np.ndarray:
    centered = matrix - matrix.mean(axis=0, keepdims=True)
    if len(matrix) == 1 or not np.any(centered):
        return np.zeros((len(matrix), 3), dtype=np.float64)

    _u, _singular_values, components = np.linalg.svd(centered, full_matrices=False)
    component_count = min(3, components.shape[0])
    selected = components[:component_count].copy()

    # SVD의 부호는 수학적으로 임의이므로 가장 큰 절댓값의 loading이 양수가 되게 고정한다.
    for index in range(component_count):
        pivot = int(np.argmax(np.abs(selected[index])))
        if selected[index, pivot] < 0:
            selected[index] *= -1

    coordinates = centered @ selected.T
    if component_count < 3:
        coordinates = np.pad(
            coordinates,
            ((0, 0), (0, 3 - component_count)),
            mode="constant",
        )
    return coordinates


def _umap_coordinates(
    matrix: np.ndarray,
    *,
    n_neighbors: int,
    min_dist: float,
    random_state: int,
) -> np.ndarray:
    from umap import UMAP

    reducer = UMAP(
        n_components=3,
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        metric="cosine",
        random_state=random_state,
        transform_seed=random_state,
    )
    return np.asarray(reducer.fit_transform(matrix), dtype=np.float64)


def _center_and_scale(coordinates: np.ndarray, target_radius: float) -> np.ndarray:
    centered = coordinates - coordinates.mean(axis=0, keepdims=True)
    radii = np.linalg.norm(centered, axis=1)
    largest = float(radii.max()) if len(radii) else 0.0
    if largest == 0:
        return centered
    return centered * (target_radius / largest)


def _coordinate_version(
    value: CoordinateReductionInput,
    effective_method: str,
) -> str:
    items = sorted(value.items, key=lambda item: item.item_id)
    payload: dict[str, Any] = {
        "version": "coordinate-v1",
        "requestedMethod": value.method,
        "method": effective_method,
        "nNeighbors": value.n_neighbors,
        "minDist": value.min_dist,
        "randomState": value.random_state,
        "targetRadius": value.target_radius,
        "items": [
            {"itemId": item.item_id, "embedding": item.embedding}
            for item in items
        ],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "coordinate-v1:" + hashlib.sha256(encoded).hexdigest()
