"""집중(focused) 증분 카테고리 테스트 실행기.

기존 112건을 로딩·호출하지 않고, gold 매니페스트에 명시된 데이터(현재 28건)만
한 건씩 입력한다. clustered / interleaved 두 순서만 기본 실행하며, 후보 파편화·
재사용률·순도·포착률·승격·오병합·순서 안정성을 측정한다.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from run_incremental_category_service import build_real_backend
from src.incremental_category_service import (
    DeterministicBackend,
    PROMOTED,
    ServiceConfig,
    WorkspaceCategoryEngine,
    summarize_run,
)
from src.dynamic_category_experiment import PRESET_SEEDS
from src.result_writer import write_json

ROOT = Path(__file__).resolve().parent
DEFAULT_MANIFEST = ROOT / "dataset" / "tester" / "focused-incremental" / "focused-gold.jsonl"
CONFIG_PATH = ROOT / "config" / "incremental-category.yaml"
REUSE_ACTIONS = {"REUSE_EMBEDDING", "REUSE_AI", "REUSE_FINAL_DEDUP"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="집중 증분 카테고리 테스트 (매니페스트 데이터만 실행)")
    parser.add_argument("--dataset", default="focused-incremental", help="데이터셋 태그 (기본: focused-incremental)")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--mode", choices=("offline", "real"), default="offline")
    parser.add_argument("--model", default="openrouter-qwen3-8b")
    parser.add_argument(
        "--order",
        nargs="+",
        default=["grouped", "interleaved"],
        choices=("grouped", "clustered", "interleaved"),
        help="기본: grouped interleaved (shuffle/112 전체는 실행하지 않음)",
    )
    parser.add_argument("--workspace-id", type=int, default=10)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--output", type=Path)
    # 재사용 임계값 재보정용 오버라이드(설정 파일을 바꾸지 않고 이번 실행만 적용)
    parser.add_argument("--center-threshold", type=float)
    parser.add_argument("--item-threshold", type=float)
    parser.add_argument("--ai-lower", type=float)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def load_service_config(path: Path) -> ServiceConfig:
    import yaml

    if not path.exists():
        return ServiceConfig()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return ServiceConfig.from_mapping(data.get("category"))


def load_manifest(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise ValueError(f"gold 매니페스트가 없습니다: {path}")
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        source = (ROOT / row["source"]).resolve()
        if not source.is_file():
            raise ValueError(f"데이터 파일이 없습니다: {source}")
        result = json.loads(source.read_text(encoding="utf-8"))
        input_str = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
        rows.append(
            {
                "item": {
                    "testId": row["itemId"],
                    "title": str(result.get("title", "")),
                    "inputType": str(result.get("type", "")).lower(),
                    "input": input_str,
                    "summary": str(result.get("summary") or ""),
                    "sourcePath": row["source"],
                },
                "gold": {
                    "dataType": row.get("dataType", ""),
                    "goldGroupId": row["goldGroupId"],
                    "goldCategoryName": row["goldCategoryName"],
                    "expectedBehavior": row["expectedBehavior"],
                    "mustNotMergeWithGroupIds": row.get("mustNotMergeWithGroupIds", []),
                    "shouldCreateOrReuseCandidate": row.get("shouldCreateOrReuseCandidate", False),
                },
            }
        )
    return rows


def order_items(rows: list[dict[str, Any]], order_name: str) -> list[dict[str, Any]]:
    if order_name in ("clustered", "grouped"):
        return list(rows)  # 매니페스트가 이미 그룹 연속 순서
    if order_name == "interleaved":
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        group_order: list[str] = []
        for row in rows:
            gid = row["gold"]["goldGroupId"]
            if gid not in groups:
                group_order.append(gid)
            groups[gid].append(row)
        interleaved: list[dict[str, Any]] = []
        index = 0
        while True:
            added = False
            for gid in group_order:
                if index < len(groups[gid]):
                    interleaved.append(groups[gid][index])
                    added = True
            if not added:
                break
            index += 1
        return interleaved
    raise ValueError(f"지원하지 않는 순서: {order_name}")


def counter_clock(base: datetime):
    state = {"n": 0}

    def now() -> datetime:
        state["n"] += 1
        return base + timedelta(seconds=state["n"])

    return now


def build_backend(options: argparse.Namespace):
    if options.mode == "offline":
        return DeterministicBackend()
    return build_real_backend(options)


def run_order(order_name, rows, gold_by_id, backend, config, workspace_id, output) -> dict[str, Any]:
    ordered = order_items(rows, order_name)
    clock = counter_clock(datetime(2026, 8, 4, 17, 0, 0, tzinfo=timezone.utc).astimezone())
    engine = WorkspaceCategoryEngine(workspace_id, PRESET_SEEDS[5], backend, config, now_fn=clock)
    formal_name = {c["id"]: c["name"] for c in engine.formal_categories}

    logs: list[dict[str, Any]] = []
    for order_index, row in enumerate(ordered, start=1):
        log = engine.submit_item(row["item"])
        log["inputOrder"] = order_index
        log["initialFormalCategory"] = engine.formal_categories and log.get("selectedFormalCategoryId")
        logs.append(log)

    # 최신 formal 이름 매핑(승격 포함)
    formal_name = {c["id"]: c["name"] for c in engine.formal_categories}

    # 승격 시점 파악
    promoted_at: dict[int, dict[str, Any]] = {}
    for log in logs:
        if log.get("promoted") and log.get("linkedCandidateId") is not None:
            promoted_at[int(log["linkedCandidateId"])] = {
                "promotedAtItemId": log["itemId"],
                "inputOrder": log["inputOrder"],
                "supportCount": log.get("candidateSupportCount"),
            }

    item_rows = _item_rows(logs, engine, gold_by_id, formal_name)
    candidate_rows = _candidate_rows(engine, gold_by_id, promoted_at)
    metrics = compute_metrics(order_name, logs, item_rows, candidate_rows, engine, gold_by_id, promoted_at)

    output.mkdir(parents=True, exist_ok=True)
    snapshot = engine.snapshot()
    write_json(
        output / "result.json",
        {
            "order": order_name,
            "config": vars(config),
            "selectedItemIds": [r["item"]["testId"] for r in ordered],
            "selectedItemCount": len(ordered),
            "metrics": metrics,
            "snapshot": snapshot,
            "items": item_rows,
            "candidates": candidate_rows,
        },
    )
    _write_csv(output / "items.csv", ITEM_COLUMNS, item_rows)
    _write_csv(output / "candidates.csv", CANDIDATE_COLUMNS, candidate_rows)
    _write_csv(
        output / "categories.csv",
        ["id", "name", "origin", "createdAtItemId", "itemCount"],
        snapshot["formalCategories"],
    )
    report = build_report(order_name, metrics, snapshot, candidate_rows)
    (output / "report.md").write_text(report, encoding="utf-8")
    (output / "report.txt").write_text(report.replace("| ", "").replace("|", " "), encoding="utf-8")
    return {"order": order_name, "metrics": metrics, "itemRows": item_rows, "candidateRows": candidate_rows}


ITEM_COLUMNS = [
    "itemId", "inputOrder", "dataType", "goldGroupId", "goldCategoryName", "expectedBehavior",
    "initialFormalCategory", "formalTopScore", "formalScoreGap", "formalConfident",
    "candidateAction", "candidateEntryDecision", "candidateEntryReason",
    "candidateId", "candidateName", "centerSimilarity", "maxItemSimilarity",
    "supportCountAfter", "wasPromoted", "finalFormalCategory", "wasReclassified",
]
CANDIDATE_COLUMNS = [
    "candidateId", "candidateName", "status", "supportCount", "linkedItemIds",
    "linkedGoldGroupIds", "purity", "createdAtItemId", "promotedAtItemId",
]


def _item_rows(logs, engine, gold_by_id, formal_name) -> list[dict[str, Any]]:
    rows = []
    for log in logs:
        item_id = log["itemId"]
        gold = gold_by_id[item_id]
        classification = engine.item_classifications[item_id]
        final_formal = formal_name.get(classification.formalCategoryId, classification.formalCategoryId)
        rows.append(
            {
                "itemId": item_id,
                "inputOrder": log["inputOrder"],
                "dataType": gold.get("dataType", ""),
                "goldGroupId": gold["goldGroupId"],
                "goldCategoryName": gold["goldCategoryName"],
                "expectedBehavior": gold["expectedBehavior"],
                "formalConfident": log.get("formalConfident"),
                "initialFormalCategory": formal_name.get(
                    log.get("selectedFormalCategoryId"), log.get("selectedFormalCategoryId")
                ),
                "formalTopScore": log.get("formalTopScore"),
                "formalScoreGap": log.get("formalScoreGap"),
                "candidateAction": log.get("candidateAction"),
                "candidateEntryDecision": log.get("candidateEntryDecision"),
                "candidateEntryReason": log.get("candidateEntryReason"),
                "candidateId": log.get("linkedCandidateId"),
                "candidateName": log.get("candidateName"),
                "centerSimilarity": log.get("centerSimilarity"),
                "maxItemSimilarity": log.get("maxItemSimilarity"),
                "supportCountAfter": log.get("candidateSupportCount"),
                "wasPromoted": log.get("promoted", False),
                "finalFormalCategory": final_formal,
                "wasReclassified": item_id in engine.reclassified_item_ids,
            }
        )
    return rows


def _candidate_rows(engine, gold_by_id, promoted_at) -> list[dict[str, Any]]:
    rows = []
    for candidate in engine.candidates:
        linked = candidate.linkedItemIds
        gold_groups = [gold_by_id[i]["goldGroupId"] for i in linked if i in gold_by_id]
        counts = Counter(gold_groups)
        purity = (max(counts.values()) / len(gold_groups)) if gold_groups else 0.0
        promo = promoted_at.get(candidate.candidateId, {})
        rows.append(
            {
                "candidateId": candidate.candidateId,
                "candidateName": candidate.suggestedName,
                "status": candidate.status,
                "supportCount": candidate.supportCount,
                "linkedItemIds": linked,
                "linkedGoldGroupIds": sorted(set(gold_groups)),
                "purity": round(purity, 4),
                "createdAtItemId": candidate.createdAtItemId,
                "promotedAtItemId": promo.get("promotedAtItemId"),
            }
        )
    return rows


def compute_metrics(order_name, logs, item_rows, candidate_rows, engine, gold_by_id, promoted_at) -> dict[str, Any]:
    # 정답 그룹 -> 연결된 후보 집합
    group_candidates: dict[str, set[int]] = defaultdict(set)
    for row in item_rows:
        if row["candidateId"] is not None:
            group_candidates[row["goldGroupId"]].add(int(row["candidateId"]))

    repeated_groups = sorted(
        {g["goldGroupId"] for g in gold_by_id.values() if g["expectedBehavior"] == "CREATE_OR_REUSE_CANDIDATE"}
    )
    fragmentation = {g: len(group_candidates.get(g, set())) for g in repeated_groups}

    entered = [r for r in item_rows if r["candidateAction"] in REUSE_ACTIONS | {"CREATE"}]
    reused = [r for r in entered if r["candidateAction"] in REUSE_ACTIONS]
    reuse_rate = (len(reused) / len(entered)) if entered else 0.0

    purities = [c["purity"] for c in candidate_rows if c["supportCount"] > 0]
    avg_purity = round(sum(purities) / len(purities), 4) if purities else 0.0

    captured = [g for g in repeated_groups if fragmentation.get(g, 0) == 1]
    capture_rate = round(len(captured) / len(repeated_groups), 4) if repeated_groups else 0.0

    # 오병합: mustNotMerge 그룹이 같은 후보에 함께 들어간 경우
    mismerge_events = []
    for candidate in candidate_rows:
        groups = set(candidate["linkedGoldGroupIds"])
        for gid in groups:
            forbidden = set()
            for item_id, gold in gold_by_id.items():
                if gold["goldGroupId"] == gid:
                    forbidden |= set(gold["mustNotMergeWithGroupIds"])
            hit = (groups & forbidden) - {gid}
            if hit:
                mismerge_events.append(
                    {"candidateId": candidate["candidateId"], "group": gid, "with": sorted(hit)}
                )

    # 승격
    promoted = [c for c in engine.candidates if c.status == PROMOTED]
    promoted_records = []
    for candidate in promoted:
        info = promoted_at.get(candidate.candidateId, {})
        row = next((c for c in candidate_rows if c["candidateId"] == candidate.candidateId), {})
        promoted_records.append(
            {
                "candidateId": candidate.candidateId,
                "candidateName": candidate.suggestedName,
                "supportCountAtPromotion": info.get("supportCount"),
                "promotedAtItemId": info.get("promotedAtItemId"),
                "promotedAtOrder": info.get("inputOrder"),
                "purity": row.get("purity"),
                "majorityGoldGroup": (
                    Counter(
                        gold_by_id[i]["goldGroupId"] for i in candidate.linkedItemIds if i in gold_by_id
                    ).most_common(1)[0][0]
                    if candidate.linkedItemIds
                    else None
                ),
            }
        )
    coherent = [p for p in promoted_records if (p["purity"] or 0) >= 0.80]
    promotion_precision = round(len(coherent) / len(promoted_records), 4) if promoted_records else None
    promoted_groups = {p["majorityGoldGroup"] for p in promoted_records}
    promotion_recall = round(
        len(promoted_groups & set(repeated_groups)) / len(repeated_groups), 4
    ) if repeated_groups else None

    # 데이터 유형별 요약
    existing_rows = [r for r in item_rows if r.get("dataType") == "EXISTING_FORMAL"]
    existing_formal_only = [r for r in existing_rows if r["candidateId"] is None]
    existing_spurious = [r for r in existing_rows if r["candidateId"] is not None]
    new5_frag = len({r["candidateId"] for r in item_rows if r["goldGroupId"] == "NEW_GROUP_5" and r["candidateId"] is not None})
    new3_frag = len({r["candidateId"] for r in item_rows if r["goldGroupId"] == "NEW_GROUP_3" and r["candidateId"] is not None})

    return {
        "order": order_name,
        "selectedItemCount": len(item_rows),
        "existingFormalCount": len(existing_rows),
        "existingFormalOnlyCount": len(existing_formal_only),
        "existingSpuriousCandidateCount": len(existing_spurious),
        "existingSpuriousItemIds": [r["itemId"] for r in existing_spurious],
        "newGroup5CandidateCount": new5_frag,
        "newGroup3CandidateCount": new3_frag,
        "fragmentationByGroup": fragmentation,
        "maxFragmentation": max(fragmentation.values()) if fragmentation else 0,
        "candidateReuseRate": round(reuse_rate, 4),
        "enteredCandidateStage": len(entered),
        "reuseEvents": len(reused),
        "avgCandidatePurity": avg_purity,
        "groupCaptureRate": capture_rate,
        "capturedGroups": captured,
        "repeatedGroups": repeated_groups,
        "promotedCount": len(promoted_records),
        "promotedRecords": promoted_records,
        "promotionPrecision": promotion_precision,
        "promotionRecall": promotion_recall,
        "reclassifiedItemCount": len(engine.reclassified_item_ids),
        "misMergeEventCount": len(mismerge_events),
        "misMergeEvents": mismerge_events,
        "finalFormalCategoryCount": len(engine.formal_categories),
        "exceededMaxFormalCategories": len(engine.formal_categories) > engine.config.max_count,
        "candidateErrorCount": sum(1 for log in logs if log.get("candidateError")),
    }


def _write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    k: (";".join(map(str, v)) if isinstance(v, list) else v)
                    for k, v in row.items()
                    if k in columns
                }
            )


def _cell(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def build_report(order_name, metrics, snapshot, candidate_rows) -> str:
    lines = [
        f"# 집중 증분 카테고리 실행: {order_name}",
        "",
        "## 지표",
        f"- 선택 데이터 수: {metrics['selectedItemCount']}",
        f"- 최종 정식 카테고리 수: {metrics['finalFormalCategoryCount']} (10 초과: {'예' if metrics['exceededMaxFormalCategories'] else '아니오'})",
        f"- 후보 재사용률: {metrics['candidateReuseRate']:.2%} (재사용 {metrics['reuseEvents']}/{metrics['enteredCandidateStage']})",
        f"- 평균 후보 순도: {metrics['avgCandidatePurity']}",
        f"- 그룹 포착률: {metrics['groupCaptureRate']:.2%} (포착 {metrics['capturedGroups']})",
        f"- 최대 파편화: {metrics['maxFragmentation']}",
        f"- 승격 수: {metrics['promotedCount']} / 정밀도 {metrics['promotionPrecision']} / 재현율 {metrics['promotionRecall']}",
        f"- 재분류 데이터 수: {metrics['reclassifiedItemCount']}",
        f"- 오병합 건수: {metrics['misMergeEventCount']} (목표 0)",
        f"- 후보 처리 에러: {metrics['candidateErrorCount']}",
        "",
        "## 정답 그룹별 후보 파편화",
        "| goldGroupId | 후보 수 |",
        "|---|--:|",
    ]
    for gid, count in metrics["fragmentationByGroup"].items():
        lines.append(f"| {_cell(gid)} | {count} |")
    lines += ["", "## 임시 후보", "| ID | 이름 | 상태 | 지지 | 순도 | 연결 그룹 |", "|---|---|---|--:|--:|---|"]
    for candidate in candidate_rows:
        lines.append(
            f"| {candidate['candidateId']} | {_cell(candidate['candidateName'])} | {_cell(candidate['status'])} "
            f"| {candidate['supportCount']} | {candidate['purity']} | {_cell(','.join(candidate['linkedGoldGroupIds']))} |"
        )
    lines += ["", "## 승격 결과"]
    if metrics["promotedRecords"]:
        lines += ["| 후보 | 승격 시점(itemId/순번) | 승격 supportCount | 순도 | 대표 그룹 |", "|---|---|--:|--:|---|"]
        for p in metrics["promotedRecords"]:
            lines.append(
                f"| {_cell(p['candidateName'])} | {_cell(p['promotedAtItemId'])}/{_cell(p['promotedAtOrder'])} "
                f"| {_cell(p['supportCountAtPromotion'])} | {_cell(p['purity'])} | {_cell(p['majorityGoldGroup'])} |"
            )
    else:
        lines.append("- 승격된 후보 없음")
    return "\n".join(lines) + "\n"


def write_comparison(output: Path, results: list[dict[str, Any]]) -> None:
    summaries = [r["metrics"] for r in results]
    write_json(output / "focused-comparison.json", {"orders": summaries})
    keys = [
        ("order", "순서"), ("selectedItemCount", "데이터 수"), ("finalFormalCategoryCount", "정식 수"),
        ("candidateReuseRate", "재사용률"), ("avgCandidatePurity", "평균 순도"),
        ("groupCaptureRate", "포착률"), ("maxFragmentation", "최대 파편화"),
        ("promotedCount", "승격 수"), ("misMergeEventCount", "오병합"),
        ("reclassifiedItemCount", "재분류"), ("candidateErrorCount", "에러"),
    ]
    _write_csv(output / "focused-comparison.csv", [k for k, _ in keys], summaries)

    lines = ["# 집중 증분 카테고리 비교 (clustered vs interleaved)", "",
             "| " + " | ".join(label for _, label in keys) + " |",
             "|" + "|".join("---" for _ in keys) + "|"]
    for s in summaries:
        lines.append("| " + " | ".join(_cell(s.get(k)) for k, _ in keys) + " |")
    # 순서 안정성: 그룹별 파편화 비교, 승격 그룹 일치
    lines += ["", "## 순서 안정성"]
    if len(summaries) == 2:
        a, b = summaries
        groups = sorted(set(a["fragmentationByGroup"]) | set(b["fragmentationByGroup"]))
        lines += ["| goldGroupId | clustered | interleaved | 동일? |", "|---|--:|--:|:--:|"]
        for g in groups:
            fa = a["fragmentationByGroup"].get(g)
            fb = b["fragmentationByGroup"].get(g)
            lines.append(f"| {g} | {fa} | {fb} | {'O' if fa == fb else 'X'} |")
        pa = {p["majorityGoldGroup"] for p in a["promotedRecords"]}
        pb = {p["majorityGoldGroup"] for p in b["promotedRecords"]}
        lines += ["", f"- 승격 그룹 (clustered): {sorted(pa)}", f"- 승격 그룹 (interleaved): {sorted(pb)}",
                  f"- 승격 그룹 일치: {'예' if pa == pb else '아니오'}"]
    (output / "focused-comparison-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def planned_output(mode: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = ROOT / "results" / f"{ts}-focused-incremental-{mode}"
    candidate, index = base, 1
    while candidate.exists():
        candidate = Path(f"{base}-{index}")
        index += 1
    return candidate


def main(argv: list[str] | None = None) -> int:
    options = parse_args(argv)
    try:
        import dataclasses

        config = load_service_config(options.config)
        overrides = {}
        if options.center_threshold is not None:
            overrides["center_similarity_threshold"] = options.center_threshold
        if options.item_threshold is not None:
            overrides["item_similarity_threshold"] = options.item_threshold
        if options.ai_lower is not None:
            overrides["ai_review_lower_bound"] = options.ai_lower
        if overrides:
            config = dataclasses.replace(config, **overrides)
        rows = load_manifest(options.manifest)
        gold_by_id = {r["item"]["testId"]: r["gold"] for r in rows}
        output = options.output.resolve() if options.output else planned_output(options.mode)

        print(f"[OK] 모드: {options.mode} | 데이터셋: {options.dataset} | 데이터 {len(rows)}건")
        print(f"[OK] 선택 itemId: {', '.join(r['item']['testId'] for r in rows)}")
        print(f"[OK] 순서: {', '.join(options.order)} | 결과 폴더: {output}")
        print(
            f"[OK] 재사용 임계값 center={config.center_similarity_threshold} "
            f"item={config.item_similarity_threshold} ai-lower={config.ai_review_lower_bound}"
        )
        if options.dry_run:
            for order in options.order:
                seq = [r["item"]["testId"] for r in order_items(rows, order)]
                print(f"  - {order}: {' '.join(seq)}")
            print("[DRY-RUN] 실행하지 않았습니다. (기존 112건은 로딩·호출하지 않음)")
            return 0

        backend = build_backend(options)
        output.mkdir(parents=True, exist_ok=bool(options.output))
        results = []
        for order in options.order:
            print(f"\n[ORDER] {order}")
            results.append(
                run_order(order, rows, gold_by_id, backend, config, options.workspace_id, output / order)
            )
        write_json(
            output / "run-summary.json",
            {
                "mode": options.mode,
                "dataset": options.dataset,
                "selectedItemIds": [r["item"]["testId"] for r in rows],
                "selectedItemCount": len(rows),
                "orders": options.order,
                "config": vars(config),
            },
        )
        write_comparison(output, results)
        print(f"\n[OK] 완료: {output}")
        print(f"[비교] {output / 'focused-comparison-report.md'}")
        return 0
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError) as exc:
        print(f"[FAIL] {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
