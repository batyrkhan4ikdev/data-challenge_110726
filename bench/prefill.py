"""Prefill gold labeling CSVs with a model's verdicts, and load filled gold labels."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from pathlib import Path

from server.config import load_profiles
from server.evaluator import evaluate
from server.scoring import allowed_verdicts

from bench.sets import checklist_for, load_records

GOLD_DIR = Path(__file__).resolve().parent / "gold"
COLUMNS = [
    "conversation_id",
    "criterion_id",
    "criterion_title",
    "allowed",
    "prefill_verdict",
    "prefill_evidence",
    "prefill_explanation",
    "gold_verdict",
    "gold_evidence",
    "note",
]


class GoldError(Exception):
    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


def _evidence(item) -> str:
    parts = [str(i) for i in item.evidence_idx]
    if item.expected_range:
        parts.append(f"{item.expected_range[0]}-{item.expected_range[1]}")
    return " ".join(parts)


def _has_gold(path: Path) -> bool:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return any((row.get("gold_verdict") or "").strip() for row in csv.DictReader(f))


async def _run(assignments: list[dict], override: str | None) -> dict[str, list[list[str]]]:
    profiles = load_profiles()
    records = load_records()
    sem = asyncio.Semaphore(8)

    async def one(a: dict) -> tuple[str, list[list[str]]]:
        record = records[a["conversation_id"]]
        checklist = checklist_for(record)
        profile = profiles[override or a["prefill_profile"]]
        items = {}
        failure = ""
        for attempt in range(3):
            try:
                async with sem:
                    evaluation, _ = await evaluate(record, checklist, profile=profile, mode="single", k=1)
                items = {it.criterion_id: it for it in evaluation.items}
                break
            except Exception as exc:  # network flakes must not abort the whole prefill
                failure = f"{type(exc).__name__}: {str(exc)[:200]}"
                await asyncio.sleep(2 * (attempt + 1))
        if not items:
            print(f"prefill failed for {record.conversation_id}: {failure}", file=sys.stderr)
        rows = []
        for c in checklist.criteria:
            it = items.get(c.id)
            rows.append(
                [
                    record.conversation_id,
                    c.id,
                    c.title,
                    "|".join(allowed_verdicts(c)),
                    it.verdict if it else "",
                    _evidence(it) if it else "",
                    it.explanation if it else "",
                    "",
                    "",
                    "" if it else "prefill не удался",
                ]
            )
        return a["labeler"], rows

    by_labeler: dict[str, list[list[str]]] = {}
    for labeler, rows in await asyncio.gather(*(one(a) for a in assignments)):
        by_labeler.setdefault(labeler, []).extend(rows)
    return by_labeler


CONSENSUS = "labels.consensus.csv"


def _label_files(directory: Path, human_only: bool = False) -> list[Path]:
    """LLM-consensus labels first, human per-labeler files after, so a filled human row always wins."""
    files = sorted(Path(directory).glob("labels.*.csv"))
    if human_only:
        return [p for p in files if p.name != CONSENSUS]
    return sorted(files, key=lambda p: p.name != CONSENSUS)


def load_gold(directory: Path = GOLD_DIR, human_only: bool = False) -> dict[str, dict[str, str]]:
    """Read every labels.*.csv; return {cid: {criterion: gold_verdict}} for filled rows.

    Human labels override `labels.consensus.csv` row by row; `human_only` skips the consensus file.
    Raises GoldError listing invalid rows as `file:line: reason`.
    """
    records = load_records()
    gold: dict[str, dict[str, str]] = {}
    problems: list[str] = []
    for path in _label_files(directory, human_only):
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                verdict = (row.get("gold_verdict") or "").strip()
                if not verdict:
                    continue
                line = reader.line_num
                where = f"{path.name}:{line}"
                cid, crit = row.get("conversation_id", ""), row.get("criterion_id", "")
                record = records.get(cid)
                if record is None:
                    problems.append(f"{where}: неизвестный диалог {cid!r}")
                    continue
                criterion = next((c for c in checklist_for(record).criteria if c.id == crit), None)
                if criterion is None:
                    problems.append(f"{where}: неизвестный критерий {crit!r}")
                    continue
                allowed = allowed_verdicts(criterion)
                if verdict not in allowed:
                    problems.append(f"{where}: {cid}/{crit} вердикт {verdict!r} не из {allowed}")
                    continue
                gold.setdefault(cid, {})[crit] = verdict
    if problems:
        raise GoldError(problems)
    return gold


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labeler")
    parser.add_argument("--profile-override", help="use this profile for every assignment (offline tests)")
    args = parser.parse_args(argv)

    assignments = json.loads((GOLD_DIR / "assignments.json").read_text(encoding="utf-8"))
    if args.labeler:
        assignments = [a for a in assignments if a["labeler"] == args.labeler]
    if not assignments:
        print("нет назначений", file=sys.stderr)
        return 1
    labelers = sorted({a["labeler"] for a in assignments})
    for labeler in labelers:
        path = GOLD_DIR / f"labels.{labeler}.csv"
        if path.exists() and _has_gold(path):
            print(f"{path} уже содержит gold_verdict; перезапись отменена", file=sys.stderr)
            return 1

    by_labeler = asyncio.run(_run(assignments, args.profile_override))
    for labeler, rows in by_labeler.items():
        path = GOLD_DIR / f"labels.{labeler}.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(COLUMNS)
            writer.writerows(rows)
        print(f"{path}: {len(rows)} строк")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
