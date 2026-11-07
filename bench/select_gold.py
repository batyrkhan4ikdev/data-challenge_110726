"""Select 24 gold dialogs, assign them to labelers and render transcripts."""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from pathlib import Path

from bench.sets import ASSIGNMENTS, load_records, smoke_ids

LABELERS = ["arynyklas", "kakhotitee", "Batyrkhantzy111"]
PROFILES = ["h200-gptoss", "h200-gemma", "h200-kz"]
ROOT = Path(__file__).resolve().parent.parent


def _pick(rng: random.Random, pool: list[str], smoke: set[str], n: int) -> list[str]:
    pool = sorted(pool)
    fresh = [i for i in pool if i not in smoke]
    if len(fresh) >= n:
        pool = fresh
    return rng.sample(pool, n)


def select(seed: int) -> list[dict]:
    rng = random.Random(seed)
    records = load_records().values()
    smoke = set(smoke_ids())

    def ids(channel: str, language: str) -> list[str]:
        return [r.conversation_id for r in records if r.channel == channel and r.language == language]

    ru_calls = _pick(rng, ids("voice call", "RU"), smoke, 3)
    ru_chats = _pick(rng, ids("agent chat", "RU"), smoke, 9)
    kz = _pick(rng, ids("agent chat", "KZ"), smoke, 6)
    en = _pick(rng, ids("agent chat", "EN"), smoke, 6)

    # Round-robin within each language so every labeler gets the same mix.
    picked: list[dict] = []
    for group in (ru_calls + ru_chats, kz, en):
        for i, cid in enumerate(group):
            picked.append({"conversation_id": cid, "labeler": LABELERS[i % len(LABELERS)]})
    rng.shuffle(picked)
    for i, a in enumerate(picked):
        a["prefill_profile"] = PROFILES[i % len(PROFILES)]
    return picked


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args(argv)

    assignments = select(args.seed)
    ASSIGNMENTS.parent.mkdir(parents=True, exist_ok=True)
    ASSIGNMENTS.write_text(
        json.dumps(assignments, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    ids = ",".join(a["conversation_id"] for a in assignments)
    result = subprocess.run(
        [sys.executable, "-m", "bench.render_transcripts", "--ids", ids], cwd=ROOT
    )
    if result.returncode:
        return result.returncode
    for labeler in LABELERS:
        n = sum(a["labeler"] == labeler for a in assignments)
        print(f"{labeler}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
