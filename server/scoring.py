from decimal import ROUND_HALF_UP, Decimal

from server.models import (
    Appeal,
    Checklist,
    Criterion,
    Decision,
    Evaluation,
    FinalItem,
    FinalResult,
    Score,
    ScoreItem,
    SectionScore,
)

_CENT = Decimal('0.01')


def allowed_verdicts(c: Criterion) -> list[str]:
    if c.answer_type == 'yes_no':
        verdicts = ['yes', 'no']
    else:
        verdicts = [str(v) for v in sorted(s.value for s in c.steps or [])]
    if c.na_allowed:
        verdicts.append('na')
    return verdicts


def _points(c: Criterion, verdict: str) -> Decimal | None:
    if verdict == 'na':
        return None
    weight = Decimal(str(c.weight))
    if c.answer_type == 'yes_no':
        return weight if verdict == 'yes' else Decimal(0)
    max_step = max(s.value for s in c.steps or [])
    return Decimal(int(verdict)) / Decimal(max_step) * weight


def _total(points: list[Decimal], weight: Decimal) -> float | None:
    if weight == 0:
        return None
    return float((sum(points, Decimal(0)) / weight * 100).quantize(_CENT, rounding=ROUND_HALF_UP))


def compute_score(checklist: Checklist, verdicts: dict[str, str]) -> Score:
    ids = {c.id for c in checklist.criteria}
    unknown = sorted(set(verdicts) - ids)
    if unknown:
        raise ValueError(f'unknown criterion ids: {unknown}')
    missing = [c.id for c in checklist.criteria if c.id not in verdicts]
    if missing:
        raise ValueError(f'missing verdicts for: {missing}')

    gross = False
    scored: list[tuple[Criterion, str, Decimal | None]] = []
    for c in checklist.criteria:
        verdict = verdicts[c.id]
        if verdict not in allowed_verdicts(c):
            raise ValueError(f'{c.id}: verdict {verdict!r} not in {allowed_verdicts(c)}')
        if c.kind == 'gross_error':
            gross = gross or verdict == 'yes'
            scored.append((c, verdict, None))
        else:
            scored.append((c, verdict, _points(c, verdict)))

    def applicable(c: Criterion, p: Decimal | None) -> bool:
        return c.kind == 'scored' and p is not None

    weight = sum((Decimal(str(c.weight)) for c, _, p in scored if applicable(c, p)), Decimal(0))
    items = [
        ScoreItem(
            criterion_id=c.id,
            verdict=v,
            applicable=applicable(c, p),
            points=float(p) if p is not None else None,
            max_points=c.weight if c.kind == 'scored' else 0,
            effective_points=float(p / weight * 100) if p is not None and weight != 0 else None,
        )
        for c, v, p in scored
    ]
    sections = []
    for s in checklist.sections:
        sec = [(c, p) for c, _, p in scored if c.section_id == s.id and applicable(c, p)]
        sec_weight = sum((Decimal(str(c.weight)) for c, _ in sec), Decimal(0))
        sections.append(
            SectionScore(section_id=s.id, title=s.title, total=_total([p for _, p in sec], sec_weight))
        )
    return Score(
        total=_total([p for c, _, p in scored if applicable(c, p)], weight),
        sections=sections,
        gross_error=gross,
        applicable_weight=float(weight),
        items=items,
    )


def final_result(checklist: Checklist, evaluation: Evaluation, appeals: list[Appeal]) -> FinalResult:
    latest: dict[str, Decision] = {}
    for a in appeals:
        d = a.decision
        if a.status != 'resolved' or d is None:
            continue
        prev = latest.get(a.criterion_id)
        if prev is None or d.decided_at > prev.decided_at:
            latest[a.criterion_id] = d
    changes: dict[str, Decision] = {}
    for a in appeals:
        d = a.decision
        if a.status != 'resolved' or d is None or d.action != 'change':
            continue
        prev = changes.get(a.criterion_id)
        if prev is None or d.decided_at > prev.decided_at:
            changes[a.criterion_id] = d

    items = []
    for it in evaluation.items:
        change = changes.get(it.criterion_id)
        final = change.new_verdict if change is not None and change.new_verdict is not None else it.verdict
        items.append(
            FinalItem(
                criterion_id=it.criterion_id,
                original_verdict=it.verdict,
                decision=latest.get(it.criterion_id),
                final_verdict=final,
            )
        )
    score = compute_score(checklist, {i.criterion_id: i.final_verdict for i in items})
    return FinalResult(items=items, score=score)
