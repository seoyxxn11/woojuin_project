from __future__ import annotations

import unittest

from search import build_search_index


class SearchIndexTest(unittest.TestCase):
    def test_preserves_flattened_benchmark_metadata(self) -> None:
        records = [
            {
                "sample_id": "sample-1",
                "model": "qwen3-vl:8b-instruct",
                "ground_truth": {"file": "images/photo.jpg"},
                "latitude": 35.1,
                "longitude": 126.8,
                "captured_at": "2026-07-28T12:00:00",
                "source_format": "JPEG",
                "original_width": 4032,
                "original_height": 3024,
                "result": {
                    "title": "사진",
                    "description": "설명",
                    "tags": [],
                    "ocr_text": "",
                    "objects": [],
                    "confidence": 0.9,
                },
                "error": None,
            }
        ]

        item = build_search_index(records)[0]

        self.assertEqual(item["metadata"]["latitude"], 35.1)
        self.assertEqual(item["metadata"]["longitude"], 126.8)
        self.assertEqual(item["metadata"]["captured_at"], "2026-07-28T12:00:00")
        self.assertEqual(
            set(item["metadata"]),
            {"latitude", "longitude", "captured_at"},
        )

    def test_keeps_null_when_source_exif_is_missing(self) -> None:
        records = [
            {
                "sample_id": "sample-2",
                "ground_truth": {"file": "images/screenshot.png"},
                "result": {
                    "title": "스크린샷",
                    "description": "설명",
                    "tags": [],
                    "ocr_text": "텍스트",
                    "objects": [],
                    "confidence": 0.8,
                },
                "error": None,
            }
        ]

        metadata = build_search_index(records)[0]["metadata"]

        self.assertIsNone(metadata["latitude"])
        self.assertIsNone(metadata["longitude"])
        self.assertIsNone(metadata["captured_at"])


if __name__ == "__main__":
    unittest.main()
