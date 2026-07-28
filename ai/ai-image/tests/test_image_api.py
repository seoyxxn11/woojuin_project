from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from image_service import ImageAiError, ImageAiErrorCode
from image_service.models import ImageAnalysisResponse, ImageAnalysisResult
from serve_image_ai import app


class FakeImageService:
    provider = SimpleNamespace(model_id="fake-vision")

    def validate_environment(self) -> None:
        return None

    def analyze(self, _image_path) -> ImageAnalysisResponse:
        return ImageAnalysisResponse(
            success=True,
            result=ImageAnalysisResult(
                title="테스트 이미지",
                description="테스트 설명",
                tags=["테스트"],
                ocr_text="인식 문구",
                objects=["화면"],
                confidence=0.9,
            ),
            metadata={"model": "fake-vision"},
        )


class UnavailableImageService(FakeImageService):
    def validate_environment(self) -> None:
        raise ImageAiError(
            ImageAiErrorCode.OLLAMA_UNAVAILABLE,
            "Ollama에 연결할 수 없습니다.",
            retryable=True,
        )


class ImageApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    @patch("serve_image_ai.get_service", return_value=FakeImageService())
    def test_health(self, _get_service) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "UP")

    @patch("serve_image_ai.get_service", return_value=FakeImageService())
    def test_analyze_returns_backend_classification_text(self, _get_service) -> None:
        response = self.client.post(
            "/v1/images/analyze",
            files={"file": ("image.jpg", b"fake-image", "image/jpeg")},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertIn("테스트 설명", payload["classificationText"])
        self.assertIn("인식 문구", payload["classificationText"])

    def test_rejects_empty_upload(self) -> None:
        response = self.client.post(
            "/v1/images/analyze",
            files={"file": ("empty.jpg", b"", "image/jpeg")},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error_code"],
            "IMAGE_DECODE_FAILED",
        )

    @patch("serve_image_ai.get_service", return_value=UnavailableImageService())
    def test_health_failure_uses_contract_shape(self, _get_service) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error_code"], "OLLAMA_UNAVAILABLE")
        self.assertTrue(payload["retryable"])


if __name__ == "__main__":
    unittest.main()
