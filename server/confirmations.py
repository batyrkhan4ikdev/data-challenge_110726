"""Подтверждения проверяющим (issue #44): пакетное «принять неспорные» и поштучное.

Хранятся отдельно от апелляций (`confirmations/<id>.json`, `confirmation_index/<evaluation_id>.json`)
и не участвуют в расчёте итога: `server/scoring.py` их не читает.
"""

import asyncio
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from litestar import Controller, get, post
from litestar.params import FromPath, JSONBody

from server.models import Attention, Confirmation, ConfirmationCreate, ConfirmationStats
from server.routes import Svc
from server.store import NotFound, Store, _read_text, _safe, atomic_write
from server.triage import evaluation_attention



class ConfirmationStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def _path(self, kind: str, name: str) -> Path:
        return self.root / kind / f'{_safe(name)}.json'

    async def save(self, c: Confirmation) -> None:
        await asyncio.to_thread(atomic_write, self._path('confirmations', c.id), c.model_dump_json(indent=2))
        async with self._locks[c.evaluation_id]:
            path = self._path('confirmation_index', c.evaluation_id)
            text = await asyncio.to_thread(_read_text, path)
            ids = json.loads(text) if text else []
            ids.append(c.id)
            await asyncio.to_thread(atomic_write, path, json.dumps(ids))

    async def _get(self, confirmation_id: str) -> Confirmation:
        text = await asyncio.to_thread(_read_text, self._path('confirmations', confirmation_id))
        if text is None:
            raise NotFound(f'Подтверждение {confirmation_id} не найдено')
        return Confirmation.model_validate_json(text)

    async def for_evaluation(self, evaluation_id: str) -> list[Confirmation]:
        text = await asyncio.to_thread(_read_text, self._path('confirmation_index', evaluation_id))
        return [await self._get(i) for i in (json.loads(text) if text else [])]

    async def all(self) -> list[Confirmation]:
        folder = self.root / 'confirmations'
        names = await asyncio.to_thread(lambda: sorted(p.stem for p in folder.glob('*.json')))
        return [await self._get(n) for n in names]


_stores: dict[Path, ConfirmationStore] = {}


def confirmation_store(store: Store) -> ConfirmationStore:
    root = Path(store.root).resolve()
    if root not in _stores:
        _stores[root] = ConfirmationStore(root)
    return _stores[root]


class ConfirmationsController(Controller):
    path = '/'

    @post('/evaluations/{evaluation_id:str}/confirmations', status_code=200)
    async def create(
        self, svc: Svc, evaluation_id: FromPath[str], data: JSONBody[ConfirmationCreate]
    ) -> Confirmation:
        if not data.reviewer.strip():
            raise ValueError('Укажите проверяющего')
        ev = await svc.store.get_evaluation(evaluation_id)
        known = {c.id for c in (await svc.recorded_checklist(ev)).criteria}
        ids = list(dict.fromkeys(data.criterion_ids))
        if not ids:
            raise ValueError('Не выбрано ни одного критерия')
        unknown = [i for i in ids if i not in known]
        if unknown:
            raise ValueError(f'неизвестные критерии: {unknown}')
        auto_note = None
        if data.mode == 'batch':
            disputed = sorted(set(ids) & set((await evaluation_attention(svc, ev)).criterion_ids))
            if disputed:
                raise ValueError(f'спорные критерии нельзя принять пакетом: {disputed}')
            auto_note = f'принято пакетом без раскрытия доказательств: {", ".join(ids)}'
        confirmation = Confirmation(
            id=uuid4().hex,
            evaluation_id=ev.id,
            criterion_ids=ids,
            mode=data.mode,
            reviewer=data.reviewer.strip(),
            note=data.note.strip(),
            auto_note=auto_note,
            created_at=datetime.now(UTC),
        )
        await confirmation_store(svc.store).save(confirmation)
        return confirmation

    @get('/evaluations/{evaluation_id:str}/confirmations')
    async def list_for_evaluation(self, svc: Svc, evaluation_id: FromPath[str]) -> list[Confirmation]:
        await svc.store.get_evaluation(evaluation_id)
        return await confirmation_store(svc.store).for_evaluation(evaluation_id)

    @get('/confirmations/stats')
    async def stats(self, svc: Svc) -> ConfirmationStats:
        batch = single = 0
        for c in await confirmation_store(svc.store).all():
            if c.mode == 'batch':
                batch += len(c.criterion_ids)
            else:
                single += len(c.criterion_ids)
        overridden = sum(
            1 for a in await svc.store.list_appeals('resolved') if a.decision and a.decision.action == 'change'
        )
        return ConfirmationStats(batch=batch, single=single, overridden=overridden)

    @get('/evaluations/{evaluation_id:str}/attention')
    async def attention(self, svc: Svc, evaluation_id: FromPath[str]) -> Attention:
        return await evaluation_attention(svc, await svc.store.get_evaluation(evaluation_id))
