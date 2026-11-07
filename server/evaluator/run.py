import asyncio
import time
from datetime import UTC, datetime
from uuid import uuid4

from server.config import Profile
from server.evaluator.parse import parse_items
from server.evaluator.prompt import build_messages
from server.evaluator.schema import build_schema
from server.evaluator.vote import aggregate
from server.llm.client import Completion, LLMClient, make_client
from server.models import Checklist, Evaluation, Item, Mode, RawCall, Record, Usage
from server.scoring import compute_score

TRUNCATED = 'ответ обрезан или пуст'
NO_SAMPLES = 'модель не вернула ни одного ответа'


class EvaluationError(Exception):
    pass


def _describe(ids: list[str], errors: dict[str, str]) -> str:
    return '; '.join(f'{cid}: {errors.get(cid, NO_SAMPLES)}' for cid in ids)


async def evaluate(
    record: Record,
    checklist: Checklist,
    *,
    profile: Profile,
    mode: Mode = 'single',
    k: int = 1,
    llm: LLMClient | None = None,
    group_id: str = 'DEV',
) -> tuple[Evaluation, list[RawCall]]:
    if not record.transcript:
        raise EvaluationError('пустой транскрипт')
    if profile.provider == 'ensemble':
        return await _evaluate_ensemble(record, checklist, profile=profile, mode=mode, k=k, group_id=group_id)
    llm = llm or make_client(profile)
    temperature = 0.0 if k == 1 else 0.7
    evaluation_id = f'{record.conversation_id}-{uuid4().hex[:8]}'
    all_ids = [c.id for c in checklist.criteria]
    raw_calls: list[RawCall] = []
    completions: list[Completion] = []
    t0 = time.perf_counter()

    async def call(messages: list[dict], ids: list[str]) -> list[Completion]:
        started_at = datetime.now(UTC)
        t = time.perf_counter()
        result = await llm.complete(messages, build_schema(checklist, ids), temperature, k)
        raw_calls.append(
            RawCall(
                evaluation_id=evaluation_id,
                criterion_ids=ids,
                messages=messages,
                response_text='\n---\n'.join(c.text or '' for c in result),
                model=profile.model,
                started_at=started_at,
                seconds=time.perf_counter() - t,
            )
        )
        completions.extend(result)
        return result

    def collect(
        result: list[Completion], ids: list[str], lenient: bool = False
    ) -> tuple[dict[str, Item], dict[str, str]]:
        samples: list[dict[str, Item]] = []
        errors: dict[str, str] = {}
        for comp in result:
            if comp.text is None or comp.finish_reason == 'length':
                for cid in ids:
                    errors.setdefault(cid, TRUNCATED)
                continue
            items, errs = parse_items(comp.text, record, checklist, ids, lenient=lenient)
            samples.append(items)
            for cid, err in errs.items():
                errors.setdefault(cid, err)
        return aggregate(samples, checklist, ids), errors

    async def run_group(ids: list[str]) -> dict[str, Item]:
        messages = build_messages(record, checklist, ids)
        first = await call(messages, ids)
        items, errors = collect(first, ids)
        failed = [cid for cid in ids if cid not in items]
        if not failed:
            return items
        retry = messages + [
            {
                'role': 'user',
                'content': (
                    f'Предыдущий ответ невалиден: {_describe(failed, errors)}. '
                    f'Исправь и верни JSON только для: {", ".join(failed)}'
                ),
            }
        ]
        second = await call(retry, failed)
        retried, errors = collect(second, failed)
        items.update(retried)
        still = [cid for cid in failed if cid not in items]
        if still:
            # A missing citation must not cost the whole dialog: accept the verdict with a warning.
            fallback, _ = collect(second + first, still, lenient=True)
            items.update(fallback)
            still = [cid for cid in still if cid not in items]
        if still:
            raise EvaluationError(f'невалидный ответ модели после повтора: {_describe(still, errors)}')
        return items

    groups = [all_ids] if mode == 'single' else [[cid] for cid in all_ids]
    merged: dict[str, Item] = {}
    for part in await asyncio.gather(*(run_group(ids) for ids in groups)):
        merged.update(part)

    items = [merged[cid] for cid in all_ids]
    evaluation = Evaluation(
        id=evaluation_id,
        conversation_id=record.conversation_id,
        group_id=group_id,
        checklist_id=checklist.id,
        checklist_version=checklist.version,
        profile=profile.name,
        model=profile.model,
        mode=mode,
        k=k,
        created_at=datetime.now(UTC),
        items=items,
        score=compute_score(checklist, {it.criterion_id: it.verdict for it in items}),
        usage=Usage(
            prompt_tokens=sum(c.prompt_tokens for c in completions),
            completion_tokens=sum(c.completion_tokens for c in completions),
            calls=len(raw_calls),
            seconds=time.perf_counter() - t0,
        ),
    )
    return evaluation, raw_calls


async def _evaluate_ensemble(
    record: Record, checklist: Checklist, *, profile: Profile, mode: Mode, k: int, group_id: str
) -> tuple[Evaluation, list[RawCall]]:
    """Every member scores the dialog in its own mode; per criterion the majority wins, scales take the median.

    Ties go to the first member, which also supplies explanation and evidence whenever it agrees with the
    result. A member that fails is dropped with a warning on every item; if all fail, the dialog fails.
    """
    members = profile.member_profiles()
    t0 = time.perf_counter()
    results = await asyncio.gather(
        *(evaluate(record, checklist, profile=p, mode=m, k=k, group_id=group_id) for p, m in members),
        return_exceptions=True,
    )
    done: list[tuple[Evaluation, list[RawCall]]] = []
    lost: list[str] = []
    for (p, _), res in zip(members, results):
        if isinstance(res, BaseException):
            lost.append(f'{p.name}: {type(res).__name__}: {str(res)[:120]}')
        else:
            done.append(res)
    if not done:
        raise EvaluationError('ни один участник ансамбля не ответил: ' + ' | '.join(lost))

    all_ids = [c.id for c in checklist.criteria]
    merged = aggregate([{it.criterion_id: it for it in ev.items} for ev, _ in done], checklist, all_ids)
    warning = [f'ансамбль без {entry.split(":")[0]}' for entry in lost]
    items = [merged[cid].model_copy(update={'warnings': [*merged[cid].warnings, *warning]}) for cid in all_ids]

    evaluation_id = f'{record.conversation_id}-{uuid4().hex[:8]}'
    raw_calls = [rc.model_copy(update={'evaluation_id': evaluation_id}) for _, calls in done for rc in calls]
    evaluation = Evaluation(
        id=evaluation_id,
        conversation_id=record.conversation_id,
        group_id=group_id,
        checklist_id=checklist.id,
        checklist_version=checklist.version,
        profile=profile.name,
        model=profile.model,
        mode=mode,
        k=k,
        created_at=datetime.now(UTC),
        items=items,
        score=compute_score(checklist, {it.criterion_id: it.verdict for it in items}),
        usage=Usage(
            prompt_tokens=sum(ev.usage.prompt_tokens for ev, _ in done),
            completion_tokens=sum(ev.usage.completion_tokens for ev, _ in done),
            calls=sum(ev.usage.calls for ev, _ in done),
            seconds=time.perf_counter() - t0,
        ),
    )
    return evaluation, raw_calls
