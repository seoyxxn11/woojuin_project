import pytest

import generate_category_descriptions as runner
import run_classification_experiment as classification_runner
from src.category_description_generator import (
    build_description_prompt,
    select_category_samples,
    validate_generated_description,
)


ITEMS = [
    {"testId": "TEXT-001", "title": "JWT", "input": "토큰 재발급 구조", "expected": {"categories": ["학습·지식"]}},
    {"testId": "TEXT-002", "title": "Docker", "input": "컨테이너 실행 방법", "expected": {"categories": ["학습·지식"]}},
    {"testId": "TEXT-003", "title": "장보기", "input": "우유 구매", "expected": {"categories": ["생활·할 일"]}},
]


def test_selects_only_target_category_and_limits_content():
    samples = select_category_samples(ITEMS, "학습·지식", max_items=1, max_chars_per_item=4)
    assert samples == [{"testId": "TEXT-001", "title": "JWT", "input": "토큰 재"}]


def test_build_prompt_contains_category_context_and_samples():
    prompt = build_description_prompt(
        "{{CATEGORY_NAME}}\n{{ALL_CATEGORY_NAMES}}\n{{CATEGORY_SAMPLES}}",
        "학습·지식", ["학습·지식", "생활·할 일"],
        select_category_samples(ITEMS, "학습·지식", max_items=2, max_chars_per_item=100),
    )
    assert "학습·지식" in prompt and "생활·할 일" in prompt
    assert "TEXT-001" in prompt and "TEXT-002" in prompt


def test_generated_description_is_normalized():
    result = validate_generated_description({
        "description": " 기술 지식 ",
        "examples": [" JWT ", "Docker", "Spring"],
    })
    assert result == {"description": "기술 지식", "examples": ["JWT", "Docker", "Spring"]}


@pytest.mark.parametrize("value", [
    {},
    {"description": "설명", "examples": ["하나"]},
    {"description": "설명", "examples": ["같음", "같음", "다름"]},
])
def test_invalid_generated_description_is_rejected(value):
    with pytest.raises(ValueError):
        validate_generated_description(value)


def test_dry_run_does_not_create_output_or_connect_to_ollama(monkeypatch, tmp_path):
    output = tmp_path / "generated.json"
    monkeypatch.setattr(runner, "OllamaClient", lambda *_: pytest.fail("Ollama를 호출하면 안 됩니다"))
    assert runner.main(["--dry-run", "--output", str(output)]) == 0
    assert not output.exists()


def test_classification_experiment_accepts_generated_definition_path(tmp_path):
    output = tmp_path / "definitions.json"
    options = classification_runner.parse_args(["--category-definitions", str(output), "--dry-run"])
    assert options.category_definitions == str(output)
