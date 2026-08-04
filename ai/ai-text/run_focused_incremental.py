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
    build_embedding_text,
    build_service_text,
    cosine_similarity,
    summarize_run,
)
from src.dynamic_category_experiment import PRESET_SEEDS
from src.result_writer import write_json

ROOT = Path(__file__).resolve().parent
DEFAULT_MANIFEST = ROOT / "dataset" / "tester" / "focused-incremental" / "focused-gold.jsonl"
CONFIG_PATH = ROOT / "config" / "incremental-category.yaml"
REUSE_ACTIONS = {"REUSE_EMBEDDING", "REUSE_AI", "REUSE_FINAL_DEDUP", "REUSE_ENTITY"}


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
    parser.add_argument("--signal-threshold", type=float, help="잠정 신호 매칭 유사도(미지정 시 center와 동일)")
    parser.add_argument(
        "--use-core-entity",
        action="store_true",
        help="핵심 대상(엔티티) 기반 매칭 + 제목+요약 임베딩 정제 실험 모드 활성화",
    )
    parser.add_argument(
        "--entity-min-confidence",
        type=float,
        help="엔티티를 신뢰해 매칭에 쓰는 최소 confidence(기본 0.5)",
    )
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


def _group_similarity_stats(vectors: dict[str, list[float]], ids: list[str], gold_by_id) -> dict[str, Any]:
    """정제/본문 임베딩 벡터로 그룹 내부·간 유사도와 최근접 동일그룹 확률을 계산한다."""
    groups: dict[str, list[str]] = defaultdict(list)
    for i in ids:
        groups[gold_by_id[i]["goldGroupId"]].append(i)

    per_group: dict[str, Any] = {}
    for gid, members in groups.items():
        sims = []
        for a in range(len(members)):
            for b in range(a + 1, len(members)):
                va, vb = vectors.get(members[a]), vectors.get(members[b])
                if va and vb:
                    sims.append(cosine_similarity(va, vb))
        per_group[gid] = {
            "pairs": len(sims),
            "avg": round(sum(sims) / len(sims), 4) if sims else None,
            "min": round(min(sims), 4) if sims else None,
            "max": round(max(sims), 4) if sims else None,
        }

    cross_max = 0.0
    for x in range(len(ids)):
        for y in range(x + 1, len(ids)):
            i, j = ids[x], ids[y]
            if gold_by_id[i]["goldGroupId"] == gold_by_id[j]["goldGroupId"]:
                continue
            vi, vj = vectors.get(i), vectors.get(j)
            if vi and vj:
                cross_max = max(cross_max, cosine_similarity(vi, vj))

    same, total = 0, 0
    for i in ids:
        vi = vectors.get(i)
        if not vi:
            continue
        best, best_sim = None, -2.0
        for j in ids:
            if j == i:
                continue
            vj = vectors.get(j)
            if not vj:
                continue
            s = cosine_similarity(vi, vj)
            if s > best_sim:
                best, best_sim = j, s
        if best is not None:
            total += 1
            if gold_by_id[best]["goldGroupId"] == gold_by_id[i]["goldGroupId"]:
                same += 1
    return {
        "perGroup": per_group,
        "crossGroupMax": round(cross_max, 4),
        "nearestNeighborSameGroupProb": round(same / total, 4) if total else None,
    }


def similarity_analysis(rows, gold_by_id, backend) -> dict[str, Any]:
    """제목+요약(정제) vs 제목+요약+본문(기존) 임베딩의 그룹 유사도를 비교 측정한다.

    엔진 결정과 무관한 '측정용' 계산이다. 두 입력 방식 모두 백엔드에서 직접 임베딩해
    (캐시 활용) 사과 대 사과로 비교한다.
    """
    ids = [r["item"]["testId"] for r in rows]
    item_by_id = {r["item"]["testId"]: r["item"] for r in rows}
    refined_vectors, body_vectors = {}, {}
    for i in ids:
        item = item_by_id[i]
        try:
            refined_vectors[i] = backend.embed(build_embedding_text(item))
            body_vectors[i] = backend.embed(build_service_text(item))
        except Exception:  # noqa: BLE001 - 측정 실패는 해당 항목만 건너뛴다
            continue
    return {
        "refined_title_summary": _group_similarity_stats(refined_vectors, ids, gold_by_id),
        "legacy_title_summary_body": _group_similarity_stats(body_vectors, ids, gold_by_id),
    }


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
    analysis = similarity_analysis(ordered, gold_by_id, backend)

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
            "similarityAnalysis": analysis,
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
    return {
        "order": order_name, "metrics": metrics, "itemRows": item_rows,
        "candidateRows": candidate_rows, "similarityAnalysis": analysis,
    }


ITEM_COLUMNS = [
    "itemId", "title", "inputOrder", "dataType", "goldGroupId", "goldCategoryName", "expectedBehavior",
    "initialFormalCategory", "formalTopScore", "formalScoreGap", "formalConfident",
    "coreEntityName", "normalizedEntityName", "coreEntityType", "entityConfidence",
    "matchMethod", "matchedCandidateName",
    "candidateAction", "candidateEntryDecision", "candidateEntryReason",
    "signalAction", "signalId",
    "candidateId", "candidateName", "centerSimilarity", "maxItemSimilarity", "embeddingSimilarity",
    "supportCountAfter", "wasPromoted", "finalFormalCategory", "finalCategoryIds", "wasReclassified",
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
        final_ids = [formal_name.get(cid, cid) for cid in classification.formalCategoryIds]
        center = log.get("centerSimilarity")
        max_item = log.get("maxItemSimilarity")
        emb_sim = None
        if center is not None or max_item is not None:
            emb_sim = round(max(center or 0.0, max_item or 0.0), 4)
        rows.append(
            {
                "itemId": item_id,
                "title": log.get("title", ""),
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
                "coreEntityName": log.get("coreEntityName"),
                "normalizedEntityName": log.get("normalizedEntityName"),
                "coreEntityType": log.get("coreEntityType"),
                "entityConfidence": log.get("entityConfidence"),
                "matchMethod": log.get("matchMethod"),
                "matchedCandidateName": log.get("matchedCandidateName"),
                "candidateAction": log.get("candidateAction"),
                "candidateEntryDecision": log.get("candidateEntryDecision"),
                "candidateEntryReason": log.get("candidateEntryReason"),
                "signalAction": log.get("signalAction"),
                "signalId": log.get("signalId"),
                "candidateId": log.get("linkedCandidateId"),
                "candidateName": log.get("candidateName"),
                "centerSimilarity": center,
                "maxItemSimilarity": max_item,
                "embeddingSimilarity": emb_sim,
                "supportCountAfter": log.get("candidateSupportCount"),
                "wasPromoted": log.get("promoted", False),
                "finalFormalCategory": final_formal,
                "finalCategoryIds": final_ids,
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
    existing_signal_only = [
        r for r in existing_rows if r["candidateId"] is None and r.get("signalAction") == "STORE_SIGNAL"
    ]
    signals = getattr(engine, "signals", [])
    signal_metrics = {
        "provisionalSignalCount": len(signals),
        "convertedSignalCount": sum(1 for s in signals if s.status == "CONVERTED"),
        "waitingSignalCount": sum(1 for s in signals if s.status == "WAITING"),
        "expiredSignalCount": sum(1 for s in signals if s.status == "EXPIRED"),
        "existingSignalOnlyCount": len(existing_signal_only),
    }
    new5_frag = len({r["candidateId"] for r in item_rows if r["goldGroupId"] == "NEW_GROUP_5" and r["candidateId"] is not None})
    new3_frag = len({r["candidateId"] for r in item_rows if r["goldGroupId"] == "NEW_GROUP_3" and r["candidateId"] is not None})

    # 매칭 방법 분포(ENTITY_EXACT/ENTITY_ALIAS/EMBEDDING/AI_REVIEW)
    match_method_counts = dict(
        Counter(r.get("matchMethod") for r in item_rows if r.get("matchMethod"))
    )
    # 에러 분류: API/파싱(엔티티·AI 응답 실패) vs 후보 처리 예외(폴백)
    item_entities = getattr(engine, "_item_entities", {})
    entity_api_failures = sum(
        1 for e in item_entities.values()
        if isinstance(e, dict) and (e.get("entityError") == "API" or e.get("entityEvidence") == "AI 응답 실패")
    )
    ai_response_failures = sum(
        1 for log in logs if isinstance(log.get("candidateEntryReason"), str)
        and "AI 응답 실패" in log.get("candidateEntryReason", "")
    )
    fallback_errors = sum(1 for log in logs if log.get("candidateError"))

    return {
        "order": order_name,
        "selectedItemCount": len(item_rows),
        "existingFormalCount": len(existing_rows),
        "existingFormalOnlyCount": len(existing_formal_only),
        "existingSpuriousCandidateCount": len(existing_spurious),
        "existingSpuriousItemIds": [r["itemId"] for r in existing_spurious],
        **signal_metrics,
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
        "candidateErrorCount": fallback_errors,
        "matchMethodCounts": match_method_counts,
        "entityApiFailureCount": entity_api_failures,
        "aiResponseFailureCount": ai_response_failures,
        "fallbackErrorCount": fallback_errors,
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
        f"- 잠정 신호: 총 {metrics['provisionalSignalCount']} / 전환 {metrics['convertedSignalCount']} / 대기 {metrics['waitingSignalCount']} / 만료 {metrics['expiredSignalCount']}",
        f"- 기존 22건: 후보 {metrics['existingSpuriousCandidateCount']} / 신호만 {metrics['existingSignalOnlyCount']} / FORMAL_ONLY {metrics['existingFormalOnlyCount']}",
        f"- 후보 재사용률: {metrics['candidateReuseRate']:.2%} (재사용 {metrics['reuseEvents']}/{metrics['enteredCandidateStage']})",
        f"- 평균 후보 순도: {metrics['avgCandidatePurity']}",
        f"- 그룹 포착률: {metrics['groupCaptureRate']:.2%} (포착 {metrics['capturedGroups']})",
        f"- 최대 파편화: {metrics['maxFragmentation']}",
        f"- 승격 수: {metrics['promotedCount']} / 정밀도 {metrics['promotionPrecision']} / 재현율 {metrics['promotionRecall']}",
        f"- 재분류 데이터 수: {metrics['reclassifiedItemCount']}",
        f"- 오병합 건수: {metrics['misMergeEventCount']} (목표 0)",
        f"- 매칭 방법: {metrics.get('matchMethodCounts') or '(없음)'}",
        f"- 에러: 엔티티API {metrics.get('entityApiFailureCount', 0)} / AI응답 {metrics.get('aiResponseFailureCount', 0)} / 폴백 {metrics.get('fallbackErrorCount', 0)}",
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
        ("provisionalSignalCount", "잠정신호"), ("convertedSignalCount", "전환"),
        ("maxFragmentation", "최대파편화"),
        ("candidateReuseRate", "재사용률"), ("groupCaptureRate", "포착률"),
        ("promotedCount", "승격 수"), ("misMergeEventCount", "오병합"),
        ("reclassifiedItemCount", "재분류"),
        ("entityApiFailureCount", "엔티티API실패"), ("aiResponseFailureCount", "AI응답실패"),
        ("fallbackErrorCount", "폴백에러"),
    ]
    _write_csv(output / "focused-comparison.csv", [k for k, _ in keys], summaries)

    lines = ["# 집중 증분 카테고리 비교 (제목+요약 엔티티 모드)", "",
             "| " + " | ".join(label for _, label in keys) + " |",
             "|" + "|".join("---" for _ in keys) + "|"]
    for s in summaries:
        lines.append("| " + " | ".join(_cell(s.get(k)) for k, _ in keys) + " |")

    # 매칭 방법 분포
    lines += ["", "## 매칭 방법 분포 (ENTITY_EXACT / ENTITY_ALIAS / EMBEDDING / AI_REVIEW)"]
    for s in summaries:
        mm = s.get("matchMethodCounts") or {}
        detail = ", ".join(f"{k}:{v}" for k, v in sorted(mm.items())) or "(없음)"
        lines.append(f"- {s['order']}: {detail}")

    # 임베딩 유사도 비교: 제목+요약(정제) vs 제목+요약+본문(기존)
    analysis = results[0].get("similarityAnalysis") if results else None
    if analysis:
        refined = analysis["refined_title_summary"]["perGroup"]
        body = analysis["legacy_title_summary_body"]["perGroup"]
        lines += [
            "", "## 그룹 내부 유사도: 제목+요약(정제) vs 제목+요약+본문(기존)",
            "| goldGroupId | 쌍수 | 정제avg | 정제min | 정제max | 본문avg | 본문min | 본문max | avg변화 |",
            "|---|--:|--:|--:|--:|--:|--:|--:|--:|",
        ]
        for gid in sorted(refined):
            r, b = refined[gid], body.get(gid, {})
            delta = (
                round((r["avg"] or 0) - (b.get("avg") or 0), 4)
                if r.get("avg") is not None and b.get("avg") is not None else None
            )
            lines.append(
                f"| {_cell(gid)} | {r['pairs']} | {_cell(r['avg'])} | {_cell(r['min'])} | {_cell(r['max'])} "
                f"| {_cell(b.get('avg'))} | {_cell(b.get('min'))} | {_cell(b.get('max'))} | {_cell(delta)} |"
            )
        rr = analysis["refined_title_summary"]
        bb = analysis["legacy_title_summary_body"]
        lines += [
            "",
            f"- 서로 다른 그룹 간 최대 유사도: 정제 {rr['crossGroupMax']} / 본문 {bb['crossGroupMax']}",
            f"- 최근접 데이터가 같은 그룹일 확률: 정제 {rr['nearestNeighborSameGroupProb']} "
            f"/ 본문 {bb['nearestNeighborSameGroupProb']}",
        ]
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
        if options.signal_threshold is not None:
            overrides["signal_similarity_threshold"] = options.signal_threshold
        elif options.center_threshold is not None:
            # 신호 매칭 임계값을 명시하지 않으면 center와 동일하게 맞춘다.
            overrides["signal_similarity_threshold"] = options.center_threshold
        if options.use_core_entity:
            overrides["use_core_entity"] = True
        if options.entity_min_confidence is not None:
            overrides["entity_min_confidence"] = options.entity_min_confidence
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
        print(
            f"[OK] 임베딩 입력: {'제목+요약(엔티티 모드)' if config.use_core_entity else '제목+요약+본문'}"
            f" | 엔티티 매칭: {'ON' if config.use_core_entity else 'OFF'}"
            + (f" (min-conf={config.entity_min_confidence})" if config.use_core_entity else "")
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
