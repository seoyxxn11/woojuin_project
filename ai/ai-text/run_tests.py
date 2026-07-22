from __future__ import annotations

import argparse
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from src.auto_evaluator import evaluate
from src.comparison import compare_result_directories
from src.dataset_loader import (
    load_categories,
    load_category_definitions,
    load_dataset,
    load_memo_dataset,
    validate_expected_categories,
)
from src.ollama_client import OllamaClient, OllamaError, performance
from src.prompt_builder import build_prompt, load_prompt
from src.report_generator import generate_auto_report, generate_mode_report
from src.response_parser import output_schema, parse_response
from src.result_writer import append_jsonl, write_csv, write_json

ROOT = Path(__file__).resolve().parent
MODES = ("category-only", "summary-only", "metadata-only", "integrated")
PROMPT_FILES = {
    "category-only": "category-prompt-v1.txt",
    "summary-only": "summary-prompt-v1.txt",
    "metadata-only": "metadata-prompt-v1.txt",
    "integrated": "integrated-prompt-v2.txt",
}

def args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+")
    parser.add_argument("--test-ids", nargs="+")
    parser.add_argument("--repeat", type=int)
    parser.add_argument("--include-memos", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--include-json", action="store_true", help="메모와 JSON 회귀 데이터를 함께 실행")
    parser.add_argument("--memo-only", action="store_true", help="dataset/memo의 메모만 실행")
    parser.add_argument("--output-parent", help=argparse.SUPPRESS)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--all-modes", action="store_true", help="4개 테스트 모드를 순서대로 모두 실행")
    mode_group.add_argument("--category-only", action="store_true")
    mode_group.add_argument("--summary-only", action="store_true")
    mode_group.add_argument("--metadata-only", action="store_true")
    mode_group.add_argument("--integrated", action="store_true")
    mode_group.add_argument("--compare-results", nargs="+", metavar="RESULT_DIR", help="기존 실행 결과를 비교")
    return parser.parse_args(argv)

def selected_mode(options: argparse.Namespace) -> str:
    for mode in MODES:
        if getattr(options, mode.replace("-", "_")):
            return mode
    return "integrated"

def all_mode_command(options: argparse.Namespace, mode: str, output_parent: Path | None = None) -> list[str]:
    command = [sys.executable, str(ROOT / "run_tests.py"), f"--{mode}"]
    if options.models: command += ["--models", *options.models]
    if options.test_ids: command += ["--test-ids", *options.test_ids]
    if options.repeat is not None: command += ["--repeat", str(options.repeat)]
    if options.memo_only: command.append("--memo-only")
    if options.include_json: command.append("--include-json")
    if options.include_memos: command.append("--include-memos")
    if output_parent is not None: command += ["--output-parent", str(output_parent)]
    return command

def run_all_modes(options: argparse.Namespace) -> int:
    result_dirs: list[Path] = []
    results_root = ROOT / "results"
    started = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_parent = results_root / f"{started}-all-modes"
    suffix = 1
    while output_parent.exists():
        output_parent = results_root / f"{started}-all-modes-{suffix}"
        suffix += 1
    output_parent.mkdir(parents=True)
    print(f"[OK] 전체 모드 결과 디렉터리: {output_parent}")
    for index, mode in enumerate(MODES, 1):
        print(f"\n[ALL MODES {index}/{len(MODES)}] {mode}", flush=True)
        completed = subprocess.run(all_mode_command(options, mode, output_parent), cwd=ROOT, check=False)
        if completed.returncode != 0:
            print(f"[FAIL] {mode} 실행 중단 (exit={completed.returncode})")
            return completed.returncode
        result_dir = output_parent / mode
        if not result_dir.is_dir():
            print(f"[FAIL] {mode} 결과 폴더를 찾지 못했습니다.")
            return 2
        result_dirs.append(result_dir)
    try:
        comparison = compare_result_directories(result_dirs, results_root, output_parent)
    except (OSError, ValueError) as exc:
        print(f"[FAIL] 전체 모드 비교 보고서 생성 실패: {exc}")
        return 2
    print("\n[OK] 전체 모드 실행 완료")
    for path in result_dirs: print(f"- {path}")
    print(f"[OK] 전체 비교 보고서: {comparison}")
    return 0

def model_installed(wanted: str, installed: list[str]) -> bool:
    return wanted in installed or any(name.split(":")[0] == wanted for name in installed)

def dataset_key(item: dict) -> str:
    return f"{item.get('datasetType', 'unknown')}:{item['testId']}"

def flat(record: dict) -> dict:
    parsed = record.get("parsedResponse") or {}
    evaluation = record.get("evaluation") or {}
    perf = record.get("performance") or {}
    expected = record.get("expected") or {}
    expected_categories = expected.get("categories", [])
    return {
        "testId": record["testId"],
        "datasetKey": record.get("datasetKey", record["testId"]),
        "datasetType": record.get("datasetType", ""),
        "testMode": record.get("testMode", "integrated"),
        "title": record.get("title", ""),
        "sourcePath": record.get("sourcePath", ""),
        "idAutoAssigned": record.get("idAutoAssigned", False),
        "model": record["model"],
        "runType": record["runType"],
        "runNumber": record["runNumber"],
        "promptVersion": record["promptVersion"],
        "expectedCategory": expected_categories[0] if len(expected_categories) == 1 else " | ".join(expected_categories),
        "generatedSummary": parsed.get("summary", ""),
        "generatedCategory": parsed.get("category", ""),
        "confidence": parsed.get("confidence"),
        "generatedTags": " | ".join(parsed.get("tags", [])),
        "generatedKeywords": " | ".join(parsed.get("keywords", [])),
        **evaluation,
        **perf,
        "requestFailed": record["error"]["requestFailed"],
        "errorType": record["error"]["errorType"],
        "errorMessage": record["error"]["errorMessage"],
        "executedAt": record["executedAt"],
    }

def representative(rows: list[dict], datasets: dict[str, dict]) -> list[dict]:
    selected: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = row.get("datasetKey", row["testId"])
        if row["runType"] == "WARM" and not row["requestFailed"] and (row["model"], key) not in selected:
            selected[(row["model"], key)] = row
    result = []
    for (model, key), row in selected.items():
        item = datasets[key]
        result.append({"testId": row["testId"], "datasetKey": key, "model": model, "input": item["input"], **row})
    return result

def manual_rows(representatives: list[dict], mode: str = "integrated") -> list[dict]:
    common = ("testId", "datasetKey", "model", "title", "input", "expectedCategory")
    generated = {
        "category-only": ("generatedCategory", "confidence", "categoryCorrect"),
        "summary-only": ("generatedSummary", "requiredKeywordRecall", "summaryPointRecall", "forbiddenClaimCount"),
        "metadata-only": ("generatedTags", "generatedKeywords", "sourceKeywordRatio"),
        "integrated": ("generatedSummary", "generatedCategory", "generatedTags", "generatedKeywords", "categoryCorrect", "requiredKeywordRecall", "summaryPointRecall", "forbiddenClaimCount"),
    }[mode]
    manual = {
        "category-only": ("reviewer", "reviewNote"),
        "summary-only": ("summaryQuality", "factuality", "readability", "hallucinationLevel", "reviewer", "reviewNote"),
        "metadata-only": ("tagQuality", "keywordQuality", "searchUsefulness", "reviewer", "reviewNote"),
        "integrated": ("summaryQuality", "factuality", "tagQuality", "readability", "hallucinationLevel", "reviewer", "reviewNote"),
    }[mode]
    return [{**{key: row.get(key, "") for key in common + generated}, **{key: "" for key in manual}} for row in representatives]

def error_from_info(info: dict) -> dict[str, Any]:
    if not info.get("rawResponse", "").strip():
        return {"requestFailed": True, "errorType": "EMPTY_RESPONSE", "errorMessage": "빈 응답"}
    if not info.get("jsonValid"):
        return {"requestFailed": True, "errorType": "INVALID_JSON", "errorMessage": info.get("validationError", "")}
    if not info.get("schemaValid"):
        return {"requestFailed": True, "errorType": "SCHEMA_VALIDATION_FAILED", "errorMessage": info.get("validationError", "")}
    if info.get("extraTextDetected"):
        return {"requestFailed": True, "errorType": "EXTRA_TEXT", "errorMessage": "JSON 외 텍스트가 포함됐습니다."}
    if info.get("thinkingTagDetected"):
        return {"requestFailed": True, "errorType": "THINK_EXPOSED", "errorMessage": "<think> 내용이 노출됐습니다."}
    return {"requestFailed": False, "errorType": "", "errorMessage": ""}

def write_confusion_csv(path: Path, summaries: list[dict], categories: list[str]) -> None:
    rows = []
    for summary in summaries:
        matrix = summary.get("classification", {}).get("confusionMatrix", {})
        for actual in categories:
            rows.append({"model": summary["model"], "actual": actual, **{predicted: matrix.get(actual, {}).get(predicted, 0) for predicted in categories}})
    if rows:
        write_csv(path, rows, ["model", "actual", *categories])

def finalize(out: Path, metadata: dict, records: list[dict], rows: list[dict], data: list[dict], categories: list[str], mode: str) -> None:
    metadata["completedAt"] = datetime.now().astimezone().isoformat()
    write_json(out / "run-metadata.json", metadata)
    write_json(out / "raw-responses.json", records)
    write_json(out / "evaluation-results.json", rows)
    write_csv(out / "detail" / "auto-evaluation.csv", rows)
    datasets = {dataset_key(item): item for item in data}
    reps = representative(rows, datasets)
    write_csv(out / "detail" / "representative-results.csv", reps)
    write_csv(out / "manual-evaluation.csv", manual_rows(reps, mode))
    summaries = generate_mode_report(metadata, rows, categories, out / "report.md")
    if mode in ("category-only", "integrated"):
        write_json(out / "category-metrics.json", [{"model": summary["model"], **summary["classification"], "confidence": summary["confidence"]} for summary in summaries])
        write_confusion_csv(out / "confusion-matrix.csv", summaries, categories)
    if mode == "integrated":
        generate_auto_report(rows, out / "ai-text-comparison-auto.md")

def main(argv: list[str] | None = None) -> int:
    options = args(argv)
    if options.all_modes:
        return run_all_modes(options)
    if options.compare_results:
        try:
            output = compare_result_directories([Path(path) for path in options.compare_results], ROOT / "results")
        except (OSError, ValueError) as exc:
            print(f"[FAIL] 결과 비교 실패: {exc}")
            return 2
        print(f"[OK] 비교 보고서: {output}")
        return 0
    mode = selected_mode(options)
    config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    models = options.models or config["models"]
    repeat = options.repeat or int(config["repeatCount"])
    if repeat < 1:
        print("[FAIL] --repeat는 1 이상이어야 합니다.")
        return 2
    if sys.version_info < (3, 11):
        print("[FAIL] Python 3.11 이상이 필요합니다.")
        return 2
    print(f"[OK] Python {platform.python_version()}")
    try:
        memo_root = ROOT / "dataset" / "memo"
        categories = load_categories(memo_root)
        definitions = load_category_definitions(ROOT / "config" / "categories.json", memo_root)
        memo_data = load_memo_dataset(memo_root, categories)
        json_data = load_dataset(ROOT / "dataset" / "text-test-data.json") if (options.include_json or options.include_memos) else []
        if json_data:
            validate_expected_categories(json_data, categories)
    except (OSError, ValueError) as exc:
        print(f"[FAIL] 테스트 데이터 검증 실패: {exc}")
        return 2
    data = memo_data if options.memo_only or not json_data else json_data + memo_data
    if options.test_ids:
        unknown = set(options.test_ids) - {item["testId"] for item in data}
        if unknown:
            print(f"[FAIL] 없는 testId: {sorted(unknown)}")
            return 2
        data = [item for item in data if item["testId"] in options.test_ids]
    if not data:
        print("[FAIL] 실행할 테스트 데이터가 없습니다.")
        return 2
    prompt_version = config["promptVersions"][mode]
    prompt = load_prompt(ROOT / "prompts" / PROMPT_FILES[mode])
    dataset_type = "memo+json" if json_data and not options.memo_only else "memo"
    print(f"[OK] 테스트 모드 {mode}")
    print(f"[OK] 테스트 데이터 {len(data)}개 로드 ({dataset_type})")
    print(f"[OK] 프롬프트 버전 {prompt_version}")
    client = OllamaClient(config["ollamaBaseUrl"], config["connectTimeoutSeconds"], config["readTimeoutSeconds"])
    try:
        installed = client.models()
        print("[OK] Ollama 연결 성공")
    except OllamaError as exc:
        print(f"[FAIL] Ollama 연결 실패 ({exc.error_type}): {exc}")
        return 3
    missing = [model for model in models if not model_installed(model, installed)]
    if missing:
        for model in missing:
            print(f"모델 {model}가 설치되어 있지 않습니다.\nollama pull {model}")
        return 4
    for model in models:
        print(f"[OK] {model} 설치 확인")
    started = datetime.now().astimezone()
    out = (Path(options.output_parent).resolve() / mode) if options.output_parent else ROOT / "results" / f"{started.strftime('%Y%m%d-%H%M%S')}-{mode}"
    (out / "raw").mkdir(parents=True)
    (out / "detail").mkdir()
    print(f"[OK] 결과 디렉터리: {out}")
    metadata = {
        "testMode": mode,
        "datasetType": dataset_type,
        "datasetCount": len(data),
        "models": models,
        "model": models[0] if len(models) == 1 else None,
        "promptVersion": prompt_version,
        "promptFile": PROMPT_FILES[mode],
        "categories": categories,
        "startedAt": started.isoformat(),
        "completedAt": None,
        "status": "RUNNING",
        "environment": f"{platform.system()} {platform.release()}, Python {platform.python_version()}",
        "options": {
            "temperature": config["temperature"], "seed": config.get("seed"),
            "thinking": config.get("thinking"), "contextLength": config.get("contextLength"),
            "keepAlive": config["keepAlive"], "repeat": repeat,
            "totalDurationIncludesModelLoading": True,
        },
    }
    write_json(out / "run-metadata.json", metadata)
    raw_path = out / "raw" / "results.jsonl"
    records: list[dict] = []
    rows: list[dict] = []
    interrupted = False
    try:
        for model_index, model in enumerate(models, 1):
            print(f"[{model_index}/{len(models)} 모델] {model}")
            client.unload(model)
            runs = [("COLD", 0, data[0])] + [("WARM", number, item) for item in data for number in range(1, repeat + 1)]
            for run_type, run_number, item in runs:
                data_index = data.index(item) + 1
                print(f"[{data_index}/{len(data)} 데이터] {item['testId']}\n[{run_number or 1}/{repeat} 반복] {run_type}")
                request: dict = {}
                response: dict = {}
                info = parse_response("", categories, mode)
                error = {"requestFailed": False, "errorType": "", "errorMessage": ""}
                perf: dict = {}
                try:
                    built_prompt = build_prompt(prompt, item["input"], categories, item.get("title", ""), definitions)
                    request, response = client.chat(
                        model, built_prompt, config["temperature"], config["keepAlive"], output_schema(categories, mode),
                        config.get("seed"), config.get("contextLength"), config.get("thinking"),
                    )
                    raw = response.get("message", {}).get("content", "")
                    info = parse_response(raw, categories, mode)
                    perf = performance(response)
                    error = error_from_info(info)
                except OllamaError as exc:
                    error = {"requestFailed": True, "errorType": exc.error_type, "errorMessage": str(exc)}
                evaluation = evaluate(info, item["expected"], categories, mode, item["input"])
                record = {
                    "testId": item["testId"], "datasetKey": dataset_key(item), "datasetType": item["datasetType"],
                    "testMode": mode, "title": item.get("title", ""), "sourcePath": item.get("sourcePath", ""),
                    "idAutoAssigned": item.get("idAutoAssigned", False), "expected": item["expected"],
                    "model": model, "runType": run_type, "runNumber": run_number, "promptVersion": prompt_version,
                    "request": request,
                    "ollamaResponse": {key: response.get(key) for key in ("model", "created_at", "done", "done_reason", "total_duration", "load_duration", "prompt_eval_count", "prompt_eval_duration", "eval_count", "eval_duration")},
                    "rawResponse": info["rawResponse"], "parsedResponse": info["parsedResponse"],
                    "evaluation": evaluation, "performance": perf, "error": error,
                    "executedAt": datetime.now().astimezone().isoformat(),
                }
                append_jsonl(raw_path, record)
                records.append(record)
                row = flat(record)
                rows.append(row)
                category_result = "N/A" if evaluation["categoryCorrect"] is None else ("정답" if evaluation["categoryCorrect"] else "오답")
                print(f"상태: {'FAILED' if error['requestFailed'] else 'SUCCESS'}\nJSON: {'VALID' if info['jsonValid'] else 'INVALID'}\n카테고리: {category_result}\n응답 시간: {perf.get('totalDurationMs', 0):.0f}ms")
    except KeyboardInterrupt:
        interrupted = True
        print("\n[WARN] 사용자 중단: 완료된 결과를 저장합니다.")
    metadata["status"] = "INTERRUPTED" if interrupted else "COMPLETED"
    finalize(out, metadata, records, rows, data, categories, mode)
    print(f"{'부분 저장' if interrupted else '완료'}: {out}")
    return 130 if interrupted else 0

if __name__ == "__main__":
    raise SystemExit(main())
