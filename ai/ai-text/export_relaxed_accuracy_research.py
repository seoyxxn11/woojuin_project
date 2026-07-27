from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="완화 정확도 개선 연구용 데이터 내보내기")
    parser.add_argument("--result-dir", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def score_text(row: dict[str, Any]) -> str:
    return " | ".join(
        f"{item.get('categoryName')}={float(item.get('score', 0)):.2f}"
        for item in row.get("validPredictions", [])
    )


def case_type(row: dict[str, Any]) -> str:
    if row.get("serviceRelaxedCorrect") is True:
        if row.get("top1Correct") is True:
            return "TOP1_CORRECT"
        return "GOLD_INCLUDED_NOT_TOP1"
    if row.get("fallbackUsed"):
        return "FALLBACK_WRONG"
    if row.get("thresholdMiss"):
        return "THRESHOLD_MISS"
    if row.get("rawGoldPresent"):
        return "GOLD_REMOVED_BY_LIMIT_OR_POLICY"
    return "GOLD_NOT_PREDICTED"


def compact_case(row: dict[str, Any]) -> dict[str, Any]:
    predictions = [
        {
            "categoryId": item.get("categoryId"),
            "categoryName": item.get("categoryName"),
            "score": item.get("score"),
        }
        for item in row.get("validPredictions", [])
    ]
    return {
        "testId": row.get("testId"),
        "caseType": case_type(row),
        "title": row.get("title"),
        "sourcePath": row.get("sourcePath"),
        "expectedCategory": row.get("expectedCategory"),
        "expectedCategoryId": row.get("expectedCategoryId"),
        "top1Category": row.get("top1CategoryName"),
        "top1Correct": row.get("top1Correct"),
        "serviceSelectedCategories": row.get("serviceSelectedCategoryNames", []),
        "serviceRelaxedCorrect": row.get("serviceRelaxedCorrect"),
        "serviceExactCorrect": row.get("serviceExactCorrect"),
        "fallbackUsed": row.get("fallbackUsed"),
        "thresholdMiss": row.get("thresholdMiss"),
        "errorTypes": row.get("errorTypes", []),
        "predictions": predictions,
        "input": row.get("input"),
    }


def main() -> int:
    options = parse_args()
    result_dir = options.result_dir.resolve()
    output = (
        options.output.resolve()
        if options.output
        else result_dir / "relaxed-accuracy-research"
    )
    rows = read_json(result_dir / "classification-results.json")
    definitions = read_json(result_dir / "category-descriptions.json")
    summary = read_json(result_dir / "classification-summary.json")[0]
    threshold_path = result_dir / "threshold-comparison" / "threshold-comparison.json"
    thresholds = read_json(threshold_path) if threshold_path.is_file() else []

    cases = [compact_case(row) for row in rows]
    incorrect = [case for case in cases if not case["serviceRelaxedCorrect"]]
    gold_not_top1 = [
        case for case in cases
        if case["serviceRelaxedCorrect"] and not case["top1Correct"]
    ]

    case_rows = []
    for row, case in zip(rows, cases):
        case_rows.append({
            "testId": case["testId"],
            "caseType": case["caseType"],
            "expectedCategory": case["expectedCategory"],
            "top1Category": case["top1Category"],
            "serviceSelectedCategories": " | ".join(case["serviceSelectedCategories"]),
            "top1Correct": case["top1Correct"],
            "relaxedCorrect": case["serviceRelaxedCorrect"],
            "exactCorrect": case["serviceExactCorrect"],
            "fallbackUsed": case["fallbackUsed"],
            "thresholdMiss": case["thresholdMiss"],
            "predictionScores": score_text(row),
            "errorTypes": " | ".join(case["errorTypes"]),
            "title": case["title"],
            "sourcePath": case["sourcePath"],
            "inputExcerpt": str(case["input"] or "")[:2000],
        })
    fields = [
        "testId", "caseType", "expectedCategory", "top1Category",
        "serviceSelectedCategories", "top1Correct", "relaxedCorrect",
        "exactCorrect", "fallbackUsed", "thresholdMiss", "predictionScores",
        "errorTypes", "title", "sourcePath", "inputExcerpt",
    ]
    write_csv(output / "all-cases.csv", case_rows, fields)
    write_csv(
        output / "incorrect-cases.csv",
        [item for item in case_rows if not item["relaxedCorrect"]],
        fields,
    )
    write_csv(
        output / "gold-included-not-top1.csv",
        [
            item for item in case_rows
            if item["relaxedCorrect"] and not item["top1Correct"]
        ],
        fields,
    )

    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_category[str(row.get("expectedCategory"))].append(row)
    category_rows = []
    for definition in definitions:
        name = str(definition["name"])
        selected = by_category.get(name, [])
        count = len(selected)
        relaxed = sum(row.get("serviceRelaxedCorrect") is True for row in selected)
        top1 = sum(row.get("top1Correct") is True for row in selected)
        category_rows.append({
            "category": name,
            "support": count,
            "relaxedCorrectCount": relaxed,
            "relaxedAccuracy": relaxed / count if count else None,
            "top1Accuracy": top1 / count if count else None,
            "description": definition.get("description"),
            "examples": " | ".join(definition.get("examples", [])),
        })
    write_csv(
        output / "category-performance.csv",
        category_rows,
        [
            "category", "support", "relaxedCorrectCount", "relaxedAccuracy",
            "top1Accuracy", "description", "examples",
        ],
    )

    confusions = Counter()
    for row in rows:
        if row.get("serviceRelaxedCorrect") is not True:
            selected = row.get("serviceSelectedCategoryNames", []) or ["선택 없음"]
            for predicted in selected:
                confusions[(str(row.get("expectedCategory")), str(predicted))] += 1
    confusion_rows = [
        {"expectedCategory": expected, "predictedCategory": predicted, "count": count}
        for (expected, predicted), count in confusions.most_common()
    ]
    write_csv(
        output / "confusion-pairs.csv",
        confusion_rows,
        ["expectedCategory", "predictedCategory", "count"],
    )

    bundle = {
        "sourceResultDirectory": str(result_dir),
        "summary": summary,
        "caseTypeCounts": dict(Counter(case["caseType"] for case in cases)),
        "thresholdComparison": thresholds,
        "categoryDefinitions": definitions,
        "incorrectCases": incorrect,
        "goldIncludedNotTop1Cases": gold_not_top1,
        "allCases": cases,
    }
    write_json(output / "research-data.json", bundle)

    lines = [
        "# 완화 정확도 개선 연구 데이터",
        "",
        f"- 원본 결과: `{result_dir}`",
        f"- 전체 데이터: {len(cases)}건",
        f"- 완화 정답: {len(cases) - len(incorrect)}건",
        f"- 완화 오답: {len(incorrect)}건",
        f"- Top-1은 오답이지만 두 번째 선택으로 정답 포함: {len(gold_not_top1)}건",
        "",
        "## 사례 유형",
        "",
    ]
    for name, count in Counter(case["caseType"] for case in cases).most_common():
        lines.append(f"- `{name}`: {count}건")
    lines.extend([
        "",
        "## 파일 설명",
        "",
        "- `incorrect-cases.csv`: 완화 정확도 오답만 모은 핵심 분석 파일",
        "- `gold-included-not-top1.csv`: 두 번째 카테고리가 정확도를 살린 사례",
        "- `all-cases.csv`: 43건 전체 예측 점수와 판정",
        "- `category-performance.csv`: 카테고리별 표본 수와 정확도, 사용 설명",
        "- `confusion-pairs.csv`: 오답에서 정답→예측 카테고리 혼동 횟수",
        "- `research-data.json`: 원문 입력과 전체 예측을 포함한 통합 JSON",
        "",
        "## 분석 시 우선 확인",
        "",
        "1. `GOLD_NOT_PREDICTED`: 프롬프트·설명·학습 데이터 보강 대상",
        "2. `FALLBACK_WRONG`: JSON 출력 실패 또는 유효 카테고리 부재 확인",
        "3. `GOLD_INCLUDED_NOT_TOP1`: 임계치와 최대 선택 수 정책의 효과 확인",
        "4. 표본이 적은 카테고리는 정확도 변동이 크므로 건수와 함께 해석",
    ])
    (output / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] 연구 데이터: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
