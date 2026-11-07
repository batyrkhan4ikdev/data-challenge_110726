"""Transcript sources of a conversation: the organizer's (`api`), one per ASR provider, and a pasted `custom` one.

Non-`api` sources are `Record` JSON files in `<store>/transcripts/<cid>/<source>.json`. Records in
`<calls_dir>/<source>.dev.json` (organizer API format) are seeded as that source for their conversations.
"""

import asyncio
import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from server.dataset import DatasetError, normalize_response
from server.models import AsrQuality, Record, Speaker, TranscriptSourceInfo, Turn
from server.store import NotFound, atomic_write

log = logging.getLogger(__name__)

API = 'api'
CUSTOM = 'custom'
LABELS = {API: 'Организатор (API)', CUSTOM: 'Свой транскрипт', 'freedomspeech': 'FreedomSpeech'}

EMPTY_CUSTOM = 'Транскрипт пуст: вставьте текст с репликами'
NO_PREFIX = 'Не найдено ни одной реплики: начинайте строки с «оператор:», «клиент:» или «бот:»'
LEADING_UNPREFIXED = (
    'Строка {n} идёт до первой реплики с префиксом «оператор:», «клиент:» или «бот:»: непонятно, кто говорит'
)

_SPEAKERS: dict[str, Speaker] = {
    'оператор': 'operator', 'operator': 'operator', 'о': 'operator',
    'клиент': 'client', 'client': 'client', 'к': 'client',
    'бот': 'bot', 'bot': 'bot', 'б': 'bot',
}
_PREFIX = re.compile(r'^\s*(' + '|'.join(sorted(_SPEAKERS, key=len, reverse=True)) + r')\s*:\s*(.*)$', re.IGNORECASE)
_SOURCE_ID = re.compile(r'^[\w.-]+$')


def parse_custom_text(text: str, base: Record) -> Record:
    """One turn per prefixed line; an unprefixed line continues the previous turn. `ValueError` on empty input.

    The turns carry no timestamps (`timestamp=''`, `offset_s=None`).
    """
    if not text.strip():
        raise ValueError(EMPTY_CUSTOM)
    parts: list[tuple[Speaker, list[str]]] = []
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        m = _PREFIX.match(line)
        if m:
            parts.append((_SPEAKERS[m.group(1).lower()], [m.group(2).strip()]))
        elif parts:
            parts[-1][1].append(line.strip())
        else:
            raise ValueError(LEADING_UNPREFIXED.format(n=n))
    turns = [
        Turn(idx=i, timestamp='', offset_s=None, speaker=speaker, text=' '.join(x for x in chunks if x))
        for i, (speaker, chunks) in enumerate(parts)
    ]
    if not turns or all(not t.text for t in turns):
        raise ValueError(NO_PREFIX if not turns else EMPTY_CUSTOM)
    return Record(
        conversation_id=base.conversation_id,
        channel=base.channel,
        language=base.language,
        transcript=turns,
        audio_url=base.audio_url,
    )


def _safe(name: str) -> str:
    if not _SOURCE_ID.match(name) or name in {'.', '..'}:
        raise NotFound(f'некорректный идентификатор {name!r}')
    return name


def _read_json(path: Path) -> str | None:
    try:
        return path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return None


def _mtime(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, UTC)


def _providers() -> dict:
    """Enabled ASR provider configs; empty when `server.asr` is missing or its config is broken."""
    try:
        from server.asr.providers import load_asr_providers

        return {k: v for k, v in load_asr_providers().items() if getattr(v, 'enabled', True)}
    except Exception as e:  # the listing must not depend on the optional ASR layer
        log.warning('ASR providers unavailable: %s: %s', type(e).__name__, e)
        return {}


class TranscriptStore:
    def __init__(
        self,
        root: Path,
        calls_dir: Path = Path('data/calls'),
        quality_path: Path = Path('data/asr/quality.json'),
    ) -> None:
        self.root = Path(root)
        self.calls_dir = Path(calls_dir)
        self.quality_path = Path(quality_path)
        self._seeds: dict[str, dict[str, tuple[Record, datetime]]] | None = None

    def _path(self, cid: str, source: str) -> Path:
        return self.root / _safe(cid) / f'{_safe(source)}.json'

    def _load_seeds(self) -> dict[str, dict[str, tuple[Record, datetime]]]:
        if self._seeds is not None:
            return self._seeds
        seeds: dict[str, dict[str, tuple[Record, datetime]]] = {}
        for path in sorted(self.calls_dir.glob('*.dev.json')):
            source = path.name.removesuffix('.dev.json')
            try:
                records = normalize_response(json.loads(path.read_text(encoding='utf-8')), 'DEV')
            except (OSError, ValueError, DatasetError) as e:
                log.warning('seed %s skipped: %s', path.name, type(e).__name__)
                continue
            stamp = _mtime(path)
            seeds[source] = {r.conversation_id: (r, stamp) for r in records}
        self._seeds = seeds
        return seeds

    def _quality(self) -> dict[str, AsrQuality]:
        text = _read_json(self.quality_path)
        if not text:
            return {}
        try:
            raw = json.loads(text)
            return {k: AsrQuality.model_validate(v) for k, v in raw.items()}
        except (ValueError, AttributeError, ValidationError) as e:
            log.warning('quality.json ignored: %s', type(e).__name__)
            return {}

    async def load(self, cid: str, source: str) -> Record | None:
        """The stored (else seeded) record of a non-`api` source, or None."""
        stored = await asyncio.to_thread(_read_json, self._path(cid, source))
        if stored is not None:
            return Record.model_validate_json(stored)
        seeded = (await asyncio.to_thread(self._load_seeds)).get(source, {}).get(cid)
        return seeded[0] if seeded else None

    async def save(self, source: str, record: Record) -> None:
        path = self._path(record.conversation_id, source)
        await asyncio.to_thread(atomic_write, path, record.model_dump_json(indent=2))

    async def sources(self, cid: str) -> list[TranscriptSourceInfo]:
        """`api` first, then ASR providers (configured, stored or seeded), then `custom`."""
        providers = await asyncio.to_thread(_providers)
        seeds = await asyncio.to_thread(self._load_seeds)
        quality = await asyncio.to_thread(self._quality)
        folder = self.root / _safe(cid)
        stored = await asyncio.to_thread(lambda: {p.stem: _mtime(p) for p in folder.glob('*.json')})
        seeded = {s: by_cid[cid][1] for s, by_cid in seeds.items() if cid in by_cid}
        made = {**seeded, **stored}

        def info(source: str, kind: Literal['api', 'asr', 'custom']) -> TranscriptSourceInfo:
            provider = providers.get(source)
            q = quality.get(source)
            label = (
                (provider.label if provider else None)
                or LABELS.get(source)
                or (q.label if q and q.label else None)
                or source
            )
            return TranscriptSourceInfo(
                source=source,
                label=label,
                kind=kind,
                available=source == API or source in made,
                created_at=made.get(source),
                provider_hosting=provider.hosting if provider else None,
                quality=q,
            )

        asr_ids = [*providers, *sorted(s for s in made if s not in providers and s != CUSTOM)]
        return [info(API, 'api'), *(info(s, 'asr') for s in asr_ids), info(CUSTOM, 'custom')]
