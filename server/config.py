import os
import tomllib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, PrivateAttr

MODES = ('single', 'per_criterion')


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
    provider: Literal['openai', 'fake', 'ensemble']
    base_url_env: str | None = None
    api_key_env: str | None = None
    model: str = 'fake'
    supports_n: bool = False
    structured: Literal['json_schema', 'json_object', 'prompt'] = 'json_schema'
    max_concurrency: int = 8
    max_tokens: int = 4096
    extra_body: dict[str, Any] = {}
    cost: Cost | None = None
    hosting: Literal['local', 'external_api', 'hybrid'] = 'local'  # results.json `model.mode`
    # provider = "ensemble": member profiles as "name:mode"; per criterion the majority (scales: median) wins.
    members: list[str] = []
    _members: list[tuple['Profile', str]] = PrivateAttr(default_factory=list)

    def base_url(self) -> str:
        value = os.environ.get(self.base_url_env) if self.base_url_env else None
        if not value:
            raise ConfigError(f'profile {self.name}: env {self.base_url_env} is not set')
        return value.rstrip('/')

    def api_key(self) -> str | None:
        return os.environ.get(self.api_key_env) if self.api_key_env else None

    def member_profiles(self) -> list[tuple['Profile', str]]:
        """Resolved (profile, mode) pairs of an ensemble, in vote order (the first member breaks ties)."""
        return list(self._members)


def _resolve_ensembles(profiles: dict[str, Profile]) -> None:
    for p in profiles.values():
        if p.provider != 'ensemble':
            continue
        if len(p.members) < 2:
            raise ConfigError(f'ensemble {p.name}: needs at least 2 members')
        resolved: list[tuple[Profile, str]] = []
        for spec in p.members:
            name, _, mode = spec.partition(':')
            member = profiles.get(name)
            if member is None or member.provider == 'ensemble':
                raise ConfigError(f'ensemble {p.name}: member {name!r} is not a plain profile')
            if mode not in MODES:
                raise ConfigError(f'ensemble {p.name}: member {spec!r} needs a mode, one of {MODES}')
            resolved.append((member, mode))
        p._members = resolved
        # What results.json reports: every model that votes, and local / external_api / hybrid.
        p.model = ', '.join(dict.fromkeys(m.model for m, _ in resolved))
        hostings = {m.hosting for m, _ in resolved}
        p.hosting = hostings.pop() if len(hostings) == 1 else 'hybrid'


def load_profiles(path: Path = Path('config/profiles.toml')) -> dict[str, Profile]:
    with path.open('rb') as f:
        tables = tomllib.load(f).get('profiles', {})
    profiles = {name: Profile(name=name, **table) for name, table in tables.items()}
    _resolve_ensembles(profiles)
    return profiles


def default_profile() -> Profile:
    name = os.environ.get('LLM_PROFILE', 'fake')
    profiles = load_profiles()
    if name not in profiles:
        raise ConfigError(f'unknown LLM_PROFILE {name!r}')
    return profiles[name]
