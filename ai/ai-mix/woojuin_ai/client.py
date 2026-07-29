from __future__ import annotations

import json
import math
import time
from typing import Any, Callable

import requests

from .config import Settings


RETRYABLE_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504, 529}


class ConfigurationError(RuntimeError):
    """서비스 설정이 누락된 경우."""


class OpenRouterError(RuntimeError):
    """OpenRouter 호출 또는 응답 검증에 실패한 경우."""


class OpenRouterClient:
    def __init__(
        self,
        settings: Settings,
        *,
        session: requests.Session | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.settings = settings
        self.session = session or requests.Session()
        self.sleeper = sleeper

    def chat_json(
        self,
        *,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
        schema_name: str,
    ) -> dict[str, Any]:
        payload = {
            "model": self.settings.chat_model,
            "messages": messages,
            "temperature": 0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                },
            },
            "provider": {"require_parameters": True},
        }
        raw = self._post("/chat/completions", payload)
        try:
            content = raw["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise TypeError("message.content가 문자열이 아닙니다")
            parsed = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise OpenRouterError("OpenRouter의 JSON 응답 형식이 올바르지 않습니다") from exc
        if not isinstance(parsed, dict):
            raise OpenRouterError("OpenRouter의 JSON 응답은 객체여야 합니다")
        return parsed

    def create_embeddings(self, texts: list[str]) -> tuple[str, list[list[float]]]:
        if not texts:
            raise ValueError("임베딩 입력은 한 개 이상이어야 합니다")
        raw = self._post(
            "/embeddings",
            {
                "model": self.settings.embedding_model,
                "input": texts,
                "encoding_format": "float",
            },
        )
        try:
            data = raw["data"]
            if not isinstance(data, list):
                raise TypeError("data가 배열이 아닙니다")
            ordered = sorted(data, key=lambda item: int(item["index"]))
            if len(ordered) != len(texts):
                raise ValueError("요청과 응답의 임베딩 개수가 다릅니다")
            vectors: list[list[float]] = []
            dimensions: int | None = None
            for expected_index, item in enumerate(ordered):
                if int(item["index"]) != expected_index:
                    raise ValueError("임베딩 응답 index가 연속적이지 않습니다")
                vector = [float(number) for number in item["embedding"]]
                if not vector or any(not math.isfinite(number) for number in vector):
                    raise ValueError("임베딩 벡터가 비었거나 유한하지 않습니다")
                if dimensions is None:
                    dimensions = len(vector)
                elif dimensions != len(vector):
                    raise ValueError("임베딩 벡터 차원이 서로 다릅니다")
                vectors.append(vector)
            model = str(raw.get("model") or self.settings.embedding_model)
            return model, vectors
        except (KeyError, TypeError, ValueError) as exc:
            raise OpenRouterError("OpenRouter의 임베딩 응답 형식이 올바르지 않습니다") from exc

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.api_key:
            raise ConfigurationError("OPENROUTER_API_KEY가 설정되어 있지 않습니다")

        last_error: Exception | None = None
        attempts = self.settings.max_retries + 1
        for attempt in range(attempts):
            try:
                response = self.session.post(
                    self.settings.base_url + path,
                    headers=self._headers(),
                    json=payload,
                    timeout=self.settings.timeout_seconds,
                )
                if response.status_code >= 400:
                    message = self._error_message(response)
                    error = OpenRouterError(
                        f"OpenRouter 요청 실패({response.status_code}): {message}"
                    )
                    if (
                        response.status_code in RETRYABLE_STATUS_CODES
                        and attempt + 1 < attempts
                    ):
                        last_error = error
                        self.sleeper(min(2**attempt, 8))
                        continue
                    raise error
                body = response.json()
                if not isinstance(body, dict):
                    raise OpenRouterError("OpenRouter 응답은 JSON 객체여야 합니다")
                return body
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_error = exc
                if attempt + 1 >= attempts:
                    break
                self.sleeper(min(2**attempt, 8))
            except requests.RequestException as exc:
                raise OpenRouterError("OpenRouter HTTP 요청에 실패했습니다") from exc
            except ValueError as exc:
                raise OpenRouterError("OpenRouter 응답 JSON을 읽지 못했습니다") from exc
        raise OpenRouterError(
            f"OpenRouter 연결에 실패했습니다({type(last_error).__name__})"
        ) from last_error

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
            "X-OpenRouter-Title": self.settings.app_title,
        }
        if self.settings.http_referer:
            headers["HTTP-Referer"] = self.settings.http_referer
        return headers

    @staticmethod
    def _error_message(response: requests.Response) -> str:
        try:
            body = response.json()
            if isinstance(body, dict):
                error = body.get("error")
                if isinstance(error, dict) and error.get("message"):
                    return str(error["message"])[:500]
                if isinstance(error, str):
                    return error[:500]
        except ValueError:
            pass
        return "상세 오류 없음"
