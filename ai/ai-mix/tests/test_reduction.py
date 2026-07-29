import pytest

from woojuin_ai.models import CoordinateReductionInput
from woojuin_ai.reduction import reduce_to_3d


def coordinate_input(method: str = "pca") -> CoordinateReductionInput:
    return CoordinateReductionInput.model_validate(
        {
            "method": method,
            "targetRadius": 25,
            "items": [
                {"itemId": 1, "embedding": [1.0, 0.0, 0.2, 0.1]},
                {"itemId": 2, "embedding": [0.8, 0.1, 0.3, 0.0]},
                {"itemId": 3, "embedding": [0.0, 1.0, 0.1, 0.2]},
                {"itemId": 4, "embedding": [0.1, 0.9, 0.0, 0.3]},
            ],
        }
    )


def test_pca_returns_three_scaled_coordinates():
    result = reduce_to_3d(coordinate_input())
    assert result.method == "pca"
    assert len(result.coordinates) == 4
    assert all(
        isinstance(value, float)
        for row in result.coordinates
        for value in (row.x, row.y, row.z)
    )
    largest_radius = max(
        (row.x**2 + row.y**2 + row.z**2) ** 0.5
        for row in result.coordinates
    )
    assert largest_radius == pytest.approx(25)


def test_small_umap_request_falls_back_to_pca():
    result = reduce_to_3d(coordinate_input("umap"))
    assert result.requested_method == "umap"
    assert result.method == "pca"
    assert result.warnings


def test_coordinate_version_is_independent_of_item_order():
    first = coordinate_input()
    reversed_value = first.model_copy(update={"items": list(reversed(first.items))})
    assert (
        reduce_to_3d(first).coordinate_version
        == reduce_to_3d(reversed_value).coordinate_version
    )


def test_single_item_is_placed_at_origin():
    value = CoordinateReductionInput.model_validate(
        {"method": "pca", "items": [{"itemId": 1, "embedding": [1, 2, 3]}]}
    )
    result = reduce_to_3d(value)
    point = result.coordinates[0]
    assert (point.x, point.y, point.z) == (0.0, 0.0, 0.0)
