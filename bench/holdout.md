# Holdout gate (#47)

Split: `bench/gold/holdout.json`, written by `python scripts/holdout_gate.py --write-split`. The 60 DEV chats (RU 30 / EN 15 / KZ 15) are stratified by language, shuffled with seed 20261108 and cut 45 tune (RU 23 / EN 11 / KZ 11) and 15 holdout (RU 7 / EN 4 / KZ 4). Gold is the current `load_gold()` (human rows over LLM consensus). Calls are excluded.

```
python scripts/holdout_gate.py --before <run> --after <run>   # exit 1 = overfit flag
```

Overfit flag: weighted agreement (WA) on tune improved, on holdout did not.

## Result on the committed runs (all `h200-gemma · per_criterion · k=1`)

| change (`docs/research/benchmark-phase1.md`) | tune WA | holdout WA | flag |
|---|---|---|---|
| C7 rule -> + C3 scope rule (`195213` -> `204453`, committed in `bench/baselines/`) | 0.911 -> 0.923 (+1.2 pp) | 0.941 -> 0.951 (+1.0 pp) | none |
| C7 with DEV phrases -> C7 with paraphrases (leak check, `195213` -> `203620`) | 0.911 -> 0.907 | 0.941 -> 0.934 | none (both fell) |
| per_criterion -> single mode (`204453` -> `030915`; not a notes change, for reference) | 0.923 -> 0.910 | 0.951 -> 0.970 | none |

The C3 change moves both parts the same way, so the gate does not flag it, but both confidence intervals include 0: this is no evidence of a real gain either. The flag fires whenever tune improves and holdout does not (including a tie), so on 15 holdout dialogs, whose bootstrap 95% CIs are about ±3 pp wide, it is a prompt to look, not a verdict; and the holdout dialogs were seen when the earlier notes were written, so these runs are in-sample. The gate is meant for the next notes edit, where the holdout chats must not be read while writing it.
