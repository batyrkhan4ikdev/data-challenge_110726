"""Verified counterfactual recourse: «как было бы правильно».

The judge proposes a minimal edit of the OPERATOR turns for one lost criterion; the edited dialog is judged again
on that single criterion through the official evaluation path (`evaluate`, per-criterion, same checklist version).
The result is coaching only: it is cached under `<store>/recourse/` and never stored as an evaluation.
"""

import asyncio
import json
from collections import defaultdict
from pathlib import Path

from pydantic import BaseModel

from server.config import Profile
from server.evaluator.run import evaluate
from server.llm.client import LLMClient, make_client
from server.models import Checklist, Criterion, Evaluation, Record, Turn
from server.store import NotFound, _safe, atomic_write

MAX_EDITS = 2
GROSS = 'Для критерия «грубая ошибка» разбор «как было бы правильно» не строится'
NO_LOSS = 'По этому критерию баллы не потеряны'

_SYSTEM = """\
Ты — наставник операторов контакт-центра Freedom Broker. Критерий чек-листа не выполнен. \
Предложи МИНИМАЛЬНУЮ правку диалога, после которой оператор выполнил бы критерий.

Правила
1. Правишь ТОЛЬКО реплики оператора (speaker = operator): заменить текст существующей реплики оператора (idx) \
или вставить новую реплику оператора после реплики с номером insert_after. Не больше двух правок.
2. Реплики клиента, бота и системные не трогай и не пересказывай.
3. Не выдумывай факты о клиенте, счёте, ценах и сроках. Всё, чего нет в диалоге, пиши плейсхолдером в квадратных \
скобках: «[сумма]», «[срок]», «[номер заявки]».
4. Пиши на языке диалога, в стиле остальных реплик оператора, коротко.
5. В каждой правке заполнен ровно один из idx / insert_after, второй равен null.
6. rationale — 1–2 предложения по-русски: что именно было не так и что исправлено.
Верни только JSON-объект по схеме."""

SCHEMA = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'edits': {
            'type': 'array',
            'maxItems': MAX_EDITS,
            'items': {
                'type': 'object',
                'additionalProperties': False,
                'properties': {
                    'idx': {'type': ['integer', 'null']},
                    'insert_after': {'type': ['integer', 'null']},
                    'new_text': {'type': 'string'},
                },
                'required': ['idx', 'insert_after', 'new_text'],
            },
        },
        'rationale': {'type': 'string'},
    },
    'required': ['edits', 'rationale'],
}


class Edit(BaseModel):
    idx: int | None = None
    insert_after: int | None = None
    new_text: str


class Verdict(BaseModel):
    verdict: str
    points: float | None
    max_points: float


class Recourse(BaseModel):
    evaluation_id: str
    criterion_id: str
    edits: list[Edit]
    rationale: str
    before: Verdict
    after: Verdict
    verified: bool
    note: str = 'Подсказка для оператора. В оценку не входит.'
    seconds: float = 0.0


class RecourseRequest(BaseModel):
    criterion_id: str


def _user(record: Record, c: Criterion, explanation: str, evidence: list[int]) -> str:
    turns = [
        f'[{t.idx}] {t.speaker}: {" ".join(t.text.splitlines())}'
        for t in record.transcript
    ]
    return '\n'.join([
        f'Язык диалога: {record.language}; канал: {record.channel}',
        f'Критерий {c.id}: {c.title}',
        f'Описание: {c.description}',
        f'Почему не выполнен: {explanation}',
        f'Реплики-основание: {evidence}' if evidence else '',
        '',
        'Транскрипт:',
        *turns,
        '',
        'Верни JSON: {"edits": [...], "rationale": "..."}',
    ])


def validate_edits(record: Record, raw: object) -> tuple[list[Edit], str]:
    """Parse the proposal and enforce: at most 2 edits, operator turns only, one of idx / insert_after."""
    if not isinstance(raw, dict) or not isinstance(raw.get('edits'), list):
        raise ValueError('модель вернула правки в неверном формате')
    by_idx = {t.idx: t for t in record.transcript}
    edits = [Edit.model_validate(e) for e in raw['edits']]
    if len(edits) > MAX_EDITS:
        raise ValueError(f'модель предложила больше {MAX_EDITS} правок')
    seen: set[int] = set()
    for e in edits:
        if (e.idx is None) == (e.insert_after is None):
            raise ValueError('в правке должно быть заполнено ровно одно из idx / insert_after')
        if not e.new_text.strip():
            raise ValueError('пустой текст правки')
        if e.idx is not None:
            turn = by_idx.get(e.idx)
            if turn is None or turn.speaker != 'operator':
                raise ValueError(f'реплика {e.idx} не принадлежит оператору')
            if e.idx in seen:
                raise ValueError(f'реплика {e.idx} правится дважды')
            seen.add(e.idx)
        elif e.insert_after not in by_idx:
            raise ValueError(f'нет реплики {e.insert_after} для вставки')
    return edits, str(raw.get('rationale') or '')


def apply_edits(record: Record, edits: list[Edit]) -> Record:
    """Replace / insert operator turns; every other turn is copied unchanged. Indexes stay contiguous."""
    replace = {e.idx: e.new_text.strip() for e in edits if e.idx is not None}
    inserts: dict[int, list[str]] = defaultdict(list)
    for e in edits:
        if e.insert_after is not None:
            inserts[e.insert_after].append(e.new_text.strip())
    first = record.transcript[0].idx if record.transcript else 0
    out: list[Turn] = []
    for t in record.transcript:
        out.append(t.model_copy(update={'text': replace[t.idx]}) if t.idx in replace else t)
        for text in inserts.get(t.idx, []):
            out.append(Turn(idx=0, timestamp=t.timestamp, offset_s=t.offset_s, speaker='operator', text=text))
    out = [t.model_copy(update={'idx': first + i}) for i, t in enumerate(out)]
    return record.model_copy(update={'transcript': out})


def _verdict(ev_score_items: list, cid: str) -> Verdict:
    it = next(i for i in ev_score_items if i.criterion_id == cid)
    return Verdict(verdict=it.verdict, points=it.points, max_points=it.max_points)


def _better(before: Verdict, after: Verdict) -> bool:
    return after.points is not None and before.points is not None and after.points > before.points


class RecourseService:
    def __init__(self, root: Path) -> None:
        self.dir = Path(root) / 'recourse'
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def _path(self, evaluation_id: str, criterion_id: str) -> Path:
        return self.dir / f'{_safe(evaluation_id)}__{_safe(criterion_id)}.json'

    def cached(self, evaluation_id: str, criterion_id: str) -> Recourse | None:
        try:
            return Recourse.model_validate_json(self._path(evaluation_id, criterion_id).read_text(encoding='utf-8'))
        except FileNotFoundError:
            return None

    async def run(
        self,
        ev: Evaluation,
        checklist: Checklist,
        record: Record,
        criterion_id: str,
        profile: Profile,
        llm: LLMClient | None = None,
    ) -> Recourse:
        c = next((c for c in checklist.criteria if c.id == criterion_id), None)
        if c is None:
            raise NotFound(f'критерий {criterion_id} отсутствует в чек-листе {checklist.id} версии {checklist.version}')
        if c.kind == 'gross_error' or c.id == 'c08':
            raise ValueError(GROSS)
        before = _verdict(ev.score.items, criterion_id)
        if before.points is None or before.points >= before.max_points:
            raise ValueError(NO_LOSS)
        async with self._locks[f'{ev.id}/{criterion_id}']:
            hit = await asyncio.to_thread(self.cached, ev.id, criterion_id)
            if hit is not None:
                return hit
            result = await self._compute(ev, checklist, record, c, before, profile, llm)
            await asyncio.to_thread(
                atomic_write, self._path(ev.id, criterion_id), result.model_dump_json(indent=2)
            )
            return result

    async def _compute(
        self,
        ev: Evaluation,
        checklist: Checklist,
        record: Record,
        c: Criterion,
        before: Verdict,
        profile: Profile,
        llm: LLMClient | None,
    ) -> Recourse:
        import time

        t0 = time.perf_counter()
        item = next(i for i in ev.items if i.criterion_id == c.id)
        proposer = llm
        if proposer is None:
            base = profile.member_profiles()[0][0] if profile.provider == 'ensemble' else profile
            proposer = make_client(base)
        messages = [
            {'role': 'system', 'content': _SYSTEM},
            {'role': 'user', 'content': _user(record, c, item.explanation, item.evidence_idx)},
        ]
        edits: list[Edit] = []
        rationale = ''
        error: Exception | None = None
        for _ in range(2):
            out = await proposer.complete(messages, SCHEMA, 0.0, 1)
            try:
                text = out[0].text or ''
                start, end = text.find('{'), text.rfind('}')
                edits, rationale = validate_edits(record, json.loads(text[start : end + 1]))
                error = None
                break
            except (ValueError, IndexError) as e:  # json.JSONDecodeError is a ValueError
                error = e
                messages = messages + [
                    {'role': 'user', 'content': f'Предыдущий ответ невалиден: {e}. Исправь и верни JSON.'}
                ]
        if error is not None:
            raise ValueError(f'не удалось получить правки от модели: {error}')
        if not edits:
            return Recourse(
                evaluation_id=ev.id, criterion_id=c.id, edits=[], rationale=rationale or 'Модель не предложила правок',
                before=before, after=before, verified=False, seconds=time.perf_counter() - t0,
            )
        edited = apply_edits(record, edits)
        # Same path as official scoring: per-criterion call on a checklist narrowed to this one criterion
        # (same version, sections and notes), so the prompt block is the one used for the real evaluation.
        narrow = checklist.model_copy(update={'criteria': [c]})
        judged, _ = await evaluate(edited, narrow, profile=profile, mode='per_criterion', k=ev.k, llm=llm)
        after = _verdict(judged.score.items, c.id)
        return Recourse(
            evaluation_id=ev.id, criterion_id=c.id, edits=edits, rationale=rationale,
            before=before, after=after, verified=_better(before, after), seconds=time.perf_counter() - t0,
        )
