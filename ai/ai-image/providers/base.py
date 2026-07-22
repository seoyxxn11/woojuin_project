from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class ImageModelProvider(ABC):
    @property
    @abstractmethod
    def model_id(self) -> str:
        """실행 결과에 기록할 모델 식별자입니다."""

    @abstractmethod
    def load(self) -> None:
        """모델과 프로세서를 메모리에 올립니다."""

    @abstractmethod
    def analyze(self, image_path: Path, prompt: str) -> tuple[str, dict[str, Any]]:
        """원본 응답 문자열과 실행 메타데이터를 반환합니다."""
