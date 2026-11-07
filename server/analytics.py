from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from server.models import BreakdownRow, CriterionStat, GroupAnalytics, HistogramBin, Record, Score
from server.routes import Services

_CENT = Decimal('0.01')
_BANDS = [('<50', 0, 50), ('50–70', 50, 70), ('70–85', 70, 85), ('85–100', 85, 1000)]


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    mean = sum((Decimal(str(v)) for v in values), Decimal(0)) / len(values)
    return float(mean.quantize(_CENT, rounding=ROUND_HALF_UP))


def _breakdown(groups: dict[str, list[float | None]]) -> list[BreakdownRow]:
    return [
        BreakdownRow(key=k, count=len(v), mean_total=_mean([x for x in v if x is not None]))
        for k, v in sorted(groups.items())
    ]


async def group_analytics(svc: Services, group_id: str) -> GroupAnalytics:
    """Aggregates the latest evaluation of every conversation in the group (totals and items after appeals)."""
    records: list[Record] = await svc.records(group_id)
    totals: list[float] = []
    gross_ids: list[str] = []
    by_channel: dict[str, list[float | None]] = defaultdict(list)
    by_language: dict[str, list[float | None]] = defaultdict(list)
    histogram = [0] * len(_BANDS)
    titles: dict[str, str] = {}
    counts: dict[str, dict[str, int]] = {}
    pct: dict[str, list[float]] = defaultdict(list)
    evaluated = 0

    for r in records:
        ev = await svc.store.latest_for_conversation(r.conversation_id, group_id)
        if ev is None:
            continue
        evaluated += 1
        checklist = await svc.recorded_checklist(ev)
        score: Score = (await svc.final(ev)).score
        by_channel[r.channel].append(score.total)
        by_language[r.language].append(score.total)
        if score.gross_error:
            gross_ids.append(r.conversation_id)
        if score.total is not None:
            totals.append(score.total)
            for i, (_, lo, hi) in enumerate(_BANDS):
                if lo <= score.total < hi:
                    histogram[i] += 1
                    break
        kinds = {c.id: c for c in checklist.criteria}
        for it in score.items:
            c = kinds.get(it.criterion_id)
            if c is None or c.kind == 'gross_error':
                continue
            titles.setdefault(it.criterion_id, c.title)
            bucket = counts.setdefault(it.criterion_id, {'yes': 0, 'no': 0, 'na': 0})
            if not it.applicable or it.points is None:
                bucket['na'] += 1
                continue
            bucket['yes' if it.points >= it.max_points else 'no'] += 1
            if it.max_points > 0:
                pct[it.criterion_id].append(it.points / it.max_points * 100)

    criteria = [
        CriterionStat(
            criterion_id=cid,
            title=titles[cid],
            applicable=b['yes'] + b['no'],
            yes=b['yes'],
            no=b['no'],
            na=b['na'],
            mean_pct=_mean(pct[cid]),
        )
        for cid, b in counts.items()
    ]
    return GroupAnalytics(
        group_id=group_id,
        dialogs=len(records),
        evaluated=evaluated,
        mean_total=_mean(totals),
        gross_error_count=len(gross_ids),
        gross_error_ids=gross_ids,
        by_channel=_breakdown(by_channel),
        by_language=_breakdown(by_language),
        criteria=criteria,
        histogram=[HistogramBin(label=b[0], count=n) for b, n in zip(_BANDS, histogram)],
    )
