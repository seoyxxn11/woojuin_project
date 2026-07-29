from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    api_key: str | None = field(repr=False)
    chat_model: str = "qwen/qwen3-8b"
    embedding_model: str = "openai/text-embedding-3-small"
    base_url: str = "https://openrouter.ai/api/v1"
    timeout_seconds: float = 90.0
    max_retries: int = 3
    http_referer: str | None = None
    app_title: str = "Woojuin AI Mix"
    category_score_threshold: float = 0.65
    category_max_results: int = 2


def _find_env_file(start: Path) -> Path | None:
    current = start.resolve()
    for directory in (current, *current.parents):
        candidate = directory / ".env"
        if candidate.is_file():
            return candidate
    return None


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name}은 숫자여야 합니다") from exc


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name}은 정수여야 합니다") from exc


def load_settings(start: Path | None = None) -> Settings:
    env_file = _find_env_file(start or Path.cwd())
    if env_file is not None:
        load_dotenv(env_file, override=False)

    timeout = _float_env("OPENROUTER_TIMEOUT_SECONDS", 90.0)
    retries = _int_env("OPENROUTER_MAX_RETRIES", 3)
    threshold = _float_env("CATEGORY_SCORE_THRESHOLD", 0.65)
    max_results = _int_env("CATEGORY_MAX_RESULTS", 2)
    if timeout <= 0:
        raise ValueError("OPENROUTER_TIMEOUT_SECONDS는 0보다 커야 합니다")
    if retries < 0:
        raise ValueError("OPENROUTER_MAX_RETRIES는 0 이상이어야 합니다")
    if not 0 <= threshold <= 1:
        raise ValueError("CATEGORY_SCORE_THRESHOLD는 0~1이어야 합니다")
    if not 1 <= max_results <= 10:
        raise ValueError("CATEGORY_MAX_RESULTS는 1~10이어야 합니다")

    api_key = os.getenv("OPENROUTER_API_KEY", "").strip() or None
    referer = os.getenv("OPENROUTER_HTTP_REFERER", "").strip() or None
    return Settings(
        api_key=api_key,
        chat_model=os.getenv("OPENROUTER_CHAT_MODEL", "qwen/qwen3-8b").strip(),
        embedding_model=os.getenv(
            "OPENROUTER_EMBEDDING_MODEL", "openai/text-embedding-3-small"
        ).strip(),
        base_url=os.getenv(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        ).strip().rstrip("/"),
        timeout_seconds=timeout,
        max_retries=retries,
        http_referer=referer,
        category_score_threshold=threshold,
        category_max_results=max_results,
    )
