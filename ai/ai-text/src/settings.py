from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None = None
    gms_key: str | None = None

    @property
    def openai_api_key_configured(self) -> bool:
        return bool(self.openai_api_key)

    def key_for(self, env_name: str) -> str | None:
        if env_name == "GMS_KEY":
            return self.gms_key
        if env_name == "OPENAI_API_KEY":
            return self.openai_api_key
        return None

    def key_configured(self, env_name: str) -> bool:
        return bool(self.key_for(env_name))


def find_env_file(start: Path) -> Path | None:
    directory = start.resolve()
    for candidate_root in (directory, *directory.parents):
        candidate = candidate_root / ".env"
        if candidate.is_file():
            return candidate
    return None


def load_settings(root: Path | None = None) -> Settings:
    env_path = find_env_file(root or Path.cwd())
    if env_path is not None:
        load_dotenv(dotenv_path=env_path, override=False)
    openai_value = os.getenv("OPENAI_API_KEY", "").strip()
    gms_value = os.getenv("GMS_KEY", "").strip() or openai_value
    return Settings(openai_api_key=openai_value or None, gms_key=gms_value or None)
