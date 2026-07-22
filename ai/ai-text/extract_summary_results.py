from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from src.dataset_loader import load_categories, load_memo_dataset
from src.result_writer import write_json


ROOT = Path(__file__).resolve().parent
PHASE2_RESULTS = ROOT / "results" / "2차 분류 테스트"
LOCAL_RESULTS = PHASE2_RESULTS / "20260721-101535-all-modes"
API_RESULTS = PHASE2_RESULTS / "20260721-140910-api-basic"
OUTPUT_DIR = ROOT / "REPORT" / "summary-evaluation"
MODES = ("summary-only", "integrated")
MODEL_ORDER = ("qwen3:4b", "qwen3:8b", "openai-gpt-5-nano", "openai-gpt-5-mini")


def read_rows(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError(f"평가 결과가 배열이 아닙니다: {path}")
    return value


def selected_rows(mode: str) -> list[dict[str, Any]]:
    rows = read_rows(LOCAL_RESULTS / mode / "evaluation-results.json")
    rows += read_rows(API_RESULTS / mode / "evaluation-results.json")
    return [
        row for row in rows
        if row.get("runType") == "WARM"
        and int(row.get("runNumber", 1)) == 1
        and not row.get("requestFailed")
        and str(row.get("generatedSummary", "")).strip()
    ]


def model_id(row: dict[str, Any]) -> str:
    return str(row.get("modelId") or row.get("model"))


def provider(model: str) -> str:
    return "openai-via-gms" if model.startswith("openai-") else "ollama"


def output_entry(row: dict[str, Any]) -> dict[str, Any]:
    model = model_id(row)
    return {
        "modelId": model,
        "provider": provider(model),
        "summary": row["generatedSummary"],
        "manualEvaluation": {
            "summaryQuality": None,
            "factuality": None,
            "readability": None,
            "hallucinationLevel": None,
            "reviewNote": "",
        },
    }


def build() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    memo_root = ROOT / "dataset" / "memo"
    dataset = load_memo_dataset(memo_root, load_categories(memo_root))
    by_test_id = {item["testId"]: item for item in dataset}
    rows_by_mode = {mode: selected_rows(mode) for mode in MODES}
    executed_ids = set.intersection(*(
        {str(row["testId"]) for row in rows}
        for rows in rows_by_mode.values()
    ))
    unknown_ids = executed_ids - set(by_test_id)
    if unknown_ids:
        raise ValueError(f"현재 메모 데이터에서 찾을 수 없는 테스트 ID: {sorted(unknown_ids)}")
    test_cases: list[dict[str, Any]] = []
    flat_rows: list[dict[str, Any]] = []
    for test_id in sorted(executed_ids, key=lambda value: int(value.split("-")[1])):
        item = by_test_id[test_id]
        case: dict[str, Any] = {
            "testId": test_id,
            "title": item.get("title", ""),
            "sourcePath": item.get("sourcePath", ""),
            "expectedCategory": item["expected"]["categories"][0],
            "input": item["input"],
            "outputs": {},
        }
        for mode in MODES:
            matching = [row for row in rows_by_mode[mode] if row["testId"] == test_id]
            matching.sort(key=lambda row: MODEL_ORDER.index(model_id(row)))
            outputs = [output_entry(row) for row in matching]
            if [entry["modelId"] for entry in outputs] != list(MODEL_ORDER):
                raise ValueError(f"{mode}/{test_id}: 네 모델의 요약이 모두 존재하지 않습니다")
            case["outputs"][mode] = outputs
            for entry in outputs:
                flat_rows.append({
                    "testId": test_id,
                    "title": item.get("title", ""),
                    "expectedCategory": item["expected"]["categories"][0],
                    "input": item["input"],
                    "testMode": mode,
                    "modelId": entry["modelId"],
                    "provider": entry["provider"],
                    "summary": entry["summary"],
                    "summaryQuality": "",
                    "factuality": "",
                    "readability": "",
                    "hallucinationLevel": "",
                    "reviewNote": "",
                })
        test_cases.append(case)
    result = {
        "metadata": {
            "purpose": "summary-only와 integrated 요약 수동 평가",
            "testCaseCount": len(test_cases),
            "datasetTestCaseCount": len(dataset),
            "unexecutedTestCaseCount": len(dataset) - len(test_cases),
            "modelCount": len(MODEL_ORDER),
            "testModes": list(MODES),
            "models": list(MODEL_ORDER),
            "summaryCount": len(flat_rows),
            "coldRunsExcluded": True,
            "scoreGuide": {
                "summaryQuality": "1~5",
                "factuality": "1~5",
                "readability": "1~5",
                "hallucinationLevel": "NONE | MINOR | MAJOR",
            },
            "sources": [str(LOCAL_RESULTS.relative_to(ROOT)), str(API_RESULTS.relative_to(ROOT))],
        },
        "testCases": test_cases,
    }
    return result, flat_rows


def main() -> None:
    result, flat_rows = build()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OUTPUT_DIR / "summary-evaluation-data.json", result)
    fields = list(flat_rows[0])
    with (OUTPUT_DIR / "summary-evaluation-template.csv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(flat_rows)
    print(f"JSON: {OUTPUT_DIR / 'summary-evaluation-data.json'}")
    print(f"CSV: {OUTPUT_DIR / 'summary-evaluation-template.csv'}")
    print(f"TEST_CASES={len(result['testCases'])}")
    print(f"SUMMARIES={result['metadata']['summaryCount']}")


if __name__ == "__main__":
    main()
