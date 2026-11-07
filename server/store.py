import asyncio
import json
import os
import tempfile
from collections import defaultdict
from pathlib import Path

from pydantic import BaseModel

from server.models import Appeal, Evaluation, RawCall


class NotFound(LookupError):
    """An unknown id: the API answers 404."""


def atomic_write(path: Path, text: str) -> None:
    """Write `text` to a temp file in the target directory, then rename it over `path`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f'.{path.name}.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return None


def _safe(name: str) -> str:
    """Ids become file names; reject anything that could escape the store directory."""
    if not name or name in {'.', '..'} or any(ch in name for ch in '/\\:*?"<>|\0'):
        raise NotFound(f'некорректный идентификатор {name!r}')
    return name


_LABELS = {'evaluations': 'Оценка', 'appeals': 'Апелляция'}


class Store:
    """Evaluations, raw LLM calls and appeals, one JSON file per object.

    Layout under `root`:
    - `evaluations/<id>.json`, `raw/<id>.jsonl`, `appeals/<id>.json`;
    - `index/<conversation_id>.json`: evaluation ids of a conversation, oldest first;
    - `appeal_index/<evaluation_id>.json`: appeal ids of an evaluation, oldest first.
    """

    def __init__(self, root: Path = Path('data/store')) -> None:
        self.root = Path(root)
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def _path(self, kind: str, name: str, suffix: str = '.json') -> Path:
        return self.root / kind / f'{_safe(name)}{suffix}'

    async def _load[M: BaseModel](self, model: type[M], kind: str, name: str) -> M:
        text = await asyncio.to_thread(_read_text, self._path(kind, name))
        if text is None:
            raise NotFound(f'{_LABELS.get(kind, kind)} {name} не найдена')
        return model.model_validate_json(text)

    async def _write(self, kind: str, name: str, obj: BaseModel) -> None:
        await asyncio.to_thread(atomic_write, self._path(kind, name), obj.model_dump_json(indent=2))

    async def _index_ids(self, kind: str, key: str) -> list[str]:
        text = await asyncio.to_thread(_read_text, self._path(kind, key))
        return json.loads(text) if text else []

    async def _index_add(self, kind: str, key: str, item_id: str) -> None:
        async with self._locks[f'{kind}/{key}']:
            ids = await self._index_ids(kind, key)
            if item_id in ids:
                return
            ids.append(item_id)
            await asyncio.to_thread(atomic_write, self._path(kind, key), json.dumps(ids))

    # Evaluations

    async def save_evaluation(self, ev: Evaluation, raw: list[RawCall]) -> None:
        lines = ''.join(r.model_dump_json() + '\n' for r in raw)
        await asyncio.to_thread(atomic_write, self._path('raw', ev.id, '.jsonl'), lines)
        await self._write('evaluations', ev.id, ev)
        await self._index_add('index', ev.conversation_id, ev.id)

    async def get_evaluation(self, evaluation_id: str) -> Evaluation:
        return await self._load(Evaluation, 'evaluations', evaluation_id)

    async def get_raw(self, evaluation_id: str) -> list[RawCall]:
        await self.get_evaluation(evaluation_id)
        text = await asyncio.to_thread(_read_text, self._path('raw', evaluation_id, '.jsonl'))
        return [RawCall.model_validate_json(line) for line in (text or '').splitlines() if line.strip()]

    async def list_for_conversation(self, conversation_id: str) -> list[Evaluation]:
        """Every evaluation of a conversation, newest first."""
        ids = await self._index_ids('index', conversation_id)
        evs = [await self.get_evaluation(i) for i in ids]
        return sorted(evs, key=lambda e: e.created_at, reverse=True)

    async def latest_for_conversation(self, conversation_id: str, group_id: str) -> Evaluation | None:
        """The newest evaluation of a conversation within a dataset group, or None."""
        for ev in await self.list_for_conversation(conversation_id):
            if ev.group_id == group_id:
                return ev
        return None

    # Appeals

    async def save_appeal(self, appeal: Appeal) -> None:
        await self._write('appeals', appeal.id, appeal)
        await self._index_add('appeal_index', appeal.evaluation_id, appeal.id)

    async def get_appeal(self, appeal_id: str) -> Appeal:
        return await self._load(Appeal, 'appeals', appeal_id)

    async def list_appeals(self, status: str | None = None) -> list[Appeal]:
        """All appeals, oldest first, optionally filtered by status."""
        folder = self.root / 'appeals'
        names = await asyncio.to_thread(lambda: sorted(p.stem for p in folder.glob('*.json')))
        appeals = [await self.get_appeal(n) for n in names]
        if status is not None:
            appeals = [a for a in appeals if a.status == status]
        return sorted(appeals, key=lambda a: a.created_at)

    async def appeals_for(self, evaluation_id: str) -> list[Appeal]:
        ids = await self._index_ids('appeal_index', evaluation_id)
        return [await self.get_appeal(i) for i in ids]
