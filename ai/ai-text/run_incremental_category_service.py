"""112개 테스트 데이터를 실제 서비스처럼 한 건씩 입력해 증분 카테고리 흐름을 실행한다.

original / shuffle-42 / shuffle-84 세 순서로 각각 실행하고, 데이터별 처리 로그와
최종 정식 카테고리·임시 후보 상태, 순서별 비교 보고서를 저장한다.

기본은 API를 호출하지 않는 오프라인 결정론 모드다. ``--mode real``을 지정하면
GMS 임베딩과 AI 모델을 사용하는 백엔드로 교체한다.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import main as base_runner
from src.dataset_loader import load_flat_test_dataset
from src.dynamic_category_experiment import PRESET_SEEDS, apply_ordering, resolve_orderings
from src.incremental_category_service import (
    DeterministicBackend,
    ServiceBackend,
    ServiceConfig,
    WorkspaceCategoryEngine,
    build_service_text,
    summarize_run,
)
from src.model_config import ModelConfigError, load_models, safe_filename, select_models
from src.result_writer import write_json
from src.settings import load_settings

ROOT = Path(__file__).resolve().parent
DEFAULT_DATASET_ROOT = ROOT / "dataset" / "tester" / "정우현"
CONFIG_PATH = ROOT / "config" / "incremental-category.yaml"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="증분 카테고리 서비스 시뮬레이션 (데이터 한 건씩 입력)"
    )
    parser.add_argument("--mode", choices=("offline", "real"), default="offline")
    parser.add_argument("--model", default="openrouter-qwen3-8b")
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument(
        "--input-type", nargs="+", choices=("url", "image", "memo", "all"), default=["url"]
    )
    parser.add_argument(
        "--order", nargs="+", default=["original", "shuffle-42", "shuffle-84"]
    )
    parser.add_argument("--workspace-id", type=int, default=10)
    parser.add_argument("--test-ids", nargs="+")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def load_service_config(path: Path) -> ServiceConfig:
    import yaml

    if not path.exists():
        return ServiceConfig()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return ServiceConfig.from_mapping(data.get("category"))


def load_seed_categories() -> list[dict[str, Any]]:
    return [dict(item) for item in PRESET_SEEDS[5]]


def load_items(options: argparse.Namespace) -> list[dict[str, Any]]:
    dataset_root = options.dataset_root.resolve()
    data, _categories = load_flat_test_dataset(dataset_root, options.input_type)
    for item in data:
        # url 데이터는 저장된 summary를 서비스 입력으로 함께 사용한다.
        item.setdefault("summary", _summary_of(item))
    if options.test_ids:
        requested = set(options.test_ids)
        data = [item for item in data if item["testId"] in requested]
    if options.limit is not None:
        if options.limit < 1:
            raise ValueError("--limit은 1 이상이어야 합니다.")
        data = data[: options.limit]
    if not data:
        raise ValueError("입력할 데이터가 없습니다.")
    return data


def _summary_of(item: dict[str, Any]) -> str:
    try:
        value = json.loads(str(item.get("input", "")))
    except json.JSONDecodeError:
        return ""
    if not isinstance(value, dict):
        return ""
    return str(value.get("summary") or value.get("preview", {}).get("description") or "").strip()


def counter_clock(base: datetime) -> Callable[[], datetime]:
    state = {"n": 0}

    def now() -> datetime:
        state["n"] += 1
        return base + timedelta(seconds=state["n"])

    return now


def build_backend(options: argparse.Namespace) -> ServiceBackend:
    if options.mode == "offline":
        return DeterministicBackend()
    return build_real_backend(options)


# ---- 실제 API 백엔드 ----


def build_real_backend(options: argparse.Namespace) -> ServiceBackend:
    from openai import OpenAI

    project_config = base_runner.load_project_config()
    settings = load_settings(ROOT)
    models = load_models(ROOT / "config" / "models.yaml")
    selection = select_models(models, [options.model], "category-only")[0]
    if selection.status != "READY" or selection.config is None:
        raise ModelConfigError(selection.error_message or f"모델을 쓸 수 없습니다: {options.model}")
    providers = base_runner.make_providers(project_config, settings, {selection.config.provider})
    provider = providers[selection.config.provider]

    openai_config = project_config.get("openai", {})
    key_env = str(openai_config.get("apiKeyEnv", "GMS_KEY"))
    api_key = settings.key_for(key_env)
    if not api_key:
        raise ModelConfigError(f"임베딩 API 키가 없습니다: {key_env}")
    kwargs: dict[str, Any] = {"api_key": api_key, "max_retries": 0}
    base_url = str(openai_config.get("baseUrl", "")).strip()
    if base_url:
        kwargs["base_url"] = base_url
    embedding_model = str(project_config.get("embedding", {}).get("model", "text-embedding-3-small"))
    return RealServiceBackend(
        provider=provider,
        config=selection.config,
        embedding_client=OpenAI(**kwargs),
        embedding_model=embedding_model,
    )


class RealServiceBackend:
    """GMS 임베딩 + AI 모델을 사용하는 실제 백엔드. offline 백엔드와 동일 인터페이스."""

    def __init__(self, provider: Any, config: Any, embedding_client: Any, embedding_model: str) -> None:
        from src.providers import ModelRequest

        self._provider = provider
        self._config = config
        self._client = embedding_client
        self._embedding_model = embedding_model
        self._ModelRequest = ModelRequest
        self._embed_cache: dict[str, list[float]] = {}

    def embed(self, text: str) -> list[float]:
        from src.embedding_pipeline import extract_embedding_vectors, input_hash

        key = input_hash(text)
        cached = self._embed_cache.get(key)
        if cached is not None:
            return cached
        response = self._client.embeddings.create(model=self._embedding_model, input=[text])
        vector = extract_embedding_vectors(response, 1)[0]
        self._embed_cache[key] = vector
        return vector

    def _ask(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any] | None:
        from src.dynamic_category_experiment import _balanced_json

        request = self._ModelRequest(
            prompt=prompt, schema=schema, test_mode="incremental-category", test_id="svc", temperature=0
        )
        response = self._provider.generate(request, self._config)
        if response.status != "SUCCESS":
            return None
        candidate, _span = _balanced_json(str(response.raw_text).strip())
        if candidate is None:
            return None
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def classify_formal(
        self, item: dict[str, Any], formal_categories: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        catalog = "\n".join(
            f"- {c['id']} | {c['name']}: {c.get('description', '')}" for c in formal_categories
        )
        prompt = (
            "다음 데이터가 각 카테고리에 얼마나 맞는지 0.0~1.0 점수로 평가하세요.\n"
            "JSON만 출력: {\"scores\":[{\"categoryId\":\"ID\",\"score\":0.0}]}\n\n"
            f"카테고리:\n{catalog}\n\n데이터:\n{build_service_text(item)[:1500]}\n"
        )
        schema = {
            "type": "object",
            "properties": {
                "scores": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "categoryId": {"type": "string"},
                            "score": {"type": "number"},
                        },
                        "required": ["categoryId", "score"],
                    },
                }
            },
            "required": ["scores"],
        }
        parsed = self._ask(prompt, schema)
        valid_ids = {str(c["id"]) for c in formal_categories}
        result: list[dict[str, Any]] = []
        if parsed:
            for entry in parsed.get("scores", []):
                cid = str(entry.get("categoryId", ""))
                if cid in valid_ids:
                    try:
                        score = max(0.0, min(1.0, float(entry.get("score", 0.0))))
                    except (TypeError, ValueError):
                        score = 0.0
                    result.append({"categoryId": cid, "score": score})
        scored = {entry["categoryId"] for entry in result}
        for cid in valid_ids - scored:
            result.append({"categoryId": cid, "score": 0.0})
        return result

    def propose_candidate(
        self,
        item: dict[str, Any],
        formal_categories: list[dict[str, Any]],
        top_scores: list[dict[str, Any]],
    ) -> dict[str, Any]:
        names = ", ".join(c["name"] for c in formal_categories)
        prompt = (
            "기존 정식 카테고리로 표현하기 어려운 반복 주제인지 판단하세요.\n"
            "필요하면 2~12자 명사형 새 카테고리 이름을 제안하세요. 특정 제목·연도·지역·브랜드는 피하고,\n"
            "다른 유사 데이터도 포함할 수 있는 범위로, 기존 카테고리와 의미가 겹치지 않게 지으세요.\n"
            "JSON만 출력: {\"needsNew\":true,\"name\":\"이름\",\"description\":\"설명\",\"reason\":\"이유\"}\n\n"
            f"기존 정식 카테고리: {names}\n\n데이터:\n{build_service_text(item)[:1500]}\n"
        )
        schema = {
            "type": "object",
            "properties": {
                "needsNew": {"type": "boolean"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["needsNew", "name", "description", "reason"],
        }
        parsed = self._ask(prompt, schema)
        if not parsed:
            return {"needsNew": False, "name": "", "description": "", "reason": "AI 응답 실패"}
        return {
            "needsNew": bool(parsed.get("needsNew")),
            "name": str(parsed.get("name", "")).strip(),
            "description": str(parsed.get("description", "")).strip(),
            "reason": str(parsed.get("reason", "")).strip(),
        }

    def review_promotion(self, candidate: Any, linked_items: list[dict[str, Any]]) -> dict[str, Any]:
        titles = "\n".join(f"- {entry.get('title', '')}" for entry in linked_items)
        prompt = (
            "다음 데이터들이 하나의 일관된 반복 주제인지 검토하세요. 사용 목적이 제각각이면 승격하지 마세요.\n"
            "JSON만 출력: {\"promote\":true,\"reason\":\"이유\"}\n\n"
            f"후보 이름: {candidate.suggestedName}\n연결 데이터:\n{titles}\n"
        )
        schema = {
            "type": "object",
            "properties": {"promote": {"type": "boolean"}, "reason": {"type": "string"}},
            "required": ["promote", "reason"],
        }
        parsed = self._ask(prompt, schema)
        if not parsed:
            return {"promote": False, "reason": "AI 응답 실패"}
        return {"promote": bool(parsed.get("promote")), "reason": str(parsed.get("reason", "")).strip()}

    def review_reuse(self, item: dict[str, Any], candidate_infos: list[dict[str, Any]]) -> dict[str, Any]:
        from src.incremental_category_service import build_service_text

        lines = []
        for info in candidate_infos:
            reps = "; ".join(
                f"{r.get('title','')}({r.get('summary','')[:40]})"
                for r in info.get("representativeItems", [])
            )
            lines.append(
                f"- candidateId={info['candidateId']} | 이름:{info['name']} | 설명:{info.get('description','')} "
                f"| 연결수:{info['supportCount']} | center:{info['centerSimilarity']} max:{info['maxItemSimilarity']} "
                f"| 대표:{reps}"
            )
        prompt = (
            "새 데이터가 아래 기존 임시 후보 중 하나와 '같은 반복 주제'인지 판단하세요.\n"
            "같으면 그 후보를 재사용(REUSE), 명확히 구분되는 새 주제면 생성(CREATE)입니다.\n"
            "형식만 같고 목적이 다르면 재사용하지 마세요. JSON만 출력하세요:\n"
            "{\"action\":\"REUSE\"|\"CREATE\",\"candidateId\":정수또는null,\"confidence\":0.0,\"reason\":\"근거\"}\n\n"
            f"새 데이터:\n제목: {item.get('title','')}\n내용: {build_service_text(item)[:800]}\n\n"
            f"기존 후보:\n" + "\n".join(lines) + "\n"
        )
        schema = {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["REUSE", "CREATE"]},
                "candidateId": {"type": ["integer", "null"]},
                "confidence": {"type": "number"},
                "reason": {"type": "string"},
            },
            "required": ["action", "confidence", "reason"],
        }
        parsed = self._ask(prompt, schema)
        if not parsed:
            return {"action": "CREATE", "candidateId": None, "confidence": 0.0, "reason": "AI 응답 실패"}
        cid = parsed.get("candidateId")
        return {
            "action": str(parsed.get("action", "CREATE")).upper(),
            "candidateId": int(cid) if isinstance(cid, (int, float)) else None,
            "confidence": float(parsed.get("confidence", 0.0) or 0.0),
            "reason": str(parsed.get("reason", "")).strip(),
        }


# ---- 실행 및 보고서 ----

ITEM_COLUMNS = [
    "itemId",
    "inputOrder",
    "selectedFormalCategoryId",
    "selectedFormalCategoryIds",
    "formalTopScore",
    "formalScoreGap",
    "ambiguous",
    "matchedExistingCandidate",
    "linkedCandidateId",
    "newCandidateCreated",
    "candidateSupportCount",
    "promoted",
    "reclassified",
    "formalCategoryCount",
    "candidateCount",
    "classificationStatus",
    "candidateError",
]


def _write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: (
                        ";".join(map(str, value)) if isinstance(value, list) else value
                    )
                    for key, value in row.items()
                    if key in columns
                }
            )


def run_order(
    order_name: str,
    items: list[dict[str, Any]],
    seeds: list[dict[str, Any]],
    backend: ServiceBackend,
    config: ServiceConfig,
    workspace_id: int,
    output: Path,
) -> dict[str, Any]:
    ordered, order_seed = apply_ordering(items, order_name)
    clock = counter_clock(datetime(2026, 8, 4, 13, 0, 0, tzinfo=timezone.utc).astimezone())
    engine = WorkspaceCategoryEngine(
        workspace_id, seeds, backend, config, now_fn=clock
    )
    logs: list[dict[str, Any]] = []
    for index, item in enumerate(ordered, start=1):
        log = engine.submit_item(item)
        log["inputOrder"] = index
        logs.append(log)
        print(
            f"  [{index}/{len(ordered)}] {log['itemId']} "
            f"formal={log['selectedFormalCategoryId']} score={log.get('formalTopScore')} "
            f"cand={log.get('linkedCandidateId')} promoted={log.get('promoted')}"
        )

    snapshot = engine.snapshot()
    summary = summarize_run(engine)
    summary["order"] = order_name
    summary["randomSeed"] = order_seed

    output.mkdir(parents=True, exist_ok=True)
    write_json(
        output / "result.json",
        {
            "order": order_name,
            "randomSeed": order_seed,
            "workspaceId": workspace_id,
            "config": vars(config),
            "summary": summary,
            "snapshot": snapshot,
            "items": logs,
        },
    )
    write_json(output / "items.jsonl-summary.json", logs)
    _write_csv(output / "items.csv", ITEM_COLUMNS, logs)
    _write_csv(
        output / "categories.csv",
        ["id", "name", "origin", "createdAtItemId", "itemCount"],
        snapshot["formalCategories"],
    )
    _write_csv(
        output / "candidates.csv",
        [
            "candidateId",
            "suggestedName",
            "description",
            "status",
            "supportCount",
            "createdAtItemId",
            "mergedIntoCandidateId",
            "promotedFormalCategoryId",
            "linkedItemIds",
        ],
        snapshot["candidates"],
    )
    (output / "report.md").write_text(
        build_order_report(summary, snapshot, markdown=True), encoding="utf-8"
    )
    (output / "report.txt").write_text(
        build_order_report(summary, snapshot, markdown=False), encoding="utf-8"
    )
    return summary


def _cell(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def build_order_report(summary: dict[str, Any], snapshot: dict[str, Any], *, markdown: bool) -> str:
    def heading(level: int, text: str) -> str:
        return f"{'#' * level} {text}" if markdown else text

    lines = [
        heading(1, f"증분 카테고리 실행: {summary['order']}"),
        "",
        heading(2, "요약"),
        f"- 최종 정식 카테고리 수: {summary['finalFormalCategoryCount']}",
        f"- AI 승격 카테고리 수: {summary['aiPromotedCategoryCount']}",
        f"- 생성된 임시 후보 수: {summary['createdCandidateCount']}",
        f"- 기존 후보 재사용 횟수: {summary['reusedCandidateEventCount']}",
        f"- 승격된 후보 수: {summary['promotedCandidateCount']}",
        f"- 승격 대기 후보 수: {summary['readyToPromoteCandidateCount']}",
        f"- 병합된 후보 수: {summary['mergedCandidateCount']}",
        f"- 1건만 연결된 후보 수: {summary['singleLinkCandidateCount']}",
        f"- 재분류된 데이터 수: {summary['reclassifiedItemCount']}",
        f"- 정식 카테고리 10개 초과 여부: {'예' if summary['exceededMaxFormalCategories'] else '아니오'}",
        "",
        heading(2, "정식 카테고리"),
    ]
    if markdown:
        lines.append("| ID | 이름 | 출처 | 최초 생성 데이터 | 데이터 수 |")
        lines.append("|---|---|---|---|--:|")
        for category in snapshot["formalCategories"]:
            lines.append(
                f"| {_cell(category['id'])} | {_cell(category['name'])} | {_cell(category['origin'])} "
                f"| {_cell(category['createdAtItemId'])} | {category['itemCount']} |"
            )
    else:
        for category in snapshot["formalCategories"]:
            lines.append(
                f"- [{_cell(category['origin'])}] {_cell(category['name'])} "
                f"(데이터 {category['itemCount']}건)"
            )
    lines.extend(["", heading(2, "임시 후보")])
    active = [c for c in snapshot["candidates"] if c["status"] != "MERGED"]
    if markdown:
        lines.append("| ID | 이름 | 상태 | 지지 수 | 최초 데이터 | 승격 카테고리 |")
        lines.append("|---|---|---|--:|---|---|")
        for candidate in snapshot["candidates"]:
            lines.append(
                f"| {candidate['candidateId']} | {_cell(candidate['suggestedName'])} "
                f"| {_cell(candidate['status'])} | {candidate['supportCount']} "
                f"| {_cell(candidate['createdAtItemId'])} | {_cell(candidate['promotedFormalCategoryId'])} |"
            )
    else:
        for candidate in active:
            lines.append(
                f"- {_cell(candidate['suggestedName'])} [{_cell(candidate['status'])}] "
                f"지지 {candidate['supportCount']}건"
            )
    return "\n".join(lines) + "\n"


COMPARISON_KEYS = [
    ("order", "순서"),
    ("finalFormalCategoryCount", "최종 정식 카테고리 수"),
    ("aiPromotedCategoryCount", "AI 승격 수"),
    ("createdCandidateCount", "생성 후보 수"),
    ("reusedCandidateEventCount", "후보 재사용 수"),
    ("promotedCandidateCount", "승격 후보 수"),
    ("readyToPromoteCandidateCount", "승격 대기 수"),
    ("mergedCandidateCount", "병합 후보 수"),
    ("singleLinkCandidateCount", "1건 후보 수"),
    ("reclassifiedItemCount", "재분류 데이터 수"),
    ("exceededMaxFormalCategories", "10개 초과"),
]


def write_comparison(output: Path, summaries: list[dict[str, Any]]) -> None:
    _write_csv(output / "comparison.csv", [key for key, _ in COMPARISON_KEYS], summaries)
    headers = [label for _, label in COMPARISON_KEYS]
    keys = [key for key, _ in COMPARISON_KEYS]
    lines = [
        "# 증분 카테고리 서비스 통합 비교",
        "",
        "데이터를 한 건씩 입력한 결과를 데이터 순서별로 비교합니다.",
        "",
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for summary in summaries:
        lines.append("| " + " | ".join(_cell(summary.get(key)) for key in keys) + " |")
    finals = ", ".join(
        f"{s['order']}={s['finalFormalCategoryCount']}" for s in summaries
    )
    created = ", ".join(f"{s['order']}={s['createdCandidateCount']}" for s in summaries)
    lines.extend(
        [
            "",
            "## 데이터 순서에 따른 차이",
            "",
            f"- 최종 정식 카테고리 수(순서별): {finals}",
            f"- 생성 임시 후보 수(순서별): {created}",
        ]
    )
    (output / "comparison-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def planned_output(mode: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = ROOT / "results" / f"{timestamp}-incremental-category-{mode}"
    candidate = base
    index = 1
    while candidate.exists():
        candidate = Path(f"{base}-{index}")
        index += 1
    return candidate


def main(argv: list[str] | None = None) -> int:
    options = parse_args(argv)
    try:
        orders = resolve_orderings(options.order)
        config = load_service_config(options.config)
        seeds = load_seed_categories()
        items = load_items(options)
        output = options.output.resolve() if options.output else planned_output(options.mode)

        print(f"[OK] 모드: {options.mode} | 데이터 {len(items)}건 | 순서: {', '.join(orders)}")
        print(
            f"[OK] 시드 카테고리 {len(seeds)}개: {', '.join(c['name'] for c in seeds)}"
        )
        print(
            f"[OK] 상한 정식 {config.max_count} / AI 승격 {config.max_ai_generated_count} / "
            f"후보 유사도 {config.candidate_similarity_threshold} / 최소 지지 {config.candidate_min_support_count}"
        )
        print(f"[OK] 결과 폴더: {output}")
        if options.dry_run:
            for order in orders:
                print(f"  - {order} ({len(items)}건 순차 입력)")
            print("[DRY-RUN] 실행하지 않았습니다.")
            return 0

        backend = build_backend(options)
        output.mkdir(parents=True, exist_ok=bool(options.output))
        summaries: list[dict[str, Any]] = []
        for order in orders:
            print(f"\n[ORDER] {order}")
            summaries.append(
                run_order(order, items, seeds, backend, config, options.workspace_id, output / order)
            )
        write_json(
            output / "run-summary.json",
            {
                "mode": options.mode,
                "datasetRoot": str(options.dataset_root.resolve()),
                "datasetCount": len(items),
                "orders": orders,
                "config": vars(config),
                "summaries": summaries,
            },
        )
        write_comparison(output, summaries)
        print(f"\n[OK] 완료: {output}")
        print(f"[비교] {output / 'comparison-report.md'}")
        return 0
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, ModelConfigError) as exc:
        print(f"[FAIL] {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
