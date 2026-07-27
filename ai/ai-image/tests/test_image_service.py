from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from PIL import Image

from image_service import ImageAnalysisService
from image_service.processing import (
    extract_image_metadata,
    extract_json_object,
    normalize_result,
    prepare_image,
)
from providers.base import ImageModelProvider


class FakeProvider(ImageModelProvider):
    @property
    def model_id(self) -> str:
        return "fake-vision"

    def load(self) -> None:
        return None

    def analyze(self, image_path: Path, prompt: str) -> tuple[str, dict[str, Any]]:
        return (
            json.dumps(
                {
                    "title": "테스트 이미지",
                    "description": "테스트 설명",
                    "tags": ["테스트", "테스트"],
                    "ocr_text": "",
                    "objects": ["이미지"],
                    "confidence": 0.9,
                },
                ensure_ascii=False,
            ),
            {"latency_ms": 1},
        )


class ProcessingTest(unittest.TestCase):
    def test_extracts_json_from_markdown(self) -> None:
        payload = {
            "title": "제목",
            "description": "설명",
            "tags": ["태그"],
            "ocr_text": "",
            "objects": ["객체"],
            "confidence": 0.9,
        }
        parsed = extract_json_object(f"```json\n{json.dumps(payload, ensure_ascii=False)}\n```")
        self.assertEqual(parsed["title"], "제목")

    def test_normalizes_duplicate_lists_and_ocr(self) -> None:
        result = normalize_result(
            {
                "title": "  제목  ",
                "description": " 설명 ",
                "tags": ["태그", "태그", " 두 번째 "],
                "ocr_text": "문구\n문구\n두 번째",
                "objects": ["객체", "객체"],
                "confidence": 1.2,
            }
        )
        self.assertEqual(result.tags, ["태그", "두 번째"])
        self.assertEqual(result.ocr_text, "문구\n두 번째")
        self.assertEqual(result.objects, ["객체"])
        self.assertEqual(result.confidence, 1.0)

    def test_prepares_and_resizes_image(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large.png"
            Image.new("RGBA", (3000, 1000), (255, 0, 0, 128)).save(path)
            prepared, metadata = prepare_image(path, max_dimension=1000)
        self.assertTrue(prepared.startswith(b"\xff\xd8"))
        self.assertEqual(metadata["sent_width"], 1000)
        self.assertEqual(metadata["sent_height"], 333)
        self.assertTrue(metadata["image_resized"])

    def test_service_returns_common_response(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image.jpg"
            Image.new("RGB", (100, 100), "white").save(path)
            response = ImageAnalysisService(FakeProvider(), "prompt").analyze(path)
        self.assertTrue(response.success)
        self.assertEqual(response.result.tags, ["테스트"])
        self.assertEqual(response.metadata["model"], "fake-vision")

    def test_metadata_is_null_without_exif(self) -> None:
        image = Image.new("RGB", (100, 100), "white")
        metadata = extract_image_metadata(image)
        self.assertIsNone(metadata["latitude"])
        self.assertIsNone(metadata["longitude"])
        self.assertIsNone(metadata["captured_at"])


if __name__ == "__main__":
    unittest.main()
