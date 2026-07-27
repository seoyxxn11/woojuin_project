from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from image_service import ImageAiError, ImageAnalysisService
from providers import OllamaVisionProvider


ROOT = Path(__file__).resolve().parent


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="서비스용 이미지 AI 단건 실행")
    parser.add_argument("image", type=Path, help="분석할 이미지 경로")
    parser.add_argument(
        "--config",
        default="config.qwen3vl8b.fast.yaml",
        help="Qwen3-VL 설정 파일",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with resolve_path(args.config).open(encoding="utf-8") as file:
        config = yaml.safe_load(file)
    prompt = resolve_path(config["benchmark"]["prompt"]).read_text(encoding="utf-8")
    service = ImageAnalysisService(
        OllamaVisionProvider(config["model"]),
        prompt,
        max_attempts=2,
    )
    try:
        service.validate_environment()
    except ImageAiError as exc:
        print(
            json.dumps(
                {
                    "success": False,
                    "result": None,
                    "error_code": exc.code.value,
                    "error_message": str(exc),
                    "retryable": exc.retryable,
                    "metadata": {},
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1
    response = service.analyze(args.image.resolve())
    print(json.dumps(response.to_dict(), ensure_ascii=False, indent=2))
    return 0 if response.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
