from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass
from typing import Any, Callable, Protocol

from .model_config import ModelConfig
from .ollama_client import OllamaClient, OllamaError, performance


@dataclass(frozen=True)
class ModelRequest:
    prompt: str
    schema: dict[str, Any]
    test_mode: str
    test_id: str
    temperature: float | None = None


@dataclass
class ModelResponse:
    provider: str
    model_id: str
    requested_model: str
    resolved_model: str | None = None
    raw_text: str = ""
    parsed_output: dict[str, Any] | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cached_input_tokens: int | None = None
    reasoning_tokens: int | None = None
    latency_ms: float = 0.0
    attempt_count: int = 0
    finish_reason: str | None = None
    request_id: str | None = None
    status: str = "SUCCESS"
    error_type: str | None = None
    error_message: str | None = None
    structured_output_requested: bool = True
    structured_output_applied: bool = False
    structured_output_fallback_used: bool = False
    structured_output_fallback_reason: str | None = None
    provider_metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        values = asdict(self)
        return {_camel_case(key): value for key, value in values.items()}


class ModelProvider(Protocol):
    def generate(self, request: ModelRequest, model_config: ModelConfig) -> ModelResponse:
        ...


def _camel_case(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+"),
    re.compile(r"(?i)(bearer\s+)[^\s,;]+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"(?i)(OPENAI_API_KEY\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"(?i)(GMS_KEY\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"(?i)(incorrect api key provided:\s*)[^\s,'\"}]+"),
)


def sanitize_error(value: object, secrets: tuple[str, ...] = ()) -> str:
    text = str(value)
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[REDACTED]")
    text = SECRET_PATTERNS[0].sub(r"\1[REDACTED]", text)
    text = SECRET_PATTERNS[1].sub(r"\1[REDACTED]", text)
    text = SECRET_PATTERNS[2].sub("[REDACTED]", text)
    text = SECRET_PATTERNS[3].sub(r"\1[REDACTED]", text)
    text = SECRET_PATTERNS[4].sub(r"\1[REDACTED]", text)
    text = SECRET_PATTERNS[5].sub(r"\1[REDACTED]", text)
    return text[:1000]


class OllamaProvider:
    def __init__(
        self,
        client: OllamaClient,
        keep_alive: str,
        seed: int | None,
        context_length: int | None,
        thinking: bool | None,
    ):
        self.client = client
        self.keep_alive = keep_alive
        self.seed = seed
        self.context_length = context_length
        self.thinking = thinking

    def available_models(self) -> list[str]:
        return self.client.models()

    def generate(self, request: ModelRequest, model_config: ModelConfig) -> ModelResponse:
        started = time.perf_counter()
        try:
            _, raw = self.client.chat(
                model_config.model,
                request.prompt,
                request.temperature or 0,
                self.keep_alive,
                request.schema,
                self.seed,
                self.context_length,
                self.thinking,
            )
            metrics = performance(raw)
            text = str(raw.get("message", {}).get("content", ""))
            if not text.strip():
                return ModelResponse(
                    provider="ollama", model_id=model_config.id, requested_model=model_config.model,
                    resolved_model=raw.get("model"), latency_ms=(time.perf_counter() - started) * 1000,
                    attempt_count=1, status="FAILED", error_type="EMPTY_RESPONSE", error_message="모델 응답이 비어 있습니다",
                    structured_output_applied=True,
                )
            return ModelResponse(
                provider="ollama", model_id=model_config.id, requested_model=model_config.model,
                resolved_model=raw.get("model") or model_config.model, raw_text=text,
                input_tokens=_integer_or_none(raw.get("prompt_eval_count")),
                output_tokens=_integer_or_none(raw.get("eval_count")),
                total_tokens=_sum_optional(raw.get("prompt_eval_count"), raw.get("eval_count")),
                latency_ms=metrics.get("totalDurationMs") or (time.perf_counter() - started) * 1000,
                attempt_count=1, finish_reason=raw.get("done_reason"), status="SUCCESS",
                structured_output_applied=True,
                provider_metadata={
                    "loadDurationMs": metrics.get("loadDurationMs"),
                    "generationDurationMs": metrics.get("evalDurationMs"),
                    "tokensPerSecond": metrics.get("tokensPerSecond"),
                    "temperatureRequested": request.temperature,
                    "temperatureApplied": request.temperature,
                    "streaming": False,
                    "toolsEnabled": False,
                },
            )
        except OllamaError as exc:
            return ModelResponse(
                provider="ollama", model_id=model_config.id, requested_model=model_config.model,
                latency_ms=(time.perf_counter() - started) * 1000, attempt_count=1,
                status="FAILED", error_type=_map_ollama_error(exc.error_type), error_message=sanitize_error(exc),
                structured_output_applied=True,
            )


class OpenAIProvider:
    def __init__(
        self,
        api_key: str | None,
        client: Any | None = None,
        base_url: str | None = None,
        api_mode: str = "responses",
        max_retries: int = 2,
        backoff_seconds: float = 1.0,
        sleeper: Callable[[float], None] = time.sleep,
    ):
        self.api_key = api_key
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.sleeper = sleeper
        if api_mode not in {"responses", "chat_completions"}:
            raise ValueError(f"지원하지 않는 OpenAI API 모드: {api_mode}")
        self.api_mode = api_mode
        self.base_url = base_url
        if client is not None:
            self.client = client
        elif api_key:
            from openai import OpenAI
            kwargs: dict[str, Any] = {"api_key": api_key, "max_retries": 0}
            if base_url:
                kwargs["base_url"] = base_url
            self.client = OpenAI(**kwargs)
        else:
            self.client = None

    def generate(self, request: ModelRequest, model_config: ModelConfig) -> ModelResponse:
        if not self.api_key:
            return ModelResponse(
                provider="openai", model_id=model_config.id, requested_model=model_config.model,
                status="SKIPPED", error_type="MISSING_API_KEY",
                error_message="OPENAI_API_KEY is not configured",
            )
        started = time.perf_counter()
        attempts = 0
        fallback = False
        fallback_reason: str | None = None
        structured = True
        last_error: Exception | None = None
        while attempts <= self.max_retries:
            attempts += 1
            try:
                response = self._create(request, model_config, structured)
                raw_text = _response_text(response, self.api_mode)
                if not raw_text.strip():
                    return self._failure(
                        model_config, started, attempts, "EMPTY_RESPONSE", "모델 응답이 비어 있습니다",
                        structured, fallback, fallback_reason,
                    )
                usage = getattr(response, "usage", None)
                input_tokens = _nested_int(usage, "input_tokens" if self.api_mode == "responses" else "prompt_tokens")
                output_tokens = _nested_int(usage, "output_tokens" if self.api_mode == "responses" else "completion_tokens")
                total_tokens = _nested_int(usage, "total_tokens")
                input_details_name = "input_tokens_details" if self.api_mode == "responses" else "prompt_tokens_details"
                output_details_name = "output_tokens_details" if self.api_mode == "responses" else "completion_tokens_details"
                input_details = getattr(usage, input_details_name, None) if usage is not None else None
                output_details = getattr(usage, output_details_name, None) if usage is not None else None
                finish = _finish_reason(response, self.api_mode)
                if finish == "content_filter":
                    return self._failure(
                        model_config, started, attempts, "CONTENT_FILTERED", "콘텐츠 필터로 응답이 중단되었습니다",
                        structured, fallback, fallback_reason, raw_text=raw_text,
                    )
                return ModelResponse(
                    provider="openai", model_id=model_config.id, requested_model=model_config.model,
                    resolved_model=getattr(response, "model", None) or model_config.model,
                    raw_text=raw_text, input_tokens=input_tokens, output_tokens=output_tokens,
                    total_tokens=total_tokens if total_tokens is not None else _sum_optional(input_tokens, output_tokens),
                    cached_input_tokens=_nested_int(input_details, "cached_tokens"),
                    reasoning_tokens=_nested_int(output_details, "reasoning_tokens"),
                    latency_ms=(time.perf_counter() - started) * 1000, attempt_count=attempts,
                    finish_reason=finish, request_id=getattr(response, "_request_id", None), status="SUCCESS",
                    structured_output_applied=structured, structured_output_fallback_used=fallback,
                    structured_output_fallback_reason=fallback_reason,
                    provider_metadata={
                        "temperatureRequested": request.temperature,
                        "temperatureApplied": None,
                        "note": "OpenAI Responses API 호출에는 temperature를 적용하지 않음",
                        "streaming": False,
                        "toolsEnabled": False,
                        "apiMode": self.api_mode,
                        "baseUrl": self.base_url or "default",
                    },
                )
            except Exception as exc:  # SDK 오류 타입은 버전별로 달라 상태 코드와 클래스명을 함께 확인한다.
                last_error = exc
                error_type, retriable, status_code = _map_openai_error(exc)
                if structured and error_type == "INVALID_REQUEST":
                    structured = False
                    fallback = True
                    fallback_reason = sanitize_error(exc, (self.api_key or "",))
                    if attempts <= self.max_retries:
                        continue
                if retriable and attempts <= self.max_retries:
                    self.sleeper(self.backoff_seconds * (2 ** (attempts - 1)))
                    continue
                detail = sanitize_error(exc, (self.api_key or "",))
                if status_code:
                    detail = f"HTTP {status_code}: {detail}"
                return self._failure(
                    model_config, started, attempts, error_type, detail,
                    structured, fallback, fallback_reason,
                )
        return self._failure(
            model_config, started, attempts, "UNKNOWN_ERROR",
            sanitize_error(last_error or "알 수 없는 오류", (self.api_key or "",)),
            structured, fallback, fallback_reason,
        )

    def _create(self, request: ModelRequest, model_config: ModelConfig, structured: bool) -> Any:
        if self.api_mode == "chat_completions":
            kwargs: dict[str, Any] = {
                "model": model_config.model,
                "messages": [{"role": "user", "content": request.prompt}],
                "stream": False,
            }
            if structured:
                kwargs["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": _schema_name(request.test_mode),
                        "schema": request.schema,
                        "strict": True,
                    },
                }
            return self.client.chat.completions.create(**kwargs)
        kwargs = {"model": model_config.model, "input": request.prompt}
        if structured:
            kwargs["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": _schema_name(request.test_mode),
                    "schema": request.schema,
                    "strict": True,
                }
            }
        return self.client.responses.create(**kwargs)

    @staticmethod
    def _failure(
        config: ModelConfig,
        started: float,
        attempts: int,
        error_type: str,
        message: str,
        structured_applied: bool,
        fallback: bool,
        fallback_reason: str | None,
        raw_text: str = "",
    ) -> ModelResponse:
        return ModelResponse(
            provider="openai", model_id=config.id, requested_model=config.model,
            raw_text=raw_text, latency_ms=(time.perf_counter() - started) * 1000,
            attempt_count=attempts, status="FAILED", error_type=error_type,
            error_message=message, structured_output_applied=structured_applied,
            structured_output_fallback_used=fallback,
            structured_output_fallback_reason=fallback_reason,
        )


def _schema_name(mode: str) -> str:
    return f"woojuin_{mode.replace('-', '_')}_result"


def _integer_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _nested_int(value: Any, name: str) -> int | None:
    if value is None:
        return None
    raw = value.get(name) if isinstance(value, dict) else getattr(value, name, None)
    return _integer_or_none(raw)


def _sum_optional(first: Any, second: Any) -> int | None:
    a, b = _integer_or_none(first), _integer_or_none(second)
    return a + b if a is not None and b is not None else None


def _response_text(response: Any, api_mode: str) -> str:
    if api_mode == "chat_completions":
        choices = getattr(response, "choices", None) or []
        if not choices:
            return ""
        message = getattr(choices[0], "message", None)
        content = message.get("content") if isinstance(message, dict) else getattr(message, "content", None)
        return str(content or "")
    return str(getattr(response, "output_text", "") or "")


def _finish_reason(response: Any, api_mode: str = "responses") -> str | None:
    if api_mode == "chat_completions":
        choices = getattr(response, "choices", None) or []
        return getattr(choices[0], "finish_reason", None) if choices else None
    incomplete = getattr(response, "incomplete_details", None)
    reason = incomplete.get("reason") if isinstance(incomplete, dict) else getattr(incomplete, "reason", None)
    return reason or getattr(response, "status", None)


def _map_ollama_error(error_type: str) -> str:
    return {
        "CONNECTION_TIMEOUT": "TIMEOUT",
        "READ_TIMEOUT": "TIMEOUT",
        "OLLAMA_NOT_RUNNING": "CONNECTION_ERROR",
        "MODEL_EXECUTION_FAILED": "UNKNOWN_ERROR",
    }.get(error_type, "UNKNOWN_ERROR")


def _map_openai_error(exc: Exception) -> tuple[str, bool, int | None]:
    name = type(exc).__name__
    status = getattr(exc, "status_code", None)
    if name == "AuthenticationError" or status == 401:
        return "AUTHENTICATION_ERROR", False, status
    if name == "PermissionDeniedError" or status == 403:
        return "PERMISSION_DENIED", False, status
    if name == "NotFoundError" or status == 404:
        return "MODEL_NOT_FOUND", False, status
    if name == "RateLimitError" or status == 429:
        return "RATE_LIMIT_ERROR", True, status
    if name in {"APITimeoutError", "TimeoutError"}:
        return "TIMEOUT", True, status
    if name == "APIConnectionError":
        return "CONNECTION_ERROR", True, status
    if name in {"BadRequestError", "UnprocessableEntityError"} or status in {400, 422}:
        message = str(exc).casefold()
        if "content_filter" in message or "content filter" in message:
            return "CONTENT_FILTERED", False, status
        return "INVALID_REQUEST", False, status
    if isinstance(status, int) and status >= 500:
        return "UNKNOWN_ERROR", True, status
    return "UNKNOWN_ERROR", False, status
