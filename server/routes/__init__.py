import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from litestar.datastructures import State
from litestar.di import NamedDependency

from server.checklists import ChecklistStore
from server.config import Profile
from server.jobs import JobRunner
from server.models import Appeal, Checklist, DatasetStatus, Evaluation, EvaluationSummary, FinalResult, Record
from server.scoring import final_result
from server.store import NotFound, Store
from server.transcripts import API, TranscriptStore
from server.uploads import UPLOADS, UploadStore

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
    uploads: UploadStore
    records_wait_s: float = 3.0  # how long the dialog list waits for a running load before answering from the cache
    _datasets: dict[str, list[Record]] = field(default_factory=dict)
    _loads: dict[str, asyncio.Task[list[Record]]] = field(default_factory=dict)
    _status: dict[str, DatasetStatus] = field(default_factory=dict)

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
        """Dataset records, cached in memory per group; `refresh` reloads. A failed load keeps the cache.
        `UPLOADS` is read from the store every time: it changes with each upload. A plain read returns the cache at
        once, even while a refresh is fetching from the organizers' API (40+ s on this network)."""
        if group_id == UPLOADS:
            return await self.uploads.records()
        if not refresh and group_id in self._datasets:
            return self._datasets[group_id]
        return await asyncio.shield(self._start_load(group_id, refresh))

    async def records_for_list(self, group_id: str, refresh: bool) -> list[Record]:
        """For the dialog list: start the load in the background and wait at most `records_wait_s` for it. Past that, answer
        with what is cached (possibly nothing) and let the UI poll `status()` until the load ends."""
        if group_id == UPLOADS:
            return await self.uploads.records()
        if not refresh and group_id in self._datasets:
            return self._datasets[group_id]
        task = self._start_load(group_id, refresh)
        try:
            return await asyncio.wait_for(asyncio.shield(task), self.records_wait_s)
        except TimeoutError:
            return self._datasets.get(group_id, [])
        except Exception:
            if group_id in self._datasets:  # the error is in status(); the cached rows are still good
                return self._datasets[group_id]
            raise

    def status(self, group_id: str) -> DatasetStatus:
        st = self._status.get(group_id) or DatasetStatus(group_id=group_id, loading=False)
        cached = self._datasets.get(group_id)
        return st.model_copy(update={'count': len(cached) if cached is not None else None})

    def _start_load(self, group_id: str, refresh: bool) -> asyncio.Task[list[Record]]:
        """One load per group at a time: a second caller joins the running one."""
        task = self._loads.get(group_id)
        if task is not None and not task.done():
            return task
        task = asyncio.create_task(self._load(group_id, refresh))
        task.add_done_callback(lambda t: t.cancelled() or t.exception())  # an unawaited failure is kept in status
        self._loads[group_id] = task
        return task

    async def _load(self, group_id: str, refresh: bool) -> list[Record]:
        started = datetime.now(UTC)
        self._status[group_id] = DatasetStatus(group_id=group_id, loading=True, started_at=started)
        try:
            loaded = await self.dataset_loader(group_id, refresh)
        except Exception as e:
            self._status[group_id] = DatasetStatus(
                group_id=group_id, loading=False, started_at=started, finished_at=datetime.now(UTC),
                error=str(e) or type(e).__name__,
            )
            raise
        self._datasets[group_id] = loaded
        self._status[group_id] = DatasetStatus(
            group_id=group_id, loading=False, started_at=started, finished_at=datetime.now(UTC)
        )
        return loaded

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
