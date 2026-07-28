import json

import pytest

import run_category_description_comparison as runner


DEFINITIONS = [
    {"id": "A", "name": "가", "description": "기존 가", "examples": []},
    {"id": "B", "name": "나", "description": "기존 나", "examples": []},
]


def test_three_comparison_conditions_are_fixed():
    assert [condition.id for condition in runner.CONDITIONS] == [
        "ai-generated-description", "existing-description", "names-only",
    ]
    assert [condition.include_descriptions for condition in runner.CONDITIONS] == [True, True, False]


def test_generated_definitions_must_match_existing_ids_and_names():
    runner.validate_matching_definitions(DEFINITIONS, list(reversed(DEFINITIONS)))
    with pytest.raises(ValueError):
        runner.validate_matching_definitions(DEFINITIONS, [DEFINITIONS[0]])


def test_dry_run_does_not_connect_or_write(monkeypatch, tmp_path):
    generated = tmp_path / "generated.json"
    source = runner.ROOT / "config" / "categories.json"
    generated.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    output = tmp_path / "output"
    monkeypatch.setattr(runner, "OllamaClient", lambda *_: pytest.fail("Ollama를 호출하면 안 됩니다"))
    result = runner.main([
        "--generated-definitions", str(generated), "--output", str(output),
        "--limit", "2", "--dry-run",
    ])
    assert result == 0
    assert not output.exists()
