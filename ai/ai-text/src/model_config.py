from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


SUPPORTED_PROVIDERS = {"ollama", "openai"}
SUPPORTED_TEST_MODES = {"category-only", "summary-only", "metadata-only", "integrated"}
REQUIRED_FIELDS = {"id", "provider", "model", "enabled", "purpose", "inputTypes", "testModes"}


class ModelConfigError(ValueError):
    pass


@dataclass(frozen=True)
class ModelConfig:
    id: str
    provider: str
    model: str
    enabled: bool
    purpose: str
    input_types: tuple[str, ...]
    test_modes: tuple[str, ...]


@dataclass(frozen=True)
class ModelSelection:
    model_id: str
    config: ModelConfig | None
    status: str = "READY"
    error_type: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class PricingConfig:
    currency: str
    unit: str
    updated_at: str | None
    models: dict[str, dict[str, float | None]]


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ModelConfigError(f"설정 파일을 읽을 수 없습니다 ({path}): {exc}") from exc
    if not isinstance(value, dict):
        raise ModelConfigError(f"설정 루트는 객체여야 합니다: {path}")
    return value


def load_models(path: Path) -> dict[str, ModelConfig]:
    raw_models = _read_yaml(path).get("models")
    if not isinstance(raw_models, list):
        raise ModelConfigError("models.yaml의 'models' 필드는 목록이어야 합니다")
    result: dict[str, ModelConfig] = {}
    for index, raw in enumerate(raw_models):
        label = raw.get("id", f"index {index}") if isinstance(raw, dict) else f"index {index}"
        if not isinstance(raw, dict):
            raise ModelConfigError(f"모델 {label}: 객체여야 합니다")
        missing = sorted(REQUIRED_FIELDS - raw.keys())
        if missing:
            raise ModelConfigError(f"모델 {label}: 필수 필드 누락: {', '.join(missing)}")
        model_id = raw["id"]
        if not isinstance(model_id, str) or not model_id.strip():
            raise ModelConfigError(f"모델 {label}: id는 비어 있지 않은 문자열이어야 합니다")
        model_id = model_id.strip()
        if model_id in result:
            raise ModelConfigError(f"모델 {model_id}: 중복 모델 ID")
        provider = raw["provider"]
        if provider not in SUPPORTED_PROVIDERS:
            raise ModelConfigError(f"모델 {model_id}: 지원하지 않는 provider '{provider}'")
        model_name = raw["model"]
        if not isinstance(model_name, str) or not model_name.strip():
            raise ModelConfigError(f"모델 {model_id}: model은 비어 있지 않은 문자열이어야 합니다")
        if not isinstance(raw["enabled"], bool):
            raise ModelConfigError(f"모델 {model_id}: enabled는 boolean이어야 합니다")
        if not isinstance(raw["inputTypes"], list) or not all(isinstance(x, str) and x for x in raw["inputTypes"]):
            raise ModelConfigError(f"모델 {model_id}: inputTypes는 비어 있지 않은 문자열 목록이어야 합니다")
        modes = raw["testModes"]
        if not isinstance(modes, list) or not all(isinstance(x, str) for x in modes):
            raise ModelConfigError(f"모델 {model_id}: testModes는 문자열 목록이어야 합니다")
        unknown_modes = sorted(set(modes) - SUPPORTED_TEST_MODES)
        if unknown_modes:
            raise ModelConfigError(f"모델 {model_id}: 알 수 없는 testModes: {', '.join(unknown_modes)}")
        result[model_id] = ModelConfig(
            id=model_id,
            provider=provider,
            model=model_name.strip(),
            enabled=raw["enabled"],
            purpose=str(raw["purpose"]),
            input_types=tuple(raw["inputTypes"]),
            test_modes=tuple(modes),
        )
    return result


def load_suites(path: Path) -> dict[str, tuple[str, ...]]:
    raw_suites = _read_yaml(path).get("suites")
    if not isinstance(raw_suites, dict):
        raise ModelConfigError("model-suites.yaml의 'suites' 필드는 객체여야 합니다")
    suites: dict[str, tuple[str, ...]] = {}
    for name, ids in raw_suites.items():
        if not isinstance(name, str) or not name.strip():
            raise ModelConfigError("suite 이름은 비어 있지 않은 문자열이어야 합니다")
        if not isinstance(ids, list) or not all(isinstance(x, str) and x.strip() for x in ids):
            raise ModelConfigError(f"suite {name}: 모델 ID 문자열 목록이어야 합니다")
        suites[name] = tuple(x.strip() for x in ids)
    return suites


def select_models(
    models: dict[str, ModelConfig], model_ids: list[str] | tuple[str, ...], mode: str
) -> list[ModelSelection]:
    selections: list[ModelSelection] = []
    seen: set[str] = set()
    for model_id in model_ids:
        if model_id in seen:
            selections.append(ModelSelection(model_id, models.get(model_id), "SKIPPED", "DUPLICATE_MODEL_ID", f"중복 모델 ID: {model_id}"))
            continue
        seen.add(model_id)
        config = models.get(model_id)
        if config is None:
            selections.append(ModelSelection(model_id, None, "SKIPPED", "MODEL_NOT_FOUND", f"등록되지 않은 모델 ID: {model_id}"))
        elif not config.enabled:
            selections.append(ModelSelection(model_id, config, "SKIPPED", "MODEL_DISABLED", f"비활성화된 모델: {model_id}"))
        elif mode not in config.test_modes:
            selections.append(ModelSelection(model_id, config, "SKIPPED", "UNSUPPORTED_TEST_MODE", f"{model_id}는 {mode} 모드를 지원하지 않습니다"))
        elif "text" not in config.input_types:
            selections.append(ModelSelection(model_id, config, "SKIPPED", "UNSUPPORTED_INPUT_TYPE", f"{model_id}는 text 입력을 지원하지 않습니다"))
        else:
            selections.append(ModelSelection(model_id, config))
    return selections


def load_pricing(path: Path) -> PricingConfig:
    raw = _read_yaml(path)
    raw_models = raw.get("models", {})
    if not isinstance(raw_models, dict):
        raise ModelConfigError("model-pricing.yaml의 'models' 필드는 객체여야 합니다")
    prices: dict[str, dict[str, float | None]] = {}
    for model_id, entry in raw_models.items():
        if not isinstance(entry, dict):
            raise ModelConfigError(f"가격 {model_id}: 객체여야 합니다")
        values: dict[str, float | None] = {}
        for key in ("inputPrice", "outputPrice"):
            value = entry.get(key)
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0):
                raise ModelConfigError(f"가격 {model_id}.{key}: 0 이상의 숫자 또는 null이어야 합니다")
            values[key] = float(value) if value is not None else None
        prices[str(model_id)] = values
    return PricingConfig(str(raw.get("currency", "USD")), str(raw.get("unit", "per_1m_tokens")), raw.get("updatedAt"), prices)


def calculate_cost(pricing: PricingConfig, model_id: str, input_tokens: int | None, output_tokens: int | None) -> float | None:
    entry = pricing.models.get(model_id)
    if not entry or entry.get("inputPrice") is None or entry.get("outputPrice") is None:
        return None
    if input_tokens is None or output_tokens is None:
        return None
    return input_tokens / 1_000_000 * float(entry["inputPrice"]) + output_tokens / 1_000_000 * float(entry["outputPrice"])


def safe_filename(value: str) -> str:
    safe = "".join(character if character.isalnum() or character in "._-" else "_" for character in value.strip())
    return safe.strip("._") or "model"
