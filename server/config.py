import os
import tomllib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel


class ConfigError(Exception):
    pass


class Cost(BaseModel):
    kind: Literal['gpu', 'tokens']
    usd_per_hour: float = 0.0
    concurrency: int = 1
    usd_per_mtok_in: float = 0.0
    usd_per_mtok_out: float = 0.0


class Profile(BaseModel):
    name: str
    provider: Literal['openai', 'fake']
    base_url_env: str | None = None
    api_key_env: str | None = None
    model: str = 'fake'
    supports_n: bool = False
    structured: Literal['json_schema', 'json_object'] = 'json_schema'
    max_concurrency: int = 8
    max_tokens: int = 4096
    extra_body: dict[str, Any] = {}
    cost: Cost | None = None

    def base_url(self) -> str:
        value = os.environ.get(self.base_url_env) if self.base_url_env else None
        if not value:
            raise ConfigError(f'profile {self.name}: env {self.base_url_env} is not set')
        return value.rstrip('/')

    def api_key(self) -> str | None:
        return os.environ.get(self.api_key_env) if self.api_key_env else None


def load_profiles(path: Path = Path('config/profiles.toml')) -> dict[str, Profile]:
    with path.open('rb') as f:
        tables = tomllib.load(f).get('profiles', {})
    return {name: Profile(name=name, **table) for name, table in tables.items()}


def default_profile() -> Profile:
    name = os.environ.get('LLM_PROFILE', 'fake')
    profiles = load_profiles()
    if name not in profiles:
        raise ConfigError(f'unknown LLM_PROFILE {name!r}')
    return profiles[name]
