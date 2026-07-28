from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from PIL import Image

from image_service import (
    ImageAnalysisService,
    build_ai_analysis_request,
    build_classification_text,
)
from image_service.errors import ImageAiError
from image_service.models import ImageAnalysisResult
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


class SequenceProvider(FakeProvider):
    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = outcomes
        self.calls = 0

    def analyze(self, image_path: Path, prompt: str) -> tuple[str, dict[str, Any]]:
        outcome = self.outcomes[self.calls]
        self.calls += 1
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


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

    def test_retries_timeout_and_returns_success(self) -> None:
        valid = FakeProvider().analyze(Path("unused"), "prompt")
        provider = SequenceProvider([TimeoutError(), valid])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image.jpg"
            Image.new("RGB", (100, 100), "white").save(path)
            response = ImageAnalysisService(provider, "prompt", max_attempts=2).analyze(path)
        self.assertTrue(response.success)
        self.assertEqual(provider.calls, 2)
        self.assertEqual(response.metadata["attempts"], 2)

    def test_returns_timeout_after_retry_limit(self) -> None:
        provider = SequenceProvider([TimeoutError(), TimeoutError()])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image.jpg"
            Image.new("RGB", (100, 100), "white").save(path)
            response = ImageAnalysisService(provider, "prompt", max_attempts=2).analyze(path)
        self.assertFalse(response.success)
        self.assertEqual(provider.calls, 2)
        self.assertEqual(response.error_code, "MODEL_TIMEOUT")
        self.assertTrue(response.retryable)

    def test_retries_empty_response_and_returns_error(self) -> None:
        provider = SequenceProvider(
            [
                RuntimeError("Ollama 모델 응답이 비어 있습니다."),
                RuntimeError("Ollama 모델 응답이 비어 있습니다."),
            ]
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image.jpg"
            Image.new("RGB", (100, 100), "white").save(path)
            response = ImageAnalysisService(provider, "prompt", max_attempts=2).analyze(path)
        self.assertFalse(response.success)
        self.assertEqual(provider.calls, 2)
        self.assertEqual(response.error_code, "EMPTY_MODEL_RESPONSE")

    def test_retries_invalid_json_and_returns_success(self) -> None:
        valid = FakeProvider().analyze(Path("unused"), "prompt")
        provider = SequenceProvider([("not-json", {}), valid])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image.jpg"
            Image.new("RGB", (100, 100), "white").save(path)
            response = ImageAnalysisService(provider, "prompt", max_attempts=2).analyze(path)
        self.assertTrue(response.success)
        self.assertEqual(provider.calls, 2)

    def test_returns_not_found_without_calling_model(self) -> None:
        provider = SequenceProvider([])
        response = ImageAnalysisService(provider, "prompt").analyze(
            Path("missing-image.jpg")
        )
        self.assertFalse(response.success)
        self.assertEqual(response.error_code, "IMAGE_NOT_FOUND")
        self.assertFalse(response.retryable)
        self.assertEqual(provider.calls, 0)

    def test_rejects_unsupported_image(self) -> None:
        provider = SequenceProvider([])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image.gif"
            Image.new("RGB", (10, 10), "white").save(path, format="GIF")
            response = ImageAnalysisService(provider, "prompt").analyze(path)
        self.assertFalse(response.success)
        self.assertEqual(response.error_code, "UNSUPPORTED_IMAGE")
        self.assertEqual(provider.calls, 0)

    def test_validate_environment_preserves_model_not_installed(self) -> None:
        class MissingModelProvider(FakeProvider):
            def load(self) -> None:
                raise RuntimeError("Ollama 모델이 설치되지 않았습니다: fake-vision")

        with self.assertRaises(ImageAiError) as context:
            ImageAnalysisService(MissingModelProvider(), "prompt").validate_environment()
        self.assertEqual(context.exception.code.value, "MODEL_NOT_INSTALLED")
        self.assertFalse(context.exception.retryable)

    def test_builds_backend_ai_analysis_request(self) -> None:
        result = ImageAnalysisResult(
            title="러닝 기록 화면",
            description="러닝 거리와 시간이 표시된 앱 화면",
            tags=["러닝", "운동 기록"],
            ocr_text="3.02 킬로미터",
            objects=["지도", "운동 통계"],
            confidence=0.95,
        )
        payload = build_ai_analysis_request(
            result,
            ["건강·운동", "기타", "건강·운동", " "],
        )
        self.assertEqual(payload["title"], "러닝 기록 화면")
        self.assertEqual(payload["candidateCategories"], ["건강·운동", "기타"])
        self.assertIn("OCR 텍스트: 3.02 킬로미터", payload["text"])
        self.assertIn("주요 객체: 지도, 운동 통계", payload["text"])

    def test_classification_text_omits_empty_ocr(self) -> None:
        result = ImageAnalysisResult(
            title="반려견 사진",
            description="실내에 있는 흰색 반려견",
            tags=["반려견", "강아지"],
            ocr_text="",
            objects=["강아지"],
            confidence=0.9,
        )
        text = build_classification_text(result)
        self.assertNotIn("OCR 텍스트", text)
        self.assertIn("태그: 반려견, 강아지", text)


if __name__ == "__main__":
    unittest.main()
