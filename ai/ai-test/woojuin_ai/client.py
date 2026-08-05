from __future__ import annotations

import json
import math
import time
from typing import Any, Callable

import requests

from .config import Settings


RETRYABLE_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504, 529}


def _strip_code_fence(content: str) -> str:
    """json_object 폴백 시 모델이 ```json 펜스로 감싸는 경우를 걷어낸다."""
    stripped = content.strip()
    if not stripped.startswith("```"):
        return stripped
    first_newline = stripped.find("\n")
    fence_end = stripped.rfind("```")
    if first_newline < 0 or fence_end <= first_newline:
        return stripped
    return stripped[first_newline + 1 : fence_end].strip()


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
        # Structured Outputs(json_schema) 미지원 판정 캐시. qwen3-8b의 유일한 OpenRouter
        # 프로바이더(Alibaba)가 json_object까지만 지원해, require_parameters를 걸면
        # "No endpoints found" 404가 난다. 한 번 확인되면 이후 호출은 폴백으로 직행한다.
        self._structured_outputs_unsupported = False

    def chat_json(
        self,
        *,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
        schema_name: str,
    ) -> dict[str, Any]:
        if self._structured_outputs_unsupported:
            raw = self._post("/chat/completions", self._json_object_payload(messages, schema))
        else:
            payload = {
                "model": self.settings.chat_model,
                "messages": messages,
                "temperature": 0,
                "reasoning": {"effort": "none"},
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
            try:
                raw = self._post("/chat/completions", payload)
            except OpenRouterError as exc:
                # 프로바이더가 json_schema를 못 받는 경우에만 폴백한다. 스키마는 프롬프트에
                # 실어 보내고, 형식 검증은 어차피 호출부의 pydantic 파싱이 한 번 더 한다.
                if "No endpoints found" not in str(exc):
                    raise
                self._structured_outputs_unsupported = True
                raw = self._post("/chat/completions", self._json_object_payload(messages, schema))
        try:
            content = raw["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise TypeError("message.content가 문자열이 아닙니다")
            parsed = json.loads(_strip_code_fence(content))
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise OpenRouterError("OpenRouter의 JSON 응답 형식이 올바르지 않습니다") from exc
        # json_object 폴백에서 일부 프로바이더(Alibaba)가 객체를 단일 원소 배열로 감싸
        # 반환하는 경우가 있다(실측). 의미가 같으므로 벗겨서 수용한다.
        if isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], dict):
            parsed = parsed[0]
        if not isinstance(parsed, dict):
            raise OpenRouterError("OpenRouter의 JSON 응답은 객체여야 합니다")
        return parsed

    def _json_object_payload(
        self, messages: list[dict[str, str]], schema: dict[str, Any]
    ) -> dict[str, Any]:
        """프롬프트 지시 기반 JSON 폴백 페이로드.

        response_format을 아예 보내지 않는다 — Alibaba(qwen3-8b의 유일한 프로바이더)는
        json_object 모드에서 `"strconv"` 같은 깨진 출력을 내는 반면(실측, temperature 0에서도
        재현), 프롬프트에 스키마를 싣기만 하면 올바른 JSON을 반환했다. 형식 검증은 호출부의
        pydantic 파싱이 담당한다.
        """
        instruction = (
            "\n\n다음 JSON Schema를 정확히 따르는 유효한 JSON 객체 하나만 반환하세요. "
            "배열로 감싸지 말고 최상위가 객체({)여야 합니다. 마크다운·주석·설명문을 붙이지 마세요.\n"
            + json.dumps(schema, ensure_ascii=False)
        )
        last = messages[-1]
        return {
            "model": self.settings.chat_model,
            "messages": [*messages[:-1], {"role": last["role"], "content": last["content"] + instruction}],
            "temperature": 0,
            "reasoning": {"effort": "none"},
        }

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
