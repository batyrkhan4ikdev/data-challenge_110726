import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from litestar.datastructures import State
from litestar.di import NamedDependency

from server.checklists import ChecklistStore
from server.config import Profile
from server.jobs import JobRunner
from server.models import Appeal, Checklist, Evaluation, EvaluationSummary, FinalResult, Record
from server.scoring import final_result
from server.store import NotFound, Store
from server.transcripts import API, TranscriptStore

DatasetLoader = Callable[[str, bool], Awaitable[list[Record]]]


@dataclass
class Services:
    """Everything the route handlers need; built by `server.app.create_app` and kept in app state."""

    store: Store
    checklists: ChecklistStore
    jobs: JobRunner
    profiles: dict[str, Profile]
    dataset_loader: DatasetLoader
    transcripts: TranscriptStore
    _datasets: dict[str, list[Record]] = field(default_factory=dict)
    _dataset_locks: defaultdict[str, asyncio.Lock] = field(default_factory=lambda: defaultdict(asyncio.Lock))

    async def group_record(self, group_id: str, cid: str) -> Record:
        """The organizer record of a conversation in a group; `NotFound` if absent."""
        for r in await self.records(group_id):
            if r.conversation_id == cid:
                return r
        raise NotFound(f'диалог {cid} не найден в группе {group_id}')

    async def record_for(self, group_id: str, cid: str, source: str = API) -> Record:
        """The conversation's record for a transcript source (`api` = organizer's)."""
        base = await self.group_record(group_id, cid)
        if source == API:
            return base
        record = await self.transcripts.load(cid, source)
        if record is None:
            raise NotFound(f'транскрипт «{source}» для диалога {cid} не найден')
        # Seeded files carry a redacted audio URL (its `sig=` is secret); playback uses the live one.
        return record.model_copy(update={'audio_url': base.audio_url})

    async def records(self, group_id: str, refresh: bool = False) -> list[Record]:
        """Dataset records, cached in memory per group; `refresh` reloads. A failed load keeps the cache."""
        async with self._dataset_locks[group_id]:
            if refresh or group_id not in self._datasets:
                self._datasets[group_id] = await self.dataset_loader(group_id, refresh)
            return self._datasets[group_id]

    async def recorded_checklist(self, ev: Evaluation) -> Checklist:
        """The checklist version the evaluation was made with, not the latest one."""
        return await self.checklists.get(ev.checklist_id, ev.checklist_version)

    async def final(self, ev: Evaluation, appeals: list[Appeal] | None = None) -> FinalResult:
        if appeals is None:
            appeals = await self.store.appeals_for(ev.id)
        return final_result(await self.recorded_checklist(ev), ev, appeals)

    async def summary(self, ev: Evaluation) -> EvaluationSummary:
        final = await self.final(ev)
        return EvaluationSummary(
            id=ev.id,
            checklist_id=ev.checklist_id,
            checklist_version=ev.checklist_version,
            total=ev.score.total,
            final_total=final.score.total,
            gross_error=final.score.gross_error,
            created_at=ev.created_at,
        )


def provide_services(state: State) -> Services:
    return state.services


Svc = NamedDependency[Services]
"""Handler parameter type: `svc: Svc` injects the app's `Services`."""
