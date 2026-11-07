"""Regression gate: candidate bench run must not lose weighted agreement with gold against a baseline.

    python scripts/regress_gate.py --baseline bench/baselines/<run> --candidate bench/results/<run> [--max-drop 0.03]

Each side is a run directory with one .jsonl (or the .jsonl itself). The comparison is paired on the
dialogs both runs scored; the CI is a bootstrap over dialogs. Exit 1 when the candidate's weighted
agreement is lower than the baseline's by more than --max-drop (absolute, 0.03 = 3 pp).
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bench.paired import RunError, dialog_cells, load_run, paired_diff  # noqa: E402
from bench.prefill import GoldError, load_gold  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--max-drop", type=float, default=0.03)
    args = ap.parse_args(argv)
    try:
        gold = load_gold()
        base = dialog_cells(load_run(args.baseline), gold)
        cand = dialog_cells(load_run(args.candidate), gold)
        r = paired_diff(base, cand)
    except (RunError, GoldError) as e:
        print(f"ошибка: {e}", file=sys.stderr)
        return 2
    print(f"dialogs (paired): {r['n']}")
    print(f"baseline  WA: {r['base']:.4f}")
    print(f"candidate WA: {r['cand']:.4f}")
    print(f"diff: {r['diff']:+.4f}  95% CI [{r['ci_low']:+.4f}, {r['ci_high']:+.4f}]  (bootstrap over dialogs)")
    if r["base"] - r["cand"] > args.max_drop:
        print(f"FAIL: drop {r['base'] - r['cand']:.4f} > max-drop {args.max_drop}")
        return 1
    print(f"OK: drop within max-drop {args.max_drop}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
