"""Paired comparison of two bench runs against gold. Shared by the regression and holdout gates."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

from bench import metrics
from bench.sets import checklist_for, load_records


class RunError(Exception):
    pass


def run_file(path: str | Path) -> Path:
    """A `.jsonl` file, or a run directory holding exactly one."""
    p = Path(path)
    if p.is_file():
        return p
    files = sorted(p.glob("*.jsonl"))
    if len(files) != 1:
        raise RunError(f"{p}: ожидался один .jsonl, найдено {len(files)}; укажите файл явно")
    return files[0]


def load_run(path: str | Path) -> dict[str, dict[str, str]]:
    """{conversation_id: {criterion_id: verdict}} for successfully evaluated dialogs."""
    out: dict[str, dict[str, str]] = {}
    for line in run_file(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("ok") and row.get("verdicts"):
            out[row["conversation_id"]] = row["verdicts"]
    return out


@dataclass(frozen=True)
class Cell:
    """Weighted agreement mass of one dialog: `agree` of `total` checklist weight matches gold."""

    agree: float
    total: float


def dialog_cells(
    pred: dict[str, dict[str, str]], gold: dict[str, dict[str, str]]
) -> dict[str, Cell]:
    records = load_records()
    out: dict[str, Cell] = {}
    for cid in pred.keys() & gold.keys():
        agree = total = 0.0
        for c in checklist_for(records[cid]).criteria:
            if c.id not in pred[cid] or c.id not in gold[cid]:
                continue
            w = metrics._weight(c)  # noqa: SLF001
            total += w
            agree += w * (pred[cid][c.id] == gold[cid][c.id])
        if total:
            out[cid] = Cell(agree, total)
    return out


def wa(cells: dict[str, Cell], ids) -> float:
    ids = [i for i in ids if i in cells]
    total = sum(cells[i].total for i in ids)
    return sum(cells[i].agree for i in ids) / total if total else float("nan")


def paired_diff(
    base: dict[str, Cell], cand: dict[str, Cell], iterations: int = 2000, seed: int = 20261108
) -> dict:
    """WA of both runs on their common dialogs, the paired difference and a 95% bootstrap CI over dialogs."""
    ids = sorted(base.keys() & cand.keys())
    if not ids:
        raise RunError("нет общих диалогов с gold у двух прогонов")
    b, c = wa(base, ids), wa(cand, ids)
    rng = random.Random(seed)
    diffs = []
    for _ in range(iterations):
        sample = [ids[rng.randrange(len(ids))] for _ in ids]
        diffs.append(wa(cand, sample) - wa(base, sample))
    diffs.sort()
    return {
        "n": len(ids),
        "base": b,
        "cand": c,
        "diff": c - b,
        "ci_low": diffs[int(0.025 * iterations)],
        "ci_high": diffs[int(0.975 * iterations) - 1],
    }
