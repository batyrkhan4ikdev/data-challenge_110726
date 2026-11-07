"""Benchmark runner: evaluate a dialog set with one or more profiles and summarise."""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

from server.config import Profile, load_profiles
from server.evaluator import evaluate
from server.models import Checklist, Record

from bench import metrics
from bench.prefill import GoldError, load_gold
from bench.sets import all_ids, checklist_for, gold_ids, load_records, smoke_ids

RESULTS = Path(__file__).resolve().parent / "results"


def citation_ok_rate(evaluation, record: Record, checklist: Checklist) -> float | None:
    """Share of positive scored items whose evidence includes at least one operator turn."""
    criteria = {c.id: c for c in checklist.criteria}
    speakers = {t.idx: t.speaker for t in record.transcript}
    checked = ok = 0
    for item in evaluation.items:
        c = criteria[item.criterion_id]
        if c.kind != "scored" or item.verdict == "na":
            continue
        if c.answer_type == "yes_no" and item.verdict != "yes":
            continue
        checked += 1
        if any(speakers.get(i) == "operator" for i in item.evidence_idx):
            ok += 1
    return ok / checked if checked else None


async def run_profile(
    profile: Profile, ids: list[str], records: dict[str, Record], mode: str, k: int, concurrency: int
) -> list[dict]:
    first = records[ids[0]]
    try:  # warmup: not timed, result discarded
        await evaluate(first, checklist_for(first), profile=profile, mode=mode, k=1)
    except Exception as e:  # noqa: BLE001
        print(f"[{profile.name}] warmup failed: {e}", file=sys.stderr)

    sem = asyncio.Semaphore(concurrency)

    async def one(cid: str) -> dict:
        record = records[cid]
        checklist = checklist_for(record)
        row = {
            "conversation_id": cid,
            "channel": record.channel,
            "language": record.language,
            "ok": False,
            "error": None,
            "seconds": 0.0,
            "usage": None,
            "verdicts": {},
            "total": None,
            "gross_error": None,
            "citation_ok_rate": None,
            "warnings": 0,
        }
        async with sem:
            t0 = time.perf_counter()
            try:
                evaluation, _ = await evaluate(record, checklist, profile=profile, mode=mode, k=k)
            except Exception as e:  # noqa: BLE001
                row["error"] = f"{type(e).__name__}: {e}"
                row["seconds"] = time.perf_counter() - t0
                return row
            row["seconds"] = time.perf_counter() - t0
        row.update(
            ok=True,
            usage=evaluation.usage.model_dump(),
            verdicts={it.criterion_id: it.verdict for it in evaluation.items},
            total=evaluation.score.total,
            gross_error=evaluation.score.gross_error,
            citation_ok_rate=citation_ok_rate(evaluation, record, checklist),
            warnings=sum(bool(it.warnings) for it in evaluation.items),
        )
        return row

    return list(await asyncio.gather(*(one(cid) for cid in ids)))


def _p90(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(0.9 * len(ordered)))]


def _fmt(x) -> str:
    if x is None:
        return "—"
    if isinstance(x, float):
        return "nan" if x != x else f"{x:.3f}"
    return str(x)


def _cost(profile: Profile, row: dict) -> float | None:
    cost = profile.cost
    if cost is None:
        return None
    if cost.kind == "gpu":
        return cost.usd_per_hour * row["seconds"] / max(cost.concurrency, 1) / 3600
    u = row["usage"]
    return (
        u["prompt_tokens"] * cost.usd_per_mtok_in / 1e6
        + u["completion_tokens"] * cost.usd_per_mtok_out / 1e6
    )


def _table(rows: list[list]) -> list[str]:
    head, *body = rows
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(_fmt(c) for c in r) + " |" for r in body]
    return out


def gold_section(rows: list[dict], gold: dict[str, dict[str, str]], records: dict[str, Record]) -> list[str]:
    ok = [r for r in rows if r["ok"] and r["conversation_id"] in gold]
    pred = {r["conversation_id"]: {c: v for c, v in r["verdicts"].items() if c in gold[r["conversation_id"]]} for r in ok}
    gold = {r["conversation_id"]: gold[r["conversation_id"]] for r in ok}
    if not ok:
        return ["", "_Нет оценённых диалогов с gold-разметкой._"]
    checklists = {cid: checklist_for(records[cid]) for cid in gold}
    base = next(iter(checklists.values()))
    pred_totals = {r["conversation_id"]: r["total"] for r in ok}
    g_totals = metrics.gold_totals(gold, checklists)
    pred_totals_cmp = {c: pred_totals[c] for c in g_totals}

    lines = ["", "**Gold**", ""]
    lines += _table(
        [
            ["metric", "value"],
            ["dialogs", len(ok)],
            ["weighted_agreement", metrics.weighted_agreement(pred, gold, base)],
            ["total_mae", metrics.total_mae(pred_totals_cmp, g_totals)],
            ["total_bias", metrics.total_bias(pred_totals_cmp, g_totals)],
            ["total_none_mismatches", metrics.none_mismatches(pred_totals_cmp, g_totals)],
        ]
    )
    for key in ("language", "channel"):
        lines += ["", f"By {key}:", ""]
        slices = metrics.by_slice(pred, gold, records, base, key)
        lines += _table([[key, "weighted_agreement"]] + [[k, v] for k, v in slices.items()])

    per = metrics.per_criterion_agreement(pred, gold, base)
    lines += ["", "Per criterion:", ""]
    table = [["criterion", "n", "agree", "majority_baseline", "kappa", "na tp/fp/fn/tn", "gross P/R/support"]]
    for c in base.criteria:
        pairs = [
            (pred[d][c.id], gold[d][c.id]) for d in gold if c.id in pred[d] and c.id in gold[d]
        ]
        if c.answer_type == "scale":
            step_pairs = [(int(p), int(g)) for p, g in pairs if p != "na" and g != "na"]
            kappa = metrics.quadratic_weighted_kappa(
                [p for p, _ in step_pairs],
                [g for _, g in step_pairs],
                [s.value for s in c.steps or []],
            )
        else:
            kappa = metrics.cohen_kappa([p for p, _ in pairs], [g for _, g in pairs])
        na = metrics.na_confusion(pred, gold, c.id) if c.na_allowed else None
        gross = metrics.gross_pr(pred, gold, c.id) if c.kind == "gross_error" else None
        table.append(
            [
                c.id,
                per[c.id]["n"],
                per[c.id]["agree"],
                per[c.id]["majority_baseline"],
                kappa,
                "/".join(str(na[x]) for x in ("tp", "fp", "fn", "tn")) if na else None,
                "/".join(_fmt(gross[x]) for x in ("precision", "recall", "support")) if gross else None,
            ]
        )
    return lines + _table(table)


def summarise(
    profile: Profile,
    mode: str,
    k: int,
    rows: list[dict],
    records: dict[str, Record],
    gold: dict[str, dict[str, str]] | None,
) -> list[str]:
    done = [r for r in rows if r["ok"]]
    valid = 0
    for r in done:
        checklist = checklist_for(records[r["conversation_id"]])
        groups = 1 if mode == "single" else len(checklist.criteria)
        valid += r["usage"]["calls"] == groups
    secs = [r["seconds"] for r in rows]
    costs = [c for c in (_cost(profile, r) for r in done) if c is not None]
    table = [
        ["metric", "value"],
        ["dialogs", len(rows)],
        ["first_try_valid_rate", valid / len(done) if done else None],
        ["failure_rate", (len(rows) - len(done)) / len(rows)],
        ["mean_seconds", statistics.fmean(secs) if secs else None],
        ["p90_seconds", _p90(secs) if secs else None],
        ["mean_prompt_tokens", statistics.fmean(r["usage"]["prompt_tokens"] for r in done) if done else None],
        ["mean_completion_tokens", statistics.fmean(r["usage"]["completion_tokens"] for r in done) if done else None],
        ["cost_per_evaluation_usd", statistics.fmean(costs) if costs else None],
        [
            "citation_ok_rate",
            statistics.fmean(r["citation_ok_rate"] for r in done if r["citation_ok_rate"] is not None)
            if any(r["citation_ok_rate"] is not None for r in done)
            else None,
        ],
        [
            "evidence_fallback_rate",
            statistics.fmean(r.get("warnings", 0) / len(r["verdicts"]) for r in done) if done else None,
        ],
    ]
    lines = [f"## {profile.name} · {mode} · k={k}", ""] + _table(table)
    if gold is not None:
        lines += gold_section(rows, gold, records)
    return lines + [""]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--mode", default="single", choices=["single", "per_criterion"])
    parser.add_argument("--k", type=int, default=1)
    parser.add_argument("--set", dest="set_name", default="smoke", choices=["smoke", "gold", "all"])
    parser.add_argument("--gold", dest="gold_source", default="all", choices=["all", "human"],
                        help="gold rows: all (human over LLM consensus) or human only (skip labels.consensus.csv)")
    parser.add_argument("--n", type=int)
    parser.add_argument("--concurrency", type=int, default=8)
    args = parser.parse_args(argv)

    records = load_records()
    gold = None
    if args.set_name == "gold":
        try:
            gold = load_gold(human_only=args.gold_source == "human")
        except GoldError as e:
            print("\n".join(e.problems), file=sys.stderr)
            return 1
        assigned = gold_ids()
        ids = [i for i in assigned if i in gold] + [i for i in gold if i not in assigned]
        if not ids:
            print("нет заполненных gold_verdict", file=sys.stderr)
            return 1
    elif args.set_name == "smoke":
        ids = smoke_ids()
    else:
        ids = all_ids()
    if args.n:
        ids = ids[: args.n]

    profiles = load_profiles()
    names = [n for n in args.profiles.split(",") if n]
    unknown = [n for n in names if n not in profiles]
    if unknown:
        print(f"неизвестные профили: {unknown}", file=sys.stderr)
        return 1

    out_dir = RESULTS / datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = [f"# Benchmark · set={args.set_name} · gold={args.gold_source} · n={len(ids)}", ""]
    for name in names:
        profile = profiles[name]
        rows = asyncio.run(run_profile(profile, ids, records, args.mode, args.k, args.concurrency))
        path = out_dir / f"{name}-{args.mode}-k{args.k}.jsonl"
        path.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
        )
        summary += summarise(profile, args.mode, args.k, rows, records, gold)
        print(f"{path}: {sum(r['ok'] for r in rows)}/{len(rows)} ok")
    (out_dir / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(out_dir / "summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
