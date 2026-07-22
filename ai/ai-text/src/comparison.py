from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json
from .report_generator import _display, _table, summarize_run

def compare_result_directories(paths: list[Path], results_root: Path, output_dir: Path | None = None) -> Path:
    summaries: list[dict] = []
    sources: list[str] = []
    for path in paths:
        resolved = path.resolve()
        metadata_path = resolved / "run-metadata.json"
        evaluation_path = resolved / "evaluation-results.json"
        if not metadata_path.is_file() or not evaluation_path.is_file():
            raise ValueError(f"비교에 필요한 파일이 없습니다: {resolved}")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        rows = json.loads(evaluation_path.read_text(encoding="utf-8"))
        categories = metadata.get("categories", [])
        summaries.extend(summarize_run(rows, categories, metadata["testMode"]))
        sources.append(str(resolved))
    output = output_dir or results_root / f"comparison-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    output.mkdir(parents=True, exist_ok=output_dir is not None)
    table_rows = []
    for summary in summaries:
        op = summary["operational"]
        table_rows.append([
            summary["model"], summary["testMode"], summary["callCount"],
            _display(summary["responseSuccessRate"], True), _display(summary["jsonSuccessRate"], True),
            _display(summary["schemaSuccessRate"], True), _display(summary["categoryAccuracy"], True),
            _display(summary["macroF1"], True), _display(op["averageResponseTimeMs"]),
            _display(op["p95ResponseTimeMs"]), _display(op["averageTokensPerSecond"]),
        ])
    report = ["# 모델 결과 비교 보고서", "", "## 입력 결과", ""] + [f"- {source}" for source in sources]
    report += ["", _table(["모델", "테스트 모드", "호출 수", "응답 성공률", "JSON 성공률", "스키마 성공률", "카테고리 정확도", "Macro F1", "평균 응답 시간(ms)", "P95(ms)", "평균 TPS"], table_rows), "", "평가하지 않은 항목은 0이 아니라 N/A로 표시합니다."]
    (output / "comparison-report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    (output / "comparison-summary.json").write_text(json.dumps(summaries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output
