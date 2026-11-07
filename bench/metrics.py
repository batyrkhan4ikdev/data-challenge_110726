"""Agreement metrics between predicted and gold verdicts. Pure functions."""

from __future__ import annotations

from collections import Counter
from typing import Mapping

from server.models import Checklist, Record
from server.scoring import compute_score

Verdicts = Mapping[str, Mapping[str, str]]


def _weight(criterion) -> float:
    return 1.0 if criterion.kind == "gross_error" else float(criterion.weight)


def weighted_agreement(pred: Verdicts, gold: Verdicts, checklist: Checklist) -> float:
    agree = total = 0.0
    for cid in pred.keys() & gold.keys():
        for c in checklist.criteria:
            if c.id not in pred[cid] or c.id not in gold[cid]:
                continue
            w = _weight(c)
            total += w
            if pred[cid][c.id] == gold[cid][c.id]:
                agree += w
    return agree / total if total else float("nan")


def _pairs(pred_totals, gold_totals):
    return [
        (pred_totals[k], gold_totals[k])
        for k in pred_totals.keys() & gold_totals.keys()
        if pred_totals[k] is not None and gold_totals[k] is not None
    ]


def total_mae(pred_totals: Mapping[str, float | None], gold_totals: Mapping[str, float | None]) -> float:
    pairs = _pairs(pred_totals, gold_totals)
    if not pairs:
        return float("nan")
    return sum(abs(p - g) for p, g in pairs) / len(pairs)


def total_bias(pred_totals: Mapping[str, float | None], gold_totals: Mapping[str, float | None]) -> float:
    pairs = _pairs(pred_totals, gold_totals)
    if not pairs:
        return float("nan")
    return sum(p - g for p, g in pairs) / len(pairs)


def none_mismatches(pred_totals: Mapping[str, float | None], gold_totals: Mapping[str, float | None]) -> int:
    """Dialogs where exactly one of pred/gold total is None."""
    return sum(
        1
        for k in pred_totals.keys() & gold_totals.keys()
        if (pred_totals[k] is None) != (gold_totals[k] is None)
    )


def per_criterion_agreement(pred: Verdicts, gold: Verdicts, checklist: Checklist) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for c in checklist.criteria:
        pairs = [
            (pred[cid][c.id], gold[cid][c.id])
            for cid in pred.keys() & gold.keys()
            if c.id in pred[cid] and c.id in gold[cid]
        ]
        n = len(pairs)
        if n == 0:
            out[c.id] = {"agree": float("nan"), "majority_baseline": float("nan"), "n": 0}
            continue
        agree = sum(p == g for p, g in pairs) / n
        majority = max(Counter(g for _, g in pairs).values()) / n
        out[c.id] = {"agree": agree, "majority_baseline": majority, "n": n}
    return out


def cohen_kappa(a: list[str], b: list[str]) -> float | None:
    n = len(a)
    if n == 0 or n != len(b):
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in ca.keys() | cb.keys()) / (n * n)
    if pe == 1:
        return None
    return (po - pe) / (1 - pe)


def quadratic_weighted_kappa(a: list[int], b: list[int], levels: list[int]) -> float | None:
    n = len(a)
    if n == 0 or n != len(b) or len(levels) < 2:
        return None
    levels = sorted(levels)
    pos = {v: i for i, v in enumerate(levels)}
    size = len(levels)
    observed = [[0.0] * size for _ in range(size)]
    for x, y in zip(a, b):
        observed[pos[x]][pos[y]] += 1
    ha = [sum(row) for row in observed]
    hb = [sum(observed[i][j] for i in range(size)) for j in range(size)]
    num = den = 0.0
    for i in range(size):
        for j in range(size):
            w = (i - j) ** 2 / (size - 1) ** 2
            num += w * observed[i][j]
            den += w * ha[i] * hb[j] / n
    if den == 0:
        return None
    return 1 - num / den


def na_confusion(pred: Verdicts, gold: Verdicts, cid: str) -> dict[str, int]:
    tp = fp = fn = tn = 0
    for conv in pred.keys() & gold.keys():
        if cid not in pred[conv] or cid not in gold[conv]:
            continue
        p, g = pred[conv][cid] == "na", gold[conv][cid] == "na"
        if p and g:
            tp += 1
        elif p:
            fp += 1
        elif g:
            fn += 1
        else:
            tn += 1
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def gross_pr(pred: Verdicts, gold: Verdicts, cid: str) -> dict:
    tp = fp = fn = 0
    for conv in pred.keys() & gold.keys():
        if cid not in pred[conv] or cid not in gold[conv]:
            continue
        p, g = pred[conv][cid] == "yes", gold[conv][cid] == "yes"
        tp += p and g
        fp += p and not g
        fn += g and not p
    return {
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "support": tp + fn,
    }


def by_slice(
    pred: Verdicts,
    gold: Verdicts,
    records: Mapping[str, Record],
    checklist: Checklist,
    key: str,
) -> dict[str, float]:
    """Weighted agreement grouped by record.language or record.channel."""
    groups: dict[str, list[str]] = {}
    for cid in pred.keys() & gold.keys():
        if cid in records:
            groups.setdefault(getattr(records[cid], key), []).append(cid)
    return {
        value: weighted_agreement(
            {c: pred[c] for c in cids}, {c: gold[c] for c in cids}, checklist
        )
        for value, cids in sorted(groups.items())
    }


def gold_totals(
    gold_verdicts: Verdicts, checklists_by_cid: Mapping[str, Checklist]
) -> dict[str, float | None]:
    """Totals for dialogs whose gold covers every criterion of their checklist."""
    out: dict[str, float | None] = {}
    for cid, verdicts in gold_verdicts.items():
        checklist = checklists_by_cid.get(cid)
        if checklist is None or {c.id for c in checklist.criteria} != set(verdicts):
            continue
        out[cid] = compute_score(checklist, dict(verdicts)).total
    return out
