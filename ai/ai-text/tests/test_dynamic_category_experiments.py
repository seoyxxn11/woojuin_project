import json
import os
import sys
import types

import pytest

try:
    import dotenv  # noqa: F401
except ModuleNotFoundError:  # 로컬 최소 테스트 환경용
    dotenv_stub = types.ModuleType("dotenv")

    def load_dotenv(dotenv_path=None, override=False, **_kwargs):
        if dotenv_path is None:
            return False
        loaded = False
        for line in open(dotenv_path, encoding="utf-8"):
            key, separator, value = line.strip().partition("=")
            if separator and key and (override or key not in os.environ):
                os.environ[key] = value.strip().strip('"').strip("'")
                loaded = True
        return loaded

    dotenv_stub.load_dotenv = load_dotenv
    sys.modules["dotenv"] = dotenv_stub

import run_dynamic_category_experiments as runner
from src.dynamic_category_experiment import (
    GENERATED_EXISTING,
    NEW_GENERATED,
    SCENARIOS,
    SEED_EXISTING,
    CategoryCatalog,
    apply_ordering,
    build_dynamic_prompt,
    category_key,
    find_duplicate_candidates,
    normalize_category_name,
    parse_dynamic_response,
    resolve_orderings,
    resolve_scenarios,
    seed_definitions,
)
from src.model_config import ModelConfig, PricingConfig
from src.providers import ModelResponse
from src.settings import Settings


DEFINITIONS = [
    {"id": "LIFE", "name": "생활", "description": "생활 기록", "examples": []},
    {"id": "STUDY", "name": "학습", "description": "학습 기록", "examples": []},
    {"id": "CAREER", "name": "취업", "description": "취업 기록", "examples": []},
]


def test_scenario_aliases_and_groups_are_resolved_in_order():
    assert [item.id for item in resolve_scenarios(["0", "2", "6"])] == [
        "baseline11",
        "ai-only",
        "cumulative",
    ]
    assert [item.id for item in resolve_scenarios(["reduced-ai"])] == [
        "existing3-ai",
        "existing5-ai",
        "existing7-ai",
    ]
    assert [item.id for item in resolve_scenarios(["all"])] == list(SCENARIOS)


def test_seed_definitions_use_current_dataset_order_without_dropping_other():
    values = [*DEFINITIONS, {"id": "OTHER", "name": "기타", "description": "기타", "examples": []}]
    assert [item["name"] for item in seed_definitions(values, 4)] == [
        "생활",
        "학습",
        "취업",
        "기타",
    ]
    with pytest.raises(ValueError, match="사용 가능한 카테고리"):
        seed_definitions(values, 5)


def test_dynamic_prompt_contains_catalog_and_content():
    template = "{{AVAILABLE_CATEGORIES}}\n{{TITLE_CONTEXT}}{{CONTENT}}"
    prompt = build_dynamic_prompt(template, "JWT 구현", "인증", DEFINITIONS[:2])
    assert "생활 [기존]" in prompt
    assert "입력 제목:\n인증" in prompt
    assert prompt.endswith("JWT 구현")


def test_parse_existing_and_generated_categories():
    existing = parse_dynamic_response(
        json.dumps(
            {
                "categoryName": "학습",
                "categoryDescription": "학습 기록",
                "categoryOrigin": "EXISTING",
                "reason": "기술 학습",
            },
            ensure_ascii=False,
        ),
        DEFINITIONS,
    )
    assert existing["schemaValid"] is True
    assert existing["parsedResponse"]["categoryOrigin"] == "EXISTING"

    generated = parse_dynamic_response(
        json.dumps(
            {
                "categoryName": "반려동물",
                "categoryDescription": "반려동물 관리 정보",
                "categoryOrigin": "GENERATED",
                "reason": "기존 분류에 없음",
            },
            ensure_ascii=False,
        ),
        DEFINITIONS,
    )
    assert generated["schemaValid"] is True
    assert generated["parsedResponse"]["categoryOrigin"] == "GENERATED"


def test_generated_synonym_with_same_name_is_deduplicated_to_existing():
    result = parse_dynamic_response(
        json.dumps(
            {
                "categoryName": "학습",
                "categoryDescription": "새 설명",
                "categoryOrigin": "GENERATED",
                "reason": "새로 생성",
            },
            ensure_ascii=False,
        ),
        DEFINITIONS,
    )
    assert result["schemaValid"] is True
    assert result["deduplicatedToExisting"] is True
    assert result["parsedResponse"]["categoryOrigin"] == "EXISTING"
    assert result["parsedResponse"]["categoryDescription"] == "학습 기록"


def test_category_catalog_reuses_generated_category():
    catalog = CategoryCatalog(DEFINITIONS[:1])
    first, created_first = catalog.add_generated("개발", "개발 자료")
    second, created_second = catalog.add_generated("개발", "다른 설명")
    assert created_first is True
    assert created_second is False
    assert first["id"] == second["id"]
    assert len(catalog.definitions) == 2


def test_cumulative_scenario_exposes_generated_category_to_next_request(tmp_path):
    class Provider:
        def __init__(self):
            self.prompts = []

        def generate(self, request, config):
            self.prompts.append(request.prompt)
            origin = "GENERATED" if len(self.prompts) == 1 else "EXISTING"
            return ModelResponse(
                "openrouter",
                config.id,
                config.model,
                raw_text=json.dumps(
                    {
                        "categoryName": "개발",
                        "categoryDescription": "개발 참고 자료",
                        "categoryOrigin": origin,
                        "reason": "개발 내용",
                    },
                    ensure_ascii=False,
                ),
                status="SUCCESS",
            )

    provider = Provider()
    config = ModelConfig(
        "test-model", "openrouter", "test/model", True, "test", ("text",), ("category-only",)
    )
    data = [
        {
            "testId": f"MEMO-{index:03d}",
            "inputType": "memo",
            "input": f"개발 메모 {index}",
            "title": f"메모 {index}",
            "sourcePath": f"학습/{index:04d}-url.txt",
        }
        for index in (1, 2)
    ]
    metadata = runner.execute_scenario(
        SCENARIOS["cumulative"],
        tmp_path / "cumulative",
        data,
        DEFINITIONS,
        config,
        provider,
        {"temperature": 0},
        PricingConfig("USD", "per_1m_tokens", None, {}),
        4,
    )
    assert "개발 [AI 생성]" not in provider.prompts[0]
    assert "개발 [AI 생성]" in provider.prompts[1]
    assert metadata["concurrencyApplied"] == 1
    assert metadata["finalCategories"] == ["개발"]
    draft = json.loads(
        (tmp_path / "cumulative" / "review-draft.json").read_text(encoding="utf-8")
    )
    assert [item["generatedCategory"] for item in draft["items"]] == ["개발", "개발"]


def test_baseline_delegates_to_original_category_only_runner(monkeypatch, tmp_path):
    captured = {}

    def fake_run_mode(*args):
        captured["args"] = args
        output = args[1]
        output.mkdir(parents=True)
        (output / "run-metadata.json").write_text(
            json.dumps({"status": "COMPLETED"}), encoding="utf-8"
        )

    monkeypatch.setattr(runner.base_runner, "run_mode", fake_run_mode)
    config = ModelConfig(
        "test-model", "openrouter", "test/model", True, "test", ("text",), ("category-only",)
    )
    result = runner.execute_baseline(
        SCENARIOS["baseline11"],
        tmp_path / "baseline11",
        [],
        DEFINITIONS,
        config,
        {},
        PricingConfig("USD", "per_1m_tokens", None, {}),
        Settings(),
        4,
    )
    assert captured["args"][0] == "category-only"
    assert result["scenario"] == "baseline11"
    saved = json.loads(
        (tmp_path / "baseline11" / "run-metadata.json").read_text(encoding="utf-8")
    )
    assert saved["baselineImplementation"] == "main.py run_mode(category-only)"


# ---- 누적/정규화/순서/재개 관련 신규 테스트 ----


def test_normalize_and_key_treat_spacing_and_separators_as_same():
    assert normalize_category_name(" 수면  건강 ") == "수면 건강"
    assert normalize_category_name("사업 · 창업") == "사업·창업"
    assert category_key("수면  건강") == category_key(" 수면 건강 ")
    assert category_key("ETF 투자") == category_key("etf 투자")


def test_catalog_dedupes_by_normalized_name():
    catalog = CategoryCatalog([])
    first, created_first = catalog.add_generated("수면 건강", "잠 관리", "URL-001")
    second, created_second = catalog.add_generated(" 수면  건강 ", "다른 설명", "URL-009")
    assert created_first is True
    assert created_second is False
    assert first["id"] == second["id"]
    assert first["origin"] == "GENERATED"
    assert first["createdAtItemId"] == "URL-001"
    assert len(catalog.definitions) == 1


def test_apply_ordering_is_deterministic_and_reproducible():
    data = [{"testId": f"URL-{index:03d}"} for index in range(10)]
    original, seed = apply_ordering(data, "original")
    assert seed is None
    assert [item["testId"] for item in original] == [item["testId"] for item in data]
    first, first_seed = apply_ordering(data, "shuffle-42")
    second, _ = apply_ordering(data, "shuffle-42")
    assert first_seed == 42
    assert [item["testId"] for item in first] == [item["testId"] for item in second]
    assert [item["testId"] for item in first] != [item["testId"] for item in data]
    assert resolve_orderings([]) == ["original"]
    assert resolve_orderings(["all"]) == ["original", "shuffle-42", "shuffle-84"]


def test_find_duplicate_candidates_flags_reordered_names():
    categories = [
        {"id": "S", "name": "생활·건강", "origin": "SEED"},
        {"id": "A", "name": "사업·창업", "origin": "GENERATED"},
        {"id": "B", "name": "창업·사업", "origin": "GENERATED"},
        {"id": "C", "name": "수면 건강", "origin": "GENERATED"},
    ]
    candidates = find_duplicate_candidates(categories)
    pairs = {tuple(sorted(item["categories"])) for item in candidates}
    assert ("사업·창업", "창업·사업") in pairs
    # 시드 카테고리는 검토 후보 대상이 아니다.
    assert all("생활·건강" not in item["categories"] for item in candidates)


def _scripted_provider(responses):
    calls = {"count": 0}

    class Provider:
        def generate(self, request, config):
            calls["count"] += 1
            payload = responses[request.test_id]
            return ModelResponse(
                "openrouter",
                config.id,
                config.model,
                raw_text=json.dumps(payload, ensure_ascii=False),
                status="SUCCESS",
            )

    return Provider(), calls


def _memo_items(ids):
    return [
        {
            "testId": test_id,
            "inputType": "memo",
            "input": f"{test_id} 본문",
            "title": f"{test_id} 제목",
            "sourcePath": f"메모/{test_id}.txt",
        }
        for test_id in ids
    ]


CUMULATIVE_RESPONSES = {
    "MEMO-001": {
        "categoryName": "수면 건강",
        "categoryDescription": "잠과 휴식 관리",
        "categoryOrigin": "GENERATED",
        "reason": "기존에 없음",
    },
    "MEMO-002": {
        "categoryName": "수면 건강",
        "categoryDescription": "다시 잠 이야기",
        "categoryOrigin": "GENERATED",
        "reason": "앞에서 만든 것과 같음",
    },
    "MEMO-003": {
        "categoryName": "생활·건강",
        "categoryDescription": "생활 관리",
        "categoryOrigin": "EXISTING",
        "reason": "시드 카테고리와 맞음",
    },
}

SEED_SOURCE = [
    {"id": f"C{index}", "name": f"소스{index}", "description": "x", "examples": []}
    for index in range(6)
]


def _run(scenario_id, output, data, provider, **kwargs):
    config = ModelConfig(
        "test-model", "openrouter", "test/model", True, "test", ("text",), ("category-only",)
    )
    return runner.execute_scenario(
        SCENARIOS[scenario_id],
        output,
        data,
        SEED_SOURCE,
        config,
        provider,
        {"temperature": 0},
        PricingConfig("USD", "per_1m_tokens", None, {}),
        4,
        **kwargs,
    )


def test_existing5_cumulative_reuses_generated_and_records_selection_types(tmp_path):
    provider, calls = _scripted_provider(CUMULATIVE_RESPONSES)
    data = _memo_items(["MEMO-001", "MEMO-002", "MEMO-003"])
    metadata = _run("existing5-ai-cumulative", tmp_path / "run", data, provider)

    assert metadata["initialCategoryCount"] == 5
    assert metadata["finalCategoryCount"] == 6  # 시드 5 + 생성 1
    assert metadata["newGeneratedCount"] == 1
    assert metadata["generatedExistingCount"] == 1
    assert metadata["seedExistingCount"] == 1
    assert calls["count"] == 3

    result = json.loads((tmp_path / "run" / "result.json").read_text(encoding="utf-8"))
    by_id = {item["itemId"]: item for item in result["items"]}
    assert by_id["MEMO-001"]["selectionType"] == NEW_GENERATED
    assert by_id["MEMO-001"]["isNewCategory"] is True
    assert by_id["MEMO-002"]["selectionType"] == GENERATED_EXISTING
    assert by_id["MEMO-002"]["isNewCategory"] is False
    assert by_id["MEMO-002"]["selectedCategoryName"] == "수면 건강"
    assert by_id["MEMO-003"]["selectionType"] == SEED_EXISTING

    generated = next(c for c in result["categories"] if c["name"] == "수면 건강")
    assert generated["origin"] == "GENERATED"
    assert generated["createdAtItemId"] == "MEMO-001"
    assert generated["selectedItemCount"] == 2

    assert (tmp_path / "run" / "items.csv").exists()
    assert (tmp_path / "run" / "categories.csv").exists()
    assert (tmp_path / "run" / "report.md").exists()
    assert (tmp_path / "run" / "report.txt").exists()


def test_resume_restores_catalog_and_skips_completed(tmp_path):
    output = tmp_path / "run"
    first_provider, first_calls = _scripted_provider(CUMULATIVE_RESPONSES)
    _run("existing5-ai-cumulative", output, _memo_items(["MEMO-001", "MEMO-002"]), first_provider)
    assert first_calls["count"] == 2

    resume_provider, resume_calls = _scripted_provider(CUMULATIVE_RESPONSES)
    metadata = _run(
        "existing5-ai-cumulative",
        output,
        _memo_items(["MEMO-001", "MEMO-002", "MEMO-003"]),
        resume_provider,
        resume=True,
    )
    # 완료된 두 건은 다시 호출하지 않는다.
    assert resume_calls["count"] == 1
    assert metadata["successCount"] == 3
    assert "수면 건강" in metadata["finalCategories"]

    result = json.loads((output / "result.json").read_text(encoding="utf-8"))
    by_id = {item["itemId"]: item for item in result["items"]}
    assert by_id["MEMO-002"]["selectionType"] == GENERATED_EXISTING
    assert by_id["MEMO-003"]["selectionType"] == SEED_EXISTING


def test_accumulate_override_forces_non_cumulative_scenario(tmp_path):
    provider, _calls = _scripted_provider(CUMULATIVE_RESPONSES)
    data = _memo_items(["MEMO-001", "MEMO-002"])
    # existing5-ai는 기본 비누적이지만 override로 누적을 강제한다.
    metadata = _run("existing5-ai", tmp_path / "run", data, provider, accumulate=True)
    assert metadata["accumulateGeneratedCategories"] is True
    result = json.loads((tmp_path / "run" / "result.json").read_text(encoding="utf-8"))
    by_id = {item["itemId"]: item for item in result["items"]}
    # 누적이므로 두 번째 데이터는 첫 번째 생성 카테고리를 재사용한다.
    assert by_id["MEMO-002"]["selectionType"] == GENERATED_EXISTING
