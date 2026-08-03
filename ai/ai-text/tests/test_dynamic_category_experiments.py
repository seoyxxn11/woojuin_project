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
    SCENARIOS,
    CategoryCatalog,
    build_dynamic_prompt,
    parse_dynamic_response,
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
