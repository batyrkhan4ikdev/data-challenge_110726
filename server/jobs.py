import asyncio
import os
from typing import cast, get_args
from uuid import uuid4

from server.checklists import ChecklistStore
from server.config import Profile
from server.evaluator import evaluate
from server.models import BatchRequest, Checklist, Job, Mode, Record
from server.store import NotFound, Store

NOT_IN_GROUP = 'диалог не найден в группе'


def resolve_settings(req: BatchRequest, profiles: dict[str, Profile]) -> tuple[Profile, Mode, int]:
    """Profile, mode and k from the request, else from env `LLM_PROFILE` / `EVAL_MODE` / `EVAL_K`."""
    name = req.profile or os.environ.get('LLM_PROFILE') or 'fake'
    if name not in profiles:
        raise ValueError(f'неизвестный профиль модели {name!r}; доступны: {", ".join(profiles)}')
    mode = req.mode or os.environ.get('EVAL_MODE') or 'single'
    if mode not in get_args(Mode):
        raise ValueError(f'неизвестный режим {mode!r}; доступны: {", ".join(get_args(Mode))}')
    raw_k = req.k if req.k is not None else os.environ.get('EVAL_K') or 1
    try:
        k = int(raw_k)
    except ValueError:
        raise ValueError(f'k должно быть целым числом, указано {raw_k!r}') from None
    if k < 1:
        raise ValueError(f'k должно быть ≥ 1, указано {k}')
    return profiles[name], cast(Mode, mode), k


def fallback_names(value: str | None, profiles: dict[str, Profile]) -> list[str]:
    """Parse a comma-separated fallback chain (env `FALLBACK_PROFILE`); unknown names are a `ValueError`."""
    names = [n.strip() for n in (value or '').split(',') if n.strip()]
    unknown = [n for n in names if n not in profiles]
    if unknown:
        raise ValueError(f'неизвестные fallback-профили {unknown}; доступны: {", ".join(profiles)}')
    return names


class JobRunner:
    """In-memory batch jobs. Each job pins its checklist versions at start.

    A dialog that fails on the job's profile is retried on each `fallbacks` profile in order, so a dead
    endpoint or a rate-limited gateway costs a slower answer, not a failed dialog (UI and batch CLI alike).
    """

    def __init__(
        self, store: Store, checklists: ChecklistStore, profiles: dict[str, Profile], fallbacks: list[str] | None = None
    ) -> None:
        self.store = store
        self.checklists = checklists
        self.profiles = profiles
        self.fallbacks = fallback_names(','.join(fallbacks or []), profiles)
        self._sem = asyncio.Semaphore(int(os.environ.get('EVAL_CONCURRENCY', 4)))
        self._jobs: dict[str, Job] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}

    async def start(self, req: BatchRequest, records: dict[str, Record]) -> Job:
        """Resolve settings and checklists, then evaluate in the background.

        Raises `ValueError` for a bad profile/mode/k and `NotFound` for an unknown checklist id.
        Ids missing from `records` are marked failed right away.
        """
        profile, mode, k = resolve_settings(req, self.profiles)
        ids = list(dict.fromkeys(req.conversation_ids))
        explicit = await self.checklists.get(req.checklist_id) if req.checklist_id else None
        by_channel: dict[str, Checklist] = {}
        plan: list[tuple[Record, Checklist]] = []
        job = Job(
            id=f'job-{uuid4().hex[:12]}', state='running', total=len(ids), done=0, failed={}, evaluation_ids=[]
        )
        for cid in ids:
            record = records.get(cid)
            if record is None:
                job.failed[cid] = NOT_IN_GROUP
                job.done += 1
                continue
            checklist = explicit
            if checklist is None:
                if record.channel not in by_channel:
                    by_channel[record.channel] = await self.checklists.default_for(record.channel)
                checklist = by_channel[record.channel]
            plan.append((record, checklist))
        self._jobs[job.id] = job
        self._tasks[job.id] = asyncio.create_task(self._run(job, plan, req.group_id, profile, mode, k))
        return job

    async def _run(
        self, job: Job, plan: list[tuple[Record, Checklist]], group_id: str, profile: Profile, mode: Mode, k: int
    ) -> None:
        chain = [profile, *(self.profiles[n] for n in self.fallbacks if n != profile.name)]

        async def one(record: Record, checklist: Checklist) -> None:
            async with self._sem:
                errors: list[str] = []
                try:
                    for p in chain:
                        try:
                            ev, raw = await evaluate(record, checklist, profile=p, mode=mode, k=k, group_id=group_id)
                        except Exception as e:
                            errors.append(f'{p.name}: {type(e).__name__}: {str(e)[:200]}')
                            continue
                        await self.store.save_evaluation(ev, raw)
                        job.evaluation_ids.append(ev.id)
                        return
                    job.failed[record.conversation_id] = ' | '.join(errors)
                finally:
                    job.done += 1

        try:
            await asyncio.gather(*(asyncio.create_task(one(r, c)) for r, c in plan))
        finally:
            job.state = 'finished'

    def get(self, job_id: str) -> Job:
        job = self._jobs.get(job_id)
        if job is None:
            raise NotFound(f'задача {job_id} не найдена')
        return job

    async def wait(self, job_id: str) -> Job:
        """Block until the job finishes; used by the batch CLI."""
        task = self._tasks.get(job_id)
        if task is not None:
            await task
        return self.get(job_id)
