from __future__ import annotations

import unittest

from run_benchmark import build_result_metadata


class BenchmarkResultTest(unittest.TestCase):
    def test_builds_nested_metadata_for_image_result(self) -> None:
        metadata = build_result_metadata(
            {
                "latency_ms": 1234.5,
                "input_tokens": 100,
                "output_tokens": 20,
            },
            {
                "latitude": 35.1,
                "longitude": 126.8,
                "captured_at": "2026-07-28T12:00:00",
                "source_format": "JPEG",
                "original_width": 4032,
                "original_height": 3024,
                "sent_width": 1536,
                "sent_height": 2048,
                "image_resized": True,
            },
        )

        self.assertEqual(metadata["latitude"], 35.1)
        self.assertEqual(metadata["longitude"], 126.8)
        self.assertEqual(metadata["captured_at"], "2026-07-28T12:00:00")
        self.assertEqual(
            set(metadata),
            {"latitude", "longitude", "captured_at"},
        )


if __name__ == "__main__":
    unittest.main()
