from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from src.dataset_loader import load_category_definitions
from src.model_config import load_models
from src.ollama_client import OllamaClient
from src.prompt_builder import build_prompt, load_prompt
from src.providers import ModelRequest, OllamaProvider
from src.response_parser import output_multi_label_schema, parse_multi_label_response


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent.parent
IMAGE_RESULTS = PROJECT_ROOT / "ai" / "ai-image" / "results"
VALID_IMAGE_FIELDS = {"title", "description", "tags", "ocr_text", "objects"}
SECONDARY_MIN_SCORE = 0.45
SECONDARY_MAX_GAP = 0.10
MAX_SELECTED_CATEGORIES = 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="이미지 AI 추출 결과를 Qwen3 텍스트 카테고리 모델로 평가"
    )
    parser.add_argument("--image-result", type=Path, help="이미지 결과 JSONL")
    parser.add_argument(
        "--answer-key",
        type=Path,
        help="정답 JSONL(id/sample_id와 category). 모델 입력에는 전달하지 않음",
    )
    parser.add_argument("--limit", type=int, help="앞에서부터 N개만 실행")
    parser.add_argument("--dry-run", action="store_true", help="모델 호출 없이 입력만 검증")
    return parser.parse_args()


def latest_image_result(directory: Path = IMAGE_RESULTS) -> Path:
    candidates = [
        path
        for path in directory.glob("*.jsonl")
        if path.is_file() and path.stat().st_size > 0
    ]
    if not candidates:
        raise FileNotFoundError(f"비어 있지 않은 이미지 결과 파일이 없습니다: {directory}")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    # utf-8-sig는 BOM이 있는 Windows UTF-8 파일과 일반 UTF-8 파일을 모두 읽는다.
    with path.open(encoding="utf-8-sig") as file:
        for line_number, line in enumerate(file, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number} JSON 오류: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} JSON 객체가 필요합니다")
            records.append(value)
    return records


def load_answer_key(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    answers: dict[str, dict[str, Any]] = {}
    for record in load_jsonl(path):
        sample_id = str(record.get("sample_id") or record.get("id") or "").strip()
        category = str(record.get("category") or "").strip()
        if not sample_id or not category:
            raise ValueError("정답 파일의 각 줄에는 id(또는 sample_id)와 category가 필요합니다")
        if sample_id in answers:
            raise ValueError(f"정답 파일에 중복 ID가 있습니다: {sample_id}")
        answers[sample_id] = {
            "category": category,
            "acceptable_categories": record.get("acceptable_categories", [category]),
            "required_concepts": record.get("required_concepts", []),
            "ocr_keywords": record.get("ocr_keywords", []),
        }
    return answers


def normalized_text(value: Any) -> str:
    return "".join(character for character in str(value).casefold() if character.isalnum())


def keyword_recall(expected: list[Any], actual: str) -> tuple[int, int, float | None]:
    if not expected:
        return 0, 0, None
    normalized_actual = normalized_text(actual)
    hits = 0
    for item in expected:
        alternatives = item if isinstance(item, list) else [item]
        if any(normalized_text(value) in normalized_actual for value in alternatives if str(value).strip()):
            hits += 1
    return hits, len(expected), hits / len(expected)


def extraction_text(result: dict[str, Any]) -> str:
    values = [
        result.get("title", ""),
        result.get("description", ""),
        result.get("ocr_text", ""),
        *result.get("tags", []),
        *result.get("objects", []),
    ]
    return "\n".join(str(value) for value in values if str(value).strip())


def select_service_categories(predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(predictions, key=lambda item: float(item["score"]), reverse=True)
    if not ordered:
        return []
    selected = [ordered[0]]
    if len(ordered) > 1:
        second = ordered[1]
        top_score = float(ordered[0]["score"])
        second_score = float(second["score"])
        if second_score >= SECONDARY_MIN_SCORE and top_score - second_score <= SECONDARY_MAX_GAP:
            selected.append(second)
    return selected[:MAX_SELECTED_CATEGORIES]


def image_result(record: dict[str, Any]) -> dict[str, Any] | None:
    result = record.get("result")
    if record.get("error") or not record.get("json_valid", False):
        return None
    if not isinstance(result, dict) or not VALID_IMAGE_FIELDS.issubset(result):
        return None
    return result


def image_metadata(record: dict[str, Any]) -> dict[str, Any]:
    """이미지 결과에서 서비스에 필요한 실제 EXIF 메타데이터만 가져온다."""
    nested = record.get("metadata")
    source = nested if isinstance(nested, dict) else record
    return {
        "latitude": source.get("latitude"),
        "longitude": source.get("longitude"),
        "captured_at": source.get("captured_at"),
    }


def classification_content(result: dict[str, Any]) -> str:
    sections = [
        ("이미지 설명", str(result.get("description", "")).strip()),
        ("OCR 텍스트", str(result.get("ocr_text", "")).strip()),
        ("태그", ", ".join(str(value) for value in result.get("tags", []) if str(value).strip())),
        ("주요 객체", ", ".join(str(value) for value in result.get("objects", []) if str(value).strip())),
    ]
    return "\n".join(f"{label}: {value}" for label, value in sections if value)


def embedded_expected_category(record: dict[str, Any], categories: list[str]) -> str | None:
    truth = record.get("ground_truth")
    if not isinstance(truth, dict):
        return None
    value = str(truth.get("expected_category") or truth.get("category") or "").strip()
    return value if value in categories else None


def write_outputs(
    output: Path,
    rows: list[dict[str, Any]],
    source: Path,
    model: str,
) -> None:
    output.mkdir(parents=True, exist_ok=False)
    with (output / "results.jsonl").open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")

    columns = [
        "sample_id", "expected_category", "acceptable_categories",
        "predicted_category", "predicted_categories",
        "correct", "gold_included",
        "concept_hits", "concept_total", "concept_recall",
        "ocr_hits", "ocr_total", "ocr_keyword_recall",
        "confidence", "status", "latency_ms", "error",
    ]
    with (output / "details.csv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    evaluated = [row for row in rows if row["expected_category"]]
    correct = sum(row["correct"] is True for row in evaluated)
    included = sum(row["gold_included"] is True for row in evaluated)
    successful_rows = [row for row in rows if row["status"] == "SUCCESS"]
    success = len(successful_rows)
    accuracy = correct / len(evaluated) if evaluated else None
    average_confidence = (
        sum(float(row["confidence"]) for row in successful_rows) / success
        if success
        else None
    )
    average_latency = (
        sum(float(row["latency_ms"]) for row in rows) / len(rows)
        if rows
        else None
    )
    concept_hits = sum(int(row["concept_hits"]) for row in rows)
    concept_total = sum(int(row["concept_total"]) for row in rows)
    ocr_hits = sum(int(row["ocr_hits"]) for row in rows)
    ocr_total = sum(int(row["ocr_total"]) for row in rows)
    distribution = Counter(
        str(row["predicted_category"])
        for row in successful_rows
        if row["predicted_category"]
    )
    report = [
        "# 이미지 → 카테고리 통합 테스트",
        "",
        f"- 이미지 결과: `{source}`",
        f"- 카테고리 모델: `{model}`",
        f"- 전체 입력: {len(rows)}개",
        f"- 분류 성공: {success}/{len(rows)} ({success / len(rows):.1%})" if rows else "- 분류 성공: 0/0",
        (
            f"- 정답 보유 데이터 정확도: {correct}/{len(evaluated)} ({accuracy:.1%})"
            if accuracy is not None
            else "- 정답 보유 데이터 정확도: N/A (정답 파일 없음)"
        ),
        (
            f"- 다중 분류 정답 포함률: {included}/{len(evaluated)} "
            f"({included / len(evaluated):.1%})"
            if evaluated
            else "- 다중 분류 정답 포함률: N/A"
        ),
        (
            f"- 다중 할당 기준: 2순위 {SECONDARY_MIN_SCORE:.0%} 이상, "
            f"1순위와 점수 차이 {SECONDARY_MAX_GAP:.0%}p 이하, 최대 {MAX_SELECTED_CATEGORIES}개"
        ),
        (
            f"- 이미지 핵심 정보 재현율: {concept_hits}/{concept_total} "
            f"({concept_hits / concept_total:.1%})"
            if concept_total
            else "- 이미지 핵심 정보 재현율: N/A"
        ),
        (
            f"- OCR 핵심어 재현율: {ocr_hits}/{ocr_total} ({ocr_hits / ocr_total:.1%}) "
            f"(글자가 있는 사진만 평가)"
            if ocr_total
            else "- OCR 핵심어 재현율: N/A"
        ),
        (
            f"- 평균 모델 신뢰도: {average_confidence:.3f}"
            if average_confidence is not None
            else "- 평균 모델 신뢰도: N/A"
        ),
        (
            f"- 이미지당 평균 분류 시간: {average_latency / 1000:.2f}초"
            if average_latency is not None
            else "- 이미지당 평균 분류 시간: N/A"
        ),
        "",
        "## 예측 카테고리 분포",
        "",
        "| 카테고리 | 이미지 수 | 비율 |",
        "| --- | ---: | ---: |",
    ]
    for category, count in distribution.most_common():
        report.append(f"| {category} | {count} | {count / len(rows):.1%} |")
    report.extend([
        "",
        "## 이미지별 결과",
        "",
        "| ID | 정답 | 최종 분류 | Top-1 | 정답 포함 | 핵심 정보 | OCR |",
        "| --- | --- | --- | --- | --- | ---: | ---: |",
    ])
    for row in rows:
        verdict = "일치" if row["correct"] is True else "불일치" if row["correct"] is False else "N/A"
        concept = (
            f"{row['concept_recall']:.0%}"
            if isinstance(row["concept_recall"], (int, float))
            else "N/A"
        )
        ocr = (
            f"{row['ocr_keyword_recall']:.0%}"
            if isinstance(row["ocr_keyword_recall"], (int, float))
            else "N/A"
        )
        report.append(
            f"| {row['sample_id']} | {', '.join(row['acceptable_categories']) or 'N/A'} | "
            f"{', '.join(row['predicted_categories']) or '실패'} | {verdict} | "
            f"{'포함' if row['gold_included'] is True else '미포함' if row['gold_included'] is False else 'N/A'} | "
            f"{concept} | {ocr} |"
        )
    (output / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def main() -> int:
    options = parse_args()
    source = (options.image_result or latest_image_result()).resolve()
    if not source.is_file() or source.stat().st_size == 0:
        raise FileNotFoundError(f"이미지 결과 파일이 없거나 비어 있습니다: {source}")

    config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    models = load_models(ROOT / "config" / "models.yaml")
    model = models["qwen-local"]
    definitions = load_category_definitions(
        ROOT / "config" / "categories.json",
        ROOT / "dataset" / "memo",
    )
    categories = [item["name"] for item in definitions]
    answers = load_answer_key(options.answer_key.resolve() if options.answer_key else None)
    records = load_jsonl(source)
    if options.limit is not None:
        if options.limit < 1:
            raise ValueError("--limit은 1 이상이어야 합니다")
        records = records[: options.limit]
    if not records:
        raise ValueError("평가할 이미지 결과가 없습니다")

    prompt_template = load_prompt(ROOT / "prompts" / "category-prompt-v1.txt")
    prepared: list[tuple[str, dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    skipped: list[str] = []
    for record in records:
        sample_id = str(record.get("sample_id") or "").strip()
        result = image_result(record)
        if not sample_id or result is None:
            skipped.append(sample_id or "(ID 없음)")
            continue
        answer = answers.get(sample_id, {})
        expected = answer.get("category") or embedded_expected_category(record, categories)
        acceptable = answer.get("acceptable_categories") or ([expected] if expected else [])
        if expected and expected not in categories:
            raise ValueError(f"{sample_id}: 알 수 없는 정답 카테고리 '{expected}'")
        invalid_acceptable = [value for value in acceptable if value not in categories]
        if invalid_acceptable:
            raise ValueError(f"{sample_id}: 알 수 없는 허용 정답 카테고리 {invalid_acceptable}")
        prepared.append((
            sample_id,
            result,
            image_metadata(record),
            {
                "category": expected,
                "acceptable_categories": acceptable,
                "required_concepts": answer.get("required_concepts", []),
                "ocr_keywords": answer.get("ocr_keywords", []),
            },
        ))

    if not prepared:
        raise ValueError("성공한 이미지 AI 결과가 없습니다")
    missing_answers = sorted(set(answers) - {sample_id for sample_id, _, _, _ in prepared})
    if missing_answers:
        raise ValueError(f"이미지 결과에 없는 정답 ID: {', '.join(missing_answers)}")

    print(f"이미지 결과: {source}")
    print(f"평가 대상: {len(prepared)}개 / 제외: {len(skipped)}개 / 모델: {model.model}")
    if options.dry_run:
        print(
            f"정답 연결: "
            f"{sum(answer['category'] is not None for _, _, _, answer in prepared)}개"
        )
        print("dry-run 완료: Ollama를 호출하지 않았습니다.")
        return 0

    client = OllamaClient(
        str(config["ollamaBaseUrl"]),
        float(config["connectTimeoutSeconds"]),
        float(config["readTimeoutSeconds"]),
    )
    if model.model not in client.models():
        raise RuntimeError(f"Ollama 모델이 없습니다: {model.model} (`ollama pull {model.model}`)")
    provider = OllamaProvider(
        client,
        str(config["keepAlive"]),
        int(config["seed"]),
        int(config["contextLength"]),
        bool(config["thinking"]),
    )

    rows: list[dict[str, Any]] = []
    for index, (sample_id, result, metadata, answer) in enumerate(prepared, 1):
        expected = answer["category"]
        acceptable = answer["acceptable_categories"]
        prompt = build_prompt(
            prompt_template,
            classification_content(result),
            categories,
            title=str(result.get("title", "")),
            category_definitions=definitions,
        )
        response = provider.generate(
            ModelRequest(
                prompt=prompt,
                schema=output_multi_label_schema(definitions),
                test_mode="category-only",
                test_id=sample_id,
                temperature=0.0,
            ),
            model,
        )
        parsed = parse_multi_label_response(response.raw_text, definitions)
        candidates = parsed.get("validPredictions", []) if parsed.get("categoryParseSuccess") else []
        selected = select_service_categories(candidates)
        predicted_categories = [str(item["categoryName"]) for item in selected]
        predicted = predicted_categories[0] if predicted_categories else None
        confidence = float(selected[0]["score"]) if selected else None
        status = "SUCCESS" if predicted_categories else "FAILED"
        concept_hits, concept_total, concept_recall = keyword_recall(
            answer["required_concepts"], extraction_text(result)
        )
        ocr_hits, ocr_total, ocr_recall = keyword_recall(
            answer["ocr_keywords"], str(result.get("ocr_text", ""))
        )
        row = {
            "sample_id": sample_id,
            "expected_category": expected,
            "acceptable_categories": acceptable,
            "predicted_category": predicted,
            "predicted_categories": predicted_categories,
            "correct": predicted in acceptable if acceptable else None,
            "gold_included": bool(set(acceptable) & set(predicted_categories)) if acceptable else None,
            "concept_hits": concept_hits,
            "concept_total": concept_total,
            "concept_recall": concept_recall,
            "ocr_hits": ocr_hits,
            "ocr_total": ocr_total,
            "ocr_keyword_recall": ocr_recall,
            "confidence": confidence,
            "status": status,
            "latency_ms": round(response.latency_ms, 2),
            "error": response.error_message or parsed.get("validationError") or None,
            "image_result": result,
            "metadata": metadata,
            "classification_text": classification_content(result),
            "model_response": response.to_dict(),
            "parse_result": parsed,
        }
        rows.append(row)
        verdict = "일치" if row["correct"] is True else "불일치" if row["correct"] is False else status
        print(f"[{index}/{len(prepared)}] {sample_id}: {verdict}")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output = ROOT / "results" / f"{timestamp}-image-to-category"
    write_outputs(output, rows, source, model.model)
    print(f"결과 저장: {output}")
    print(f"보고서: {output / 'report.md'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"실행 실패: {exc}", file=sys.stderr)
        raise SystemExit(1)
