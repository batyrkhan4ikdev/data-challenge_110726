"""Human-arbitration queue: which (dialog, criterion) cells of the LLM-labelled gold deserve a human look first.

    python -m bench.arbitration_queue [--top 40]

Priority = committee entropy (bits) x criterion weight x scale distance, over the 4 labeling runs in
`bench/gold/calibration/round2/runs/` (+ the consensus verdict shown for context). Scale distance is
(max - min step of the votes) / (full scale span); yes/no and N/A-vs-value splits count as 1.
Cells with a human `gold_verdict` (any `labels.<login>*.csv` except the consensus file) are skipped.
Order is deterministic: priority desc, then dialog id, then criterion id. Writes
`bench/gold/arbitration_queue.csv` (top N) and prints the top 10.
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import Counter, defaultdict
from pathlib import Path

from bench import metrics
from bench.prefill import CONSENSUS, GOLD_DIR
from bench.sets import checklist_for, load_records

RUNS = GOLD_DIR / "calibration" / "round2" / "runs"
OUT = GOLD_DIR / "arbitration_queue.csv"
_WORDS = {"да": "yes", "нет": "no", "n/a": "na"}


def _norm(raw: str) -> str:
    raw = raw.strip()
    return _WORDS.get(raw.lower(), raw)


def committee_votes() -> dict[tuple[str, str], list[str]]:
    votes: dict[tuple[str, str], list[str]] = defaultdict(list)
    for path in sorted(RUNS.glob("*/*.csv")):
        with path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f, delimiter=";"):
                if row.get("conversation_id") and row.get("оценка"):
                    votes[(row["conversation_id"], row["criterion_id"])].append(_norm(row["оценка"]))
    return votes


def human_cells() -> set[tuple[str, str]]:
    cells: set[tuple[str, str]] = set()
    for path in sorted(GOLD_DIR.glob("labels.*.csv")):
        if path.name == CONSENSUS:
            continue
        with path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if (row.get("gold_verdict") or "").strip():
                    cells.add((row["conversation_id"], row["criterion_id"]))
    return cells


def consensus_verdicts() -> dict[tuple[str, str], str]:
    with (GOLD_DIR / CONSENSUS).open(encoding="utf-8-sig", newline="") as f:
        return {(r["conversation_id"], r["criterion_id"]): r["gold_verdict"].strip() for r in csv.DictReader(f)}


def entropy(votes: list[str]) -> float:
    n = len(votes)
    return -sum(c / n * math.log2(c / n) for c in Counter(votes).values())


def scale_distance(votes: list[str], steps: list[int] | None) -> float:
    if "na" in votes and len(set(votes)) > 1:
        return 1.0
    if not steps:
        return 1.0 if len(set(votes)) > 1 else 0.0
    nums = [int(v) for v in votes if v != "na"]
    span = max(steps) - min(steps)
    return (max(nums) - min(nums)) / span if nums and span else 0.0


def build_queue() -> list[dict]:
    records = load_records()
    votes = committee_votes()
    skip = human_cells()
    consensus = consensus_verdicts()
    rows = []
    for (cid, crit), vs in votes.items():
        if (cid, crit) in skip or cid not in records:
            continue
        criterion = next((c for c in checklist_for(records[cid]).criteria if c.id == crit), None)
        if criterion is None:
            continue
        steps = [s.value for s in criterion.steps] if criterion.answer_type == "scale" and criterion.steps else None
        h = entropy(vs)
        weight = metrics._weight(criterion)  # noqa: SLF001
        dist = scale_distance(vs, steps)
        priority = h * weight * dist
        if priority <= 0:
            continue
        rows.append(
            {
                "conversation_id": cid,
                "criterion_id": crit,
                "priority": round(priority, 4),
                "entropy": round(h, 4),
                "weight": weight,
                "scale_distance": round(dist, 4),
                "votes": " ".join(f"{k}:{n}" for k, n in sorted(Counter(vs).items())),
                "consensus": consensus.get((cid, crit), ""),
            }
        )
    rows.sort(key=lambda r: (-r["priority"], r["conversation_id"], r["criterion_id"]))
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--top", type=int, default=40)
    args = ap.parse_args(argv)
    queue = build_queue()[: args.top]
    cols = ["rank", "conversation_id", "criterion_id", "priority", "entropy", "weight", "scale_distance", "votes", "consensus"]
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for i, r in enumerate(queue, 1):
            w.writerow({"rank": i, **r})
    print(f"{OUT}: {len(queue)} rows")
    for i, r in enumerate(queue[:10], 1):
        print(f"{i:>2}. {r['conversation_id']} {r['criterion_id']}  priority={r['priority']:.3f}  votes[{r['votes']}]  consensus={r['consensus']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
