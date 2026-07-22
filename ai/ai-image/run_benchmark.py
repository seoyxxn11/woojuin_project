from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from providers import GemmaProvider, GeminiGmsProvider, GmsProvider
from providers.base import ImageModelProvider
from report import generate_reports


ROOT = Path(__file__).resolve().parent
REQUIRED_RESULT_FIELDS = {
    "title",
    "description",
    "tags",
    "ocr_text",
    "objects",
    "confidence",
}
ALLOWED_CATEGORIES = {
    "DOCUMENT",
    "FOOD",
    "PLACE",
    "PRODUCT",
    "PERSON",
    "SCREENSHOT",
    "OTHER",
}


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def load_config(config_path: str = "config.yaml") -> dict[str, Any]:
    with resolve_path(config_path).open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_dataset(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(
            f"데이터셋이 없습니다: {path}\n"
            "ground_truth.example.jsonl을 ground_truth.jsonl로 복사해 작성하세요."
        )

    samples: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                sample = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number} JSON 오류: {exc}") from exc
            if not sample.get("id") or not sample.get("file"):
                raise ValueError(f"{path}:{line_number}에는 id와 file이 필요합니다.")
            samples.append(sample)
    return samples


def extract_json(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise
        parsed = json.loads(cleaned[start : end + 1])

    if not isinstance(parsed, dict):
        raise ValueError("모델 응답은 JSON 객체여야 합니다.")
    missing = REQUIRED_RESULT_FIELDS - parsed.keys()
    if missing:
        raise ValueError(f"필수 결과 필드 누락: {sorted(missing)}")
    if parsed.get("category") and parsed["category"] not in ALLOWED_CATEGORIES:
        raise ValueError(f"허용되지 않은 category: {parsed['category']}")
    return parsed


def validate_samples(samples: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    for sample in samples:
        sample_id = str(sample["id"])
        if sample_id in seen_ids:
            errors.append(f"중복 id: {sample_id}")
        seen_ids.add(sample_id)

        image_path = resolve_path(f"datasets/{sample['file']}")
        if not image_path.is_file():
            errors.append(f"{sample_id}: 이미지 없음 ({image_path})")
        category = sample.get("category")
        if category and category not in ALLOWED_CATEGORIES:
            errors.append(f"{sample_id}: 잘못된 category ({category})")
    return errors


def create_provider(model_config: dict[str, Any]) -> ImageModelProvider:
    provider = model_config.get("provider")
    if provider == "gemma":
        return GemmaProvider(model_config)
    if provider == "gms":
        return GmsProvider(model_config)
    if provider == "gemini_gms":
        return GeminiGmsProvider(model_config)
    raise ValueError(f"현재 지원하지 않는 provider입니다: {provider}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="로컬 이미지 모델 벤치마크")
    parser.add_argument("--sample-id", help="특정 샘플 ID만 실행")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="사용할 설정 파일 (기본값: config.yaml)",
    )
    parser.add_argument(
        "--model-id",
        help="설정 파일의 model_id를 이번 실행에서만 변경",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="모델을 로드하지 않고 설정과 데이터만 검증",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    if args.model_id:
        config["model"]["model_id"] = args.model_id
    benchmark_config = config["benchmark"]
    dataset_path = resolve_path(benchmark_config["dataset"])
    samples = load_dataset(dataset_path)

    if args.sample_id:
        samples = [sample for sample in samples if sample["id"] == args.sample_id]
        if not samples:
            print(f"샘플 ID를 찾을 수 없습니다: {args.sample_id}", file=sys.stderr)
            return 1

    errors = validate_samples(samples)
    if errors:
        print("데이터 검증 실패:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"데이터 검증 완료: {len(samples)}개")
    if args.dry_run:
        print("dry-run 완료: 모델은 로드하지 않았습니다.")
        return 0

    prompt = resolve_path(benchmark_config["prompt"]).read_text(encoding="utf-8")
    provider = create_provider(config["model"])
    print(f"모델 로드 중: {provider.model_id}")
    provider.load()

    results_dir = resolve_path(benchmark_config["results_dir"])
    results_dir.mkdir(parents=True, exist_ok=True)
    safe_model_name = provider.model_id.rsplit("/", maxsplit=1)[-1]
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = results_dir / f"{timestamp}-{safe_model_name}.jsonl"

    with output_path.open("a", encoding="utf-8") as output:
        for index, sample in enumerate(samples, start=1):
            sample_id = str(sample["id"])
            image_path = resolve_path(f"datasets/{sample['file']}")
            record: dict[str, Any] = {
                "sample_id": sample_id,
                "provider": config["model"]["provider"],
                "model": provider.model_id,
                "ground_truth": sample,
            }
            try:
                raw_response, metadata = provider.analyze(image_path, prompt)
                record.update(metadata)
                record["raw_response"] = raw_response
                record["result"] = extract_json(raw_response)
                record["json_valid"] = True
                record["error"] = None
            except Exception as exc:  # 한 샘플 실패가 전체 실행을 중단하지 않게 함
                record["result"] = None
                record["json_valid"] = False
                record["error"] = f"{type(exc).__name__}: {exc}"

            output.write(json.dumps(record, ensure_ascii=False) + "\n")
            output.flush()
            status = "성공" if record["error"] is None else "실패"
            print(f"[{index}/{len(samples)}] {sample_id}: {status}")

    print(f"결과 저장: {output_path}")
    reports_dir = resolve_path(benchmark_config.get("reports_dir", "reports"))
    try:
        report_paths = generate_reports(results_dir, reports_dir)
        for report_path in report_paths:
            print(f"보고서 생성: {report_path}")
    except Exception as exc:
        print(f"보고서 생성 실패: {type(exc).__name__}: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
