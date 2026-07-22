from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import main as app
from src.model_config import (
    ModelConfig,
    ModelConfigError,
    PricingConfig,
    calculate_cost,
    load_models,
    load_suites,
    safe_filename,
    select_models,
)
from src.providers import ModelRequest, ModelResponse, OpenAIProvider, sanitize_error
from src.settings import Settings, load_settings


def model(model_id: str = "openai-test", enabled: bool = True, modes: tuple[str, ...] = ("category-only",)) -> ModelConfig:
    return ModelConfig(model_id, "openai", "gpt-test", enabled, "test", ("text",), modes)


def request() -> ModelRequest:
    return ModelRequest("JSON으로 답하세요", {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"], "additionalProperties": False}, "category-only", "TEXT-001", 0)


class FakeResponses:
    def __init__(self, values):
        self.values = list(values)
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        value = self.values.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


class FakeClient:
    def __init__(self, values):
        self.responses = FakeResponses(values)


class FakeChatClient:
    def __init__(self, values):
        self.completions = FakeResponses(values)
        self.chat = SimpleNamespace(completions=self.completions)


def fake_response(text: str = '{"ok":true}'):
    return SimpleNamespace(
        output_text=text,
        model="gpt-test-2026-01-01",
        status="completed",
        _request_id="req_test",
        incomplete_details=None,
        usage=SimpleNamespace(
            input_tokens=10,
            output_tokens=4,
            total_tokens=14,
            input_tokens_details=SimpleNamespace(cached_tokens=2),
            output_tokens_details=SimpleNamespace(reasoning_tokens=1),
        ),
    )


def fake_chat_response(text: str = '{"ok":true}'):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text), finish_reason="stop")],
        model="gpt-test-2026-01-01",
        _request_id="req_chat_test",
        usage=SimpleNamespace(
            prompt_tokens=10,
            completion_tokens=4,
            total_tokens=14,
            prompt_tokens_details=SimpleNamespace(cached_tokens=2),
            completion_tokens_details=SimpleNamespace(reasoning_tokens=1),
        ),
    )


def sdk_error(name: str, message: str, status_code: int | None = None) -> Exception:
    error = type(name, (Exception,), {})(message)
    error.status_code = status_code
    return error


def write_yaml(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_env_loading_and_presence(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    (tmp_path / ".env").write_text("OPENAI_API_KEY=test-value\n", encoding="utf-8")
    settings = load_settings(tmp_path)
    assert settings.openai_api_key_configured
    assert settings.openai_api_key == "test-value"


def test_env_loading_searches_project_parents(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    tool_root = tmp_path / "ai" / "ai-text"
    tool_root.mkdir(parents=True)
    (tmp_path / ".env").write_text("OPENAI_API_KEY=root-value\n", encoding="utf-8")
    settings = load_settings(tool_root)
    assert settings.openai_api_key_configured
    assert settings.openai_api_key == "root-value"


def test_gms_key_uses_legacy_openai_key_as_fallback(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GMS_KEY", raising=False)
    (tmp_path / ".env").write_text("OPENAI_API_KEY=gms-compatible-value\n", encoding="utf-8")
    settings = load_settings(tmp_path)
    assert settings.gms_key == "gms-compatible-value"
    assert settings.key_configured("GMS_KEY")


def test_missing_key_is_skipped():
    response = OpenAIProvider(None).generate(request(), model())
    assert response.status == "SKIPPED"
    assert response.error_type == "MISSING_API_KEY"


def test_secret_masking():
    secret = "sk-secret123456789"
    masked = sanitize_error(
        f"Authorization: Bearer {secret}; OPENAI_API_KEY={secret}; GMS_KEY={secret}; Incorrect API key provided: prefix********suffix.",
        (secret,),
    )
    assert secret not in masked
    assert "[REDACTED]" in masked
    assert "prefix" not in masked and "suffix" not in masked


def test_models_and_suites_load():
    models = load_models(app.ROOT / "config" / "models.yaml")
    suites = load_suites(app.ROOT / "config" / "model-suites.yaml")
    assert models["openai-gpt-5-nano"].model == "gpt-5-nano"
    assert suites["text-comparison"][0] == "qwen-local"


@pytest.mark.parametrize(
    "body, message",
    [
        ("models:\n  - id: x\n", "필수 필드 누락"),
        ("models:\n  - &m {id: x, provider: openai, model: m, enabled: true, purpose: p, inputTypes: [text], testModes: [integrated]}\n  - *m\n", "중복 모델 ID"),
        ("models:\n  - {id: x, provider: unknown, model: m, enabled: true, purpose: p, inputTypes: [text], testModes: [integrated]}\n", "provider"),
    ],
)
def test_model_config_validation(tmp_path, body, message):
    with pytest.raises(ModelConfigError, match=message):
        load_models(write_yaml(tmp_path / "models.yaml", body))


def test_unknown_disabled_unsupported_and_duplicate_selections():
    models = {
        "disabled": model("disabled", False),
        "summary": model("summary", True, ("summary-only",)),
        "ready": model("ready"),
    }
    selected = select_models(models, ["missing", "disabled", "summary", "ready", "ready"], "category-only")
    assert [item.error_type for item in selected] == ["MODEL_NOT_FOUND", "MODEL_DISABLED", "UNSUPPORTED_TEST_MODE", None, "DUPLICATE_MODEL_ID"]


def test_openai_success_and_token_usage():
    client = FakeClient([fake_response()])
    response = OpenAIProvider("sk-test-value", client=client).generate(request(), model())
    assert response.status == "SUCCESS"
    assert response.resolved_model == "gpt-test-2026-01-01"
    assert (response.input_tokens, response.output_tokens, response.total_tokens) == (10, 4, 14)
    assert (response.cached_input_tokens, response.reasoning_tokens) == (2, 1)
    assert response.request_id == "req_test"
    assert client.responses.calls[0]["text"]["format"]["type"] == "json_schema"


def test_gms_chat_completions_success_and_schema():
    client = FakeChatClient([fake_chat_response()])
    response = OpenAIProvider(
        "gms-test-value", client=client,
        base_url="https://gms.ssafy.io/gmsapi/api.openai.com/v1",
        api_mode="chat_completions",
    ).generate(request(), model())
    assert response.status == "SUCCESS"
    assert (response.input_tokens, response.output_tokens, response.total_tokens) == (10, 4, 14)
    assert response.request_id == "req_chat_test"
    call = client.completions.calls[0]
    assert call["messages"][0]["role"] == "user"
    assert call["response_format"]["type"] == "json_schema"


@pytest.mark.parametrize(
    "error, expected",
    [
        (sdk_error("AuthenticationError", "bad key", 401), "AUTHENTICATION_ERROR"),
        (sdk_error("NotFoundError", "missing model", 404), "MODEL_NOT_FOUND"),
    ],
)
def test_non_retryable_openai_errors(error, expected):
    client = FakeClient([error])
    response = OpenAIProvider("sk-test-value", client=client, sleeper=lambda _: None).generate(request(), model())
    assert response.error_type == expected
    assert response.attempt_count == 1


@pytest.mark.parametrize("error", [sdk_error("RateLimitError", "slow", 429), sdk_error("APITimeoutError", "timeout")])
def test_retryable_openai_errors(error):
    client = FakeClient([error, fake_response()])
    sleeps: list[float] = []
    response = OpenAIProvider("sk-test-value", client=client, sleeper=sleeps.append).generate(request(), model())
    assert response.status == "SUCCESS"
    assert response.attempt_count == 2
    assert sleeps == [1.0]


def test_structured_output_fallback():
    client = FakeClient([sdk_error("BadRequestError", "json_schema unsupported", 400), fake_response()])
    response = OpenAIProvider("sk-test-value", client=client, sleeper=lambda _: None).generate(request(), model())
    assert response.status == "SUCCESS"
    assert response.structured_output_fallback_used
    assert not response.structured_output_applied
    assert "text" not in client.responses.calls[1]


def test_empty_response():
    response = OpenAIProvider("sk-test-value", client=FakeClient([fake_response("")])).generate(request(), model())
    assert response.error_type == "EMPTY_RESPONSE"


def test_missing_price_is_na_and_known_price_calculates():
    missing = PricingConfig("USD", "per_1m_tokens", None, {"m": {"inputPrice": None, "outputPrice": None}})
    known = PricingConfig("USD", "per_1m_tokens", None, {"m": {"inputPrice": 1.0, "outputPrice": 2.0}})
    assert calculate_cost(missing, "m", 100, 50) is None
    assert calculate_cost(known, "m", 1_000_000, 500_000) == 2.0


def test_safe_filename():
    assert safe_filename("openai/model:one?*") == "openai_model_one"
    assert safe_filename("...") == "model"


def test_dry_run_does_not_create_provider_or_result(monkeypatch, tmp_path, capsys):
    planned = tmp_path / "planned"
    monkeypatch.setattr(app, "planned_output", lambda modes, selector: planned)
    monkeypatch.setattr(app, "make_providers", lambda *args: pytest.fail("provider must not be created"))
    result = app.main(["--category-only", "--suite", "text-comparison", "--limit", "1", "--dry-run"])
    output = capsys.readouterr().out
    assert result == 0
    assert "전체 예상 요청 수: 3" in output
    assert "GMS_KEY:" in output
    assert not planned.exists()


def test_multi_mode_report_uses_saved_mode_directories(monkeypatch, tmp_path):
    modes = ["category-only", "summary-only"]
    for mode_name in modes:
        (tmp_path / mode_name).mkdir()
    captured = {}

    def fake_compare(paths, results_root, output_dir):
        captured["paths"] = paths
        captured["results_root"] = results_root
        captured["output_dir"] = output_dir
        return output_dir

    monkeypatch.setattr(app, "compare_result_directories", fake_compare)
    result = app.generate_multi_mode_report(tmp_path, modes)
    assert result == tmp_path
    assert captured["paths"] == [tmp_path / mode for mode in modes]
    assert captured["output_dir"] == tmp_path


def test_model_failure_does_not_stop_next_model(monkeypatch, tmp_path):
    class Provider:
        def generate(self, _request, config):
            if config.id == "bad":
                return ModelResponse("openai", config.id, config.model, status="FAILED", error_type="RATE_LIMIT_ERROR", error_message="limited")
            return ModelResponse("openai", config.id, config.model, raw_text='{"category":"학습·지식","confidence":0.9}', status="SUCCESS", structured_output_applied=True)

    monkeypatch.setattr(app, "make_providers", lambda *_: {"openai": Provider()})
    selections = [app.ModelSelection("bad", model("bad")), app.ModelSelection("good", model("good"))]
    data = [{"testId": "TEXT-001", "datasetType": "memo", "input": "JWT 구현", "expected": {"categories": ["학습·지식"], "requiredKeywords": [], "summaryPoints": [], "forbiddenClaims": []}}]
    pricing = PricingConfig("USD", "per_1m_tokens", None, {})
    config = app.load_project_config()
    definitions = [{"name": "학습·지식", "description": "기술과 지식 관련 메모", "examples": []}]
    app.run_mode("category-only", tmp_path, selections, data, ["학습·지식"], definitions, "memo", config, pricing, Settings(gms_key="gms-test"), 1)
    good = json.loads((tmp_path / "model-results" / "good.json").read_text(encoding="utf-8"))
    assert good["status"] == "COMPLETED"
    assert good["requests"][0]["response"]["status"] == "SUCCESS"


def test_api_key_is_not_written_to_results(monkeypatch, tmp_path):
    secret = "sk-super-secret-value"

    class Provider:
        def generate(self, _request, config):
            return ModelResponse("openai", config.id, config.model, status="FAILED", error_type="AUTHENTICATION_ERROR", error_message=f"Bearer {secret}")

    monkeypatch.setattr(app, "make_providers", lambda *_: {"openai": Provider()})
    selections = [app.ModelSelection("bad", model("bad"))]
    data = [{"testId": "TEXT-001", "datasetType": "memo", "input": "JWT 구현", "expected": {"categories": ["학습·지식"], "requiredKeywords": [], "summaryPoints": [], "forbiddenClaims": []}}]
    definitions = [{"name": "학습·지식", "description": "기술과 지식 관련 메모", "examples": []}]
    app.run_mode("category-only", tmp_path, selections, data, ["학습·지식"], definitions, "memo", app.load_project_config(), PricingConfig("USD", "per_1m_tokens", None, {}), Settings(gms_key=secret), 1)
    assert secret not in "\n".join(path.read_text(encoding="utf-8-sig") for path in tmp_path.rglob("*") if path.is_file())


@pytest.mark.integration
@pytest.mark.requires_openai_api_key
def test_openai_live_call_requires_explicit_opt_in(monkeypatch):
    import os
    if os.getenv("RUN_OPENAI_INTEGRATION") != "1" or not load_settings(app.ROOT).gms_key:
        pytest.skip("RUN_OPENAI_INTEGRATION=1 및 GMS_KEY가 필요합니다")
    assert app.main(["--category-only", "--model", "openai-gpt-5-nano", "--limit", "1"]) == 0
