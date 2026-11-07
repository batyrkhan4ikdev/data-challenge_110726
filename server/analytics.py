import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from server.models import (
    BreakdownRow,
    CriterionStat,
    DriftCriterion,
    DriftMetric,
    DriftReport,
    GroupAnalytics,
    HistogramBin,
    Record,
    Score,
)
from server.routes import Services

_CENT = Decimal('0.01')
DRIFT_MIN_N = 30
_PSI_BINS = 10
_PSI_EPS = 1e-4
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


def psi(expected: dict, actual: dict) -> float | None:
    """Population stability index over matching categories: sum((a - e) * ln(a / e)), zero shares floored at 1e-4."""
    ne, na = sum(expected.values()), sum(actual.values())
    if not ne or not na:
        return None
    total = 0.0
    for k in expected.keys() | actual.keys():
        e = max(expected.get(k, 0) / ne, _PSI_EPS)
        a = max(actual.get(k, 0) / na, _PSI_EPS)
        total += (a - e) * math.log(a / e)
    return total


def total_bin(total: float) -> int:
    """Ten equal-width bins over the 0..100 total; 100 falls into the last one."""
    return min(int(total // (100 / _PSI_BINS)), _PSI_BINS - 1)


def ks_statistic(a: list[float], b: list[float]) -> float | None:
    """Two-sample Kolmogorov-Smirnov D: max distance between the empirical CDFs."""
    if not a or not b:
        return None
    xs, ys = sorted(a), sorted(b)
    i = j = 0
    d = 0.0
    while i < len(xs) and j < len(ys):
        v = min(xs[i], ys[j])
        while i < len(xs) and xs[i] <= v:
            i += 1
        while j < len(ys) and ys[j] <= v:
            j += 1
        d = max(d, abs(i / len(xs) - j / len(ys)))
    return d


def ks_pvalue(d: float, n: int, m: int) -> float:
    """Asymptotic p-value: 2 * sum_{k>=1} (-1)^(k-1) exp(-2 k^2 lambda^2), lambda = D * sqrt(nm / (n + m))."""
    lam = d * math.sqrt(n * m / (n + m))
    if lam < 0.27:  # series has not converged and p is > 0.99999
        return 1.0
    p = 2 * sum((-1) ** (k - 1) * math.exp(-2 * k * k * lam * lam) for k in range(1, 101))
    return min(max(p, 0.0), 1.0)


def psi_verdict(value: float | None) -> str | None:
    if value is None:
        return None
    return 'stable' if value < 0.1 else 'watch' if value <= 0.25 else 'drift'


@dataclass
class _Sample:
    created_at: datetime
    total: float | None
    cats: dict[str, str]  # criterion_id -> verdict category ('na' when not applicable)


def _num(x: float) -> str:
    return f'{x:g}'


def _metric(base: list[_Sample], win: list[_Sample], cid: str | None) -> DriftMetric:
    if cid is None:
        b = [s.total for s in base if s.total is not None]
        w = [s.total for s in win if s.total is not None]
        value = psi(Counter(total_bin(x) for x in b), Counter(total_bin(x) for x in w))
        d = ks_statistic(b, w)
        return DriftMetric(
            psi=value, verdict=psi_verdict(value), ks=d, ks_p=ks_pvalue(d, len(b), len(w)) if d is not None else None,
            n_baseline=len(b), n_window=len(w),
        )
    b = [s.cats[cid] for s in base if cid in s.cats]
    w = [s.cats[cid] for s in win if cid in s.cats]
    value = psi(Counter(b), Counter(w))
    return DriftMetric(psi=value, verdict=psi_verdict(value), ks=None, ks_p=None, n_baseline=len(b), n_window=len(w))


def drift_report(
    base: list[_Sample], win: list[_Sample], mode: str, baseline_label: str, window_label: str, titles: dict[str, str]
) -> DriftReport:
    total = _metric(base, win, None)
    criteria = [DriftCriterion(criterion_id=cid, title=titles[cid], metric=_metric(base, win, cid)) for cid in sorted(titles)]
    return DriftReport(
        mode=mode,  # type: ignore[arg-type]
        baseline_label=baseline_label,
        window_label=window_label,
        min_n=DRIFT_MIN_N,
        enough_data=total.n_baseline >= DRIFT_MIN_N and total.n_window >= DRIFT_MIN_N,
        total=total,
        criteria=criteria,
    )


async def _samples(svc: Services, group_id: str) -> tuple[list[_Sample], dict[str, str]]:
    """Latest evaluation of every conversation in the group as (time, total, per-criterion category)."""
    out: list[_Sample] = []
    titles: dict[str, str] = {}
    for r in await svc.records(group_id):
        ev = await svc.store.latest_for_conversation(r.conversation_id, group_id)
        if ev is None:
            continue
        kinds = {c.id: c for c in (await svc.recorded_checklist(ev)).criteria}
        score = (await svc.final(ev)).score
        cats: dict[str, str] = {}
        for it in score.items:
            c = kinds.get(it.criterion_id)
            if c is None or c.kind == 'gross_error':
                continue
            titles.setdefault(it.criterion_id, c.title)
            cats[it.criterion_id] = 'na' if not it.applicable or it.points is None else _num(it.points)
        out.append(_Sample(ev.created_at, score.total, cats))
    return out, titles


async def group_drift(svc: Services, group_id: str, baseline: str | None) -> DriftReport:
    """Baseline group vs this group, or (no baseline) the earlier half vs the later half of this group's evaluations."""
    samples, titles = await _samples(svc, group_id)
    if baseline and baseline != group_id:
        base, base_titles = await _samples(svc, baseline)
        for k, v in base_titles.items():
            titles.setdefault(k, v)
        common = {k: v for k, v in titles.items() if k in base_titles and any(k in s.cats for s in samples)}
        return drift_report(base, samples, 'groups', baseline, group_id, common)
    ordered = sorted(samples, key=lambda s: s.created_at)
    half = len(ordered) // 2
    return drift_report(ordered[:half], ordered[half:], 'halves', f'{group_id}: первая половина', f'{group_id}: вторая половина', titles)


async def group_analytics(svc: Services, group_id: str, baseline: str | None = None) -> GroupAnalytics:
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
        drift=await group_drift(svc, group_id, baseline),
    )
