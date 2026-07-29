import json

import pytest

from woojuin_ai.client import ConfigurationError, OpenRouterClient, OpenRouterError
from woojuin_ai.config import Settings


class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self.body = body

    def json(self):
        return self.body


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def settings(**overrides):
    values = {"api_key": "or-test", "max_retries": 0}
    values.update(overrides)
    return Settings(**values)


def test_chat_uses_structured_output_and_required_parameters():
    session = FakeSession(
        [
            FakeResponse(
                200,
                {"choices": [{"message": {"content": '{"title":"t","summary":"s"}'}}]},
            )
        ]
    )
    client = OpenRouterClient(settings(), session=session)
    result = client.chat_json(
        messages=[{"role": "user", "content": "test"}],
        schema={"type": "object"},
        schema_name="result",
    )
    assert result == {"title": "t", "summary": "s"}
    payload = session.calls[0][1]["json"]
    assert payload["response_format"]["type"] == "json_schema"
    assert payload["provider"]["require_parameters"] is True
    assert session.calls[0][1]["headers"]["Authorization"] == "Bearer or-test"


def test_embeddings_are_sorted_by_index():
    session = FakeSession(
        [
            FakeResponse(
                200,
                {
                    "model": "embedding-model",
                    "data": [
                        {"index": 1, "embedding": [3, 4]},
                        {"index": 0, "embedding": [1, 2]},
                    ],
                },
            )
        ]
    )
    model, vectors = OpenRouterClient(settings(), session=session).create_embeddings(
        ["a", "b"]
    )
    assert model == "embedding-model"
    assert vectors == [[1.0, 2.0], [3.0, 4.0]]


def test_missing_api_key_fails_without_http_call():
    session = FakeSession([])
    client = OpenRouterClient(settings(api_key=None), session=session)
    with pytest.raises(ConfigurationError, match="OPENROUTER_API_KEY"):
        client.create_embeddings(["a"])
    assert session.calls == []


def test_api_error_does_not_expose_key():
    session = FakeSession(
        [FakeResponse(401, {"error": {"message": "invalid key"}})]
    )
    client = OpenRouterClient(settings(api_key="top-secret"), session=session)
    with pytest.raises(OpenRouterError) as raised:
        client.create_embeddings(["a"])
    assert "top-secret" not in str(raised.value)
