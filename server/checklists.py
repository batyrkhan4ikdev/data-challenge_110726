import asyncio
import builtins
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from server.models import Channel, Checklist, ChecklistSummary
from server.store import NotFound, atomic_write

FALLBACK_ID = 'chat'


class ChecklistError(Exception):
    """An invalid checklist or a conflicting create; `details` lists the validation errors."""

    def __init__(self, message: str, details: list[str] | None = None) -> None:
        super().__init__(message)
        self.details = details


def validate(c: Checklist) -> list[str]:
    """Russian error messages; an empty list means the checklist is valid."""
    errors: list[str] = []
    if not c.id.strip():
        errors.append('пустой id чек-листа')
    if not c.name.strip():
        errors.append('пустое название чек-листа')

    section_ids: set[str] = set()
    for s in c.sections:
        if not s.id.strip():
            errors.append('пустой id раздела')
        elif s.id in section_ids:
            errors.append(f'повторяющийся id раздела {s.id}')
        if not s.title.strip():
            errors.append(f'пустое название раздела {s.id}')
        section_ids.add(s.id)

    seen: set[str] = set()
    for cr in c.criteria:
        name = cr.id or '?'
        if not cr.id.strip():
            errors.append('пустой id критерия')
        elif cr.id in seen:
            errors.append(f'повторяющийся id критерия {cr.id}')
        seen.add(cr.id)
        if not cr.title.strip():
            errors.append(f'{name}: пустое название критерия')
        if cr.section_id is not None and cr.section_id not in section_ids:
            errors.append(f'{name}: неизвестный раздел {cr.section_id}')
        if cr.weight < 0:
            errors.append(f'{name}: отрицательный вес {cr.weight:g}')

        if cr.kind == 'gross_error':
            if cr.answer_type != 'yes_no':
                errors.append(f'{name}: грубая ошибка должна иметь тип ответа «да/нет»')
            if cr.weight != 0:
                errors.append(f'{name}: вес грубой ошибки должен быть 0, указан {cr.weight:g}')

        if cr.answer_type == 'yes_no':
            if cr.steps is not None:
                errors.append(f'{name}: у критерия «да/нет» не должно быть ступеней шкалы')
            continue
        if not cr.steps or len(cr.steps) < 2:
            errors.append(f'{name}: у шкалы должно быть не меньше двух ступеней')
            continue
        values = [s.value for s in cr.steps]
        if len(set(values)) != len(values):
            errors.append(f'{name}: повторяющиеся значения ступеней шкалы')
        elif min(values) < 0 or max(values) <= 0:
            errors.append(f'{name}: значения ступеней должны быть ≥ 0, верхняя ступень > 0')
        if cr.kind == 'scored' and cr.weight == 0:
            errors.append(f'{name}: вес шкалы не может быть 0')

    if sum(cr.weight for cr in c.criteria if cr.kind == 'scored') == 0:
        errors.append('сумма весов оцениваемых критериев равна 0')
    return errors


def _check(c: Checklist) -> None:
    errors = validate(c)
    if errors:
        raise ChecklistError('Чек-лист невалиден', errors)


def _versions(folder: Path) -> builtins.list[int]:
    out = []
    for p in folder.glob('v*.json'):
        if p.stem[1:].isdigit():
            out.append(int(p.stem[1:]))
    return sorted(out)


class ChecklistStore:
    """Versioned checklists at `<root>/<id>/v<N>.json`. Saving writes v(N+1); vN is never rewritten."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._cache: dict[tuple[str, int], Checklist] = {}

    def _folder(self, checklist_id: str) -> Path:
        if not checklist_id or checklist_id in {'.', '..'} or any(ch in checklist_id for ch in '/\\:*?"<>|\0'):
            raise NotFound(f'чек-лист {checklist_id!r} не найден')
        return self.root / checklist_id

    async def _latest_version(self, checklist_id: str) -> int | None:
        versions = await asyncio.to_thread(_versions, self._folder(checklist_id))
        return versions[-1] if versions else None

    async def _write(self, c: Checklist) -> None:
        path = self._folder(c.id) / f'v{c.version}.json'
        await asyncio.to_thread(atomic_write, path, c.model_dump_json(indent=2))
        self._cache[(c.id, c.version)] = c

    async def list(self) -> builtins.list[ChecklistSummary]:
        ids = await asyncio.to_thread(
            lambda: sorted(p.name for p in self.root.iterdir() if p.is_dir()) if self.root.is_dir() else []
        )
        out = []
        for cid in ids:
            if await self._latest_version(cid) is None:
                continue
            c = await self.get(cid)
            out.append(
                ChecklistSummary(id=c.id, name=c.name, channel_default=c.channel_default, version=c.version)
            )
        return out

    async def get(self, checklist_id: str, version: int | None = None) -> Checklist:
        if version is None:
            version = await self._latest_version(checklist_id)
            if version is None:
                raise NotFound(f'чек-лист {checklist_id} не найден')
        cached = self._cache.get((checklist_id, version))
        if cached is not None:
            return cached
        path = self._folder(checklist_id) / f'v{version}.json'
        try:
            text = await asyncio.to_thread(path.read_text, encoding='utf-8')
        except FileNotFoundError:
            raise NotFound(f'чек-лист {checklist_id} версии {version} не найден') from None
        c = Checklist.model_validate_json(text)
        self._cache[(checklist_id, version)] = c
        return c

    async def create(self, c: Checklist) -> Checklist:
        """Store a new checklist as v1; the incoming version is ignored."""
        _check(c)
        async with self._locks[c.id]:
            if await self._latest_version(c.id) is not None:
                raise ChecklistError(f'чек-лист {c.id} уже существует')
            new = c.model_copy(update={'version': 1})
            await self._write(new)
            return new

    async def save(self, c: Checklist) -> Checklist:
        """Store the next version of an existing checklist."""
        _check(c)
        async with self._locks[c.id]:
            latest = await self._latest_version(c.id)
            if latest is None:
                raise NotFound(f'чек-лист {c.id} не найден')
            new = c.model_copy(update={'version': latest + 1})
            await self._write(new)
            return new

    async def seed_defaults(self, directory: Path) -> None:
        """Copy `<directory>/*.default.json` for ids not yet present."""
        paths = await asyncio.to_thread(lambda: sorted(Path(directory).glob('*.default.json')))
        for path in paths:
            c = Checklist.model_validate_json(await asyncio.to_thread(path.read_text, encoding='utf-8'))
            _check(c)
            async with self._locks[c.id]:
                if await self._latest_version(c.id) is None:
                    await self._write(c.model_copy(update={'version': 1}))

    async def default_for(self, channel: Channel) -> Checklist:
        """Latest version of the checklist whose `channel_default` is `channel`.

        If several match, the one saved most recently wins; with none, the `chat` checklist is used.
        """
        best: tuple[int, str] | None = None
        for s in await self.list():
            if s.channel_default != channel:
                continue
            path = self._folder(s.id) / f'v{s.version}.json'
            mtime = await asyncio.to_thread(lambda p=path: p.stat().st_mtime_ns)
            if best is None or mtime > best[0]:
                best = (mtime, s.id)
        return await self.get(best[1] if best else FALLBACK_ID)

    async def seed_drift(self, directory: Path, channels: Iterable[Channel]) -> builtins.list[tuple[Checklist, Checklist]]:
        """(current default, seed) for each channel whose default checklist no longer equals `<directory>/*.default.json`.

        Used before an organizer submission: the control set must be scored with the organizers' checklist,
        not with whatever was last edited in the UI (version numbers are ignored in the comparison).
        """
        paths = await asyncio.to_thread(lambda: sorted(Path(directory).glob('*.default.json')))
        seeds: dict[Channel | None, Checklist] = {}
        for path in paths:
            c = Checklist.model_validate_json(await asyncio.to_thread(path.read_text, encoding='utf-8'))
            seeds[c.channel_default] = c
        drift = []
        for channel in sorted(set(channels)):
            seed = seeds.get(channel)
            if seed is None:
                continue
            current = await self.default_for(channel)
            if current.model_dump(exclude={'version'}) != seed.model_dump(exclude={'version'}):
                drift.append((current, seed))
        return drift
