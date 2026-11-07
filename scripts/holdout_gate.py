"""Holdout gate for checklist-notes changes: tune/holdout split of the DEV chats and an overfit flag.

    python scripts/holdout_gate.py --before <run> --after <run>     # compare two runs (before/after a notes change)
    python scripts/holdout_gate.py --write-split                    # (re)write bench/gold/holdout.json

The split is deterministic: DEV chats stratified by language, shuffled with a fixed seed, 25% to holdout
(60 chats -> 45 tune / 15 holdout). Each run side is a run directory with one .jsonl, or the .jsonl itself.
'overfit' = weighted agreement on tune improved but did not improve on holdout (by more than --eps).
Note: when notes were edited on DEV chats, the holdout is only "unseen" if the edit was written without
looking at those chats; use it going forward and read old results as in-sample.
"""

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bench.paired import RunError, dialog_cells, load_run, paired_diff, wa  # noqa: E402
from bench.prefill import GoldError, load_gold  # noqa: E402
from bench.sets import load_records  # noqa: E402

SPLIT_PATH = ROOT / "bench" / "gold" / "holdout.json"
SEED = 20261108
HOLDOUT_SHARE = 0.25


def make_split() -> dict:
    by_lang: dict[str, list[str]] = {}
    for r in load_records().values():
        if r.channel == "agent chat":
            by_lang.setdefault(r.language, []).append(r.conversation_id)
    total = sum(len(v) for v in by_lang.values())
    target = round(total * HOLDOUT_SHARE)
    # largest-remainder allocation of holdout slots per language
    quota = {k: len(v) * HOLDOUT_SHARE for k, v in by_lang.items()}
    alloc = {k: int(q) for k, q in quota.items()}
    for k in sorted(quota, key=lambda k: (-(quota[k] - alloc[k]), k))[: target - sum(alloc.values())]:
        alloc[k] += 1
    rng = random.Random(SEED)
    tune: list[str] = []
    holdout: list[str] = []
    for lang in sorted(by_lang):
        ids = sorted(by_lang[lang])
        rng.shuffle(ids)
        holdout += ids[: alloc[lang]]
        tune += ids[alloc[lang] :]
    return {"seed": SEED, "tune": sorted(tune), "holdout": sorted(holdout)}


def load_split() -> dict:
    if not SPLIT_PATH.exists():
        raise RunError(f"нет {SPLIT_PATH}; запустите --write-split")
    return json.loads(SPLIT_PATH.read_text(encoding="utf-8"))


def compare(before: dict, after: dict, split: dict, eps: float = 0.0) -> dict:
    out = {}
    for part in ("tune", "holdout"):
        ids = [i for i in split[part] if i in before and i in after]
        d = paired_diff({i: before[i] for i in ids}, {i: after[i] for i in ids}) if ids else None
        out[part] = {"n": len(ids), "before": wa(before, ids), "after": wa(after, ids), "diff": d and d["diff"],
                     "ci": d and (d["ci_low"], d["ci_high"])}
    out["overfit"] = bool(out["tune"]["diff"] and out["tune"]["diff"] > eps and not (out["holdout"]["diff"] or 0) > eps)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write-split", action="store_true")
    ap.add_argument("--before")
    ap.add_argument("--after")
    ap.add_argument("--eps", type=float, default=0.0, help="min WA gain that counts as improvement")
    args = ap.parse_args(argv)
    if args.write_split:
        split = make_split()
        SPLIT_PATH.write_text(json.dumps(split, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{SPLIT_PATH}: tune={len(split['tune'])} holdout={len(split['holdout'])}")
        return 0
    if not (args.before and args.after):
        ap.error("--before and --after are required")
    try:
        gold = load_gold()
        split = load_split()
        before = dialog_cells(load_run(args.before), gold)
        after = dialog_cells(load_run(args.after), gold)
        res = compare(before, after, split, args.eps)
    except (RunError, GoldError) as e:
        print(f"ошибка: {e}", file=sys.stderr)
        return 2
    print("part     n   before   after    diff     95% CI")
    for part in ("tune", "holdout"):
        r = res[part]
        ci = f"[{r['ci'][0]:+.3f}, {r['ci'][1]:+.3f}]" if r["ci"] else "-"
        diff = f"{r['diff']:+.4f}" if r["diff"] is not None else "-"
        print(f"{part:<8} {r['n']:<3} {r['before']:.4f}  {r['after']:.4f}  {diff}  {ci}")
    print("OVERFIT: tune improved but holdout did not" if res["overfit"] else "no overfit flag")
    return 1 if res["overfit"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
