"""Приоритет просмотра оценки (triage, issue #52).

Детерминированный ранжировщик по уже готовой оценке и фактам диалога, без LLM. Это не вероятность
ошибки и не меняет итог: официальный счёт считается только в `server/scoring.py`.
"""

import re
from typing import TYPE_CHECKING

from server.facts import dialog_facts
from server.models import Appeal, Attention, Checklist, Criterion, DialogFacts, Evaluation, Item, Record

if TYPE_CHECKING:
    from server.routes import Services

# Историческое согласие судьи с gold-разметкой по критериям (DEV, n=65, профиль h200-gemma, k=1):
# bench/results/20261107-213616/summary.md, таблица «Per criterion», колонка agree.
# Берём только критерии ниже 0.92: на остальных судья практически не расходится с эталоном.
DEV_AGREE = {'c04': 0.862, 'c05': 0.908, 'c06': 0.785}

W_GROSS = 50
W_WARNING = 10
W_NA = 5
W_VOTES = 8
W_APPEAL = 20
W_FACT = 15
W_INTERIOR = 4

_GREETING = re.compile(
    r'здравств|добр(?:ый|ое|ого)|привет|сәлем|салем|қайырлы|кайырлы|hello|\bhi\b|good (?:morning|afternoon|evening)',
    re.IGNORECASE,
)


def _is_default(c: Criterion, verdict: str) -> bool:
    """Вердикт «как у большинства»: максимум шкалы или «yes». На нём согласие с эталоном не показательно."""
    if c.answer_type == 'scale':
        return verdict == str(max(s.value for s in c.steps or []))
    return verdict == 'yes'


def _first_operator_text(record: Record) -> str | None:
    for t in record.transcript:
        if t.speaker == 'operator':
            return t.text
    return None


def _fact_checks(
    checklist: Checklist, verdicts: dict[str, str], record: Record, facts: DialogFacts
) -> list[tuple[str, list[str]]]:
    """Расхождения «вердикт × факты»: (причина, затронутые критерии)."""
    ids = {c.id for c in checklist.criteria}
    out: list[tuple[str, list[str]]] = []
    first = _first_operator_text(record)
    if 'c01' in ids and verdicts.get('c01') == 'yes' and first is not None and not _GREETING.search(first):
        out.append(('c01 «да», но в первой реплике оператора нет приветствия', ['c01']))
    c06 = next((c for c in checklist.criteria if c.id == 'c06'), None)
    if c06 and facts.sla_ok is False and _is_default(c06, verdicts.get('c06', '')):
        out.append(('SLA первой реакции нарушен, а c06 оценён максимально', ['c06']))
    if 'c03' in ids and verdicts.get('c03') == 'no' and facts.identity_verified_idx is not None:
        out.append(('c03 «нет», но в диалоге есть отметка верификации клиента', ['c03']))
    return out


def attention(
    checklist: Checklist, ev: Evaluation, appeals: list[Appeal], record: Record | None
) -> Attention:
    """Балл приоритета (0–100) и причины; `criterion_ids` — критерии с причиной (спорные)."""
    found: list[tuple[int, str]] = []
    disputed: set[str] = set()

    def add(weight: int, reason: str, cids: list[str]) -> None:
        found.append((weight, reason))
        disputed.update(cids)

    if ev.score.gross_error:
        gross = [c.id for c in checklist.criteria if c.kind == 'gross_error']
        add(W_GROSS, 'Зафиксирована грубая ошибка', gross)

    by_id = {c.id: c for c in checklist.criteria}
    for it in sorted(ev.items, key=lambda i: i.criterion_id):
        c = by_id.get(it.criterion_id)
        if c is None:
            continue
        _item_signals(c, it, add)

    open_by_crit = sorted({a.criterion_id for a in appeals if a.status == 'open'})
    for cid in open_by_crit:
        add(W_APPEAL, f'Открыта апелляция по {cid}', [cid])

    if record is not None:
        verdicts = {i.criterion_id: i.verdict for i in ev.items}
        for reason, cids in _fact_checks(checklist, verdicts, record, dialog_facts(record)):
            add(W_FACT, reason, cids)

    found.sort(key=lambda x: -x[0])  # стабильная сортировка: при равных весах порядок добавления
    return Attention(
        score=min(100, sum(w for w, _ in found)),
        reasons=[r for _, r in found],
        criterion_ids=sorted(disputed),
    )


def _item_signals(c: Criterion, it: Item, add) -> None:
    cid = c.id
    if it.warnings:
        add(W_WARNING, f'{cid}: принят без подтверждения (фолбэк доказательств)', [cid])
    if it.verdict == 'na' and c.na_allowed:
        add(W_NA, f'{cid}: решение «неприменимо»', [cid])
    votes = [v for v, n in sorted(it.votes.items()) if n > 0]
    if len(votes) > 1:
        add(W_VOTES, f'{cid}: голоса прогонов расходятся ({"/".join(votes)})', [cid])
    agree = DEV_AGREE.get(cid)
    if agree is not None and it.verdict != 'na' and not _is_default(c, it.verdict):
        add(max(1, round((1 - agree) * 50)), f'{cid}: исторически низкое согласие с эталоном ({agree:.0%})', [cid])
    if c.answer_type == 'scale' and it.verdict != 'na':
        values = sorted(s.value for s in c.steps or [])
        if values and int(it.verdict) not in (values[0], values[-1]):
            add(W_INTERIOR, f'{cid}: оценка между ступенями шкалы, соседний балл возможен', [cid])


async def evaluation_attention(svc: 'Services', ev: Evaluation, record: Record | None = None) -> Attention:
    """Приоритет оценки из хранилища; `record` — запись группы (если уже загружена)."""
    from server.store import NotFound

    checklist = await svc.recorded_checklist(ev)
    appeals = await svc.store.appeals_for(ev.id)
    if ev.transcript_source != 'api':
        try:
            record = await svc.record_for(ev.group_id, ev.conversation_id, ev.transcript_source)
        except NotFound:
            pass
    if record is None:
        try:
            record = await svc.group_record(ev.group_id, ev.conversation_id)
        except NotFound:
            record = None
    return attention(checklist, ev, appeals, record)
