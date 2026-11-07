# Benchmark phase 1 (smoke set, 12 DEV dialogs, no gold yet)

Run on 2026-11-07 between 16:10 and 16:30 (UTC+5) with `python -m bench.run --set smoke`. Raw summaries are in `bench/results/20261107-161143/`, `…-161450/` and `…-162940/`. The set is 5 RU chats, 3 KZ chats, 2 EN chats and 2 calls, all k=1.

No gold labels existed yet, so "agreement" is measured against other models:
- **vs consensus:** the weighted share of criteria where the run matches the majority verdict of all *other* runs. It uses checklist weights; c08 counts with weight 1.
- **vs sonnet:** the same measure against Claude Sonnet 5.5 alone, used as a strong reference.

These numbers are proxies. Phase 2 against the 24 gold dialogs decides the default (B6).

| run | ok | first-try valid | s/dialog (mean) | vs consensus | vs sonnet | mean total | N/A share |
|---|---|---|---|---|---|---|---|
| h200-gemma · single | 12/12 | 1.00 | 6.5 | 0.884 | 0.835 | 93.4 | 0.27 |
| h200-gemma · per_criterion | 12/12 | 1.00 | 39.4 | **0.913** | **0.880** | 88.5 | 0.27 |
| h200-gptoss · single | 12/12 | 0.92 | 22.7 | 0.794 | 0.769 | 76.8 | 0.15 |
| h200-gptoss · per_criterion | 12/12 | 0.83 | 28.0 | 0.715 | 0.645 | 64.6 | 0.10 |
| h200-kz · single | 11/12 | 0.91 | 23.8 | 0.820 | 0.748 | 92.3 | 0.22 |
| h200-kz · per_criterion | 12/12 | 1.00 | 21.8 | 0.757 | 0.761 | 75.1 | 0.18 |
| aigw-sonnet · single | 12/12 | 1.00 | 6.9 | 0.847 | n/a | 78.7 | 0.26 |
| aigw-luna · single | 12/12 | 1.00 | 20.6 | 0.876 | 0.802 | 84.6 | 0.23 |
| aigw-alemllm · single | 9/12 | 0.89 | 7.4 | 0.631 | 0.648 | 70.6 | 0.18 |
| h200-glimmer · single | 12/12 | 1.00 | 13.5 | 0.839 | 0.785 | 83.5 | — |
| h200-glimmer · per_criterion | 12/12 | 1.00 | 48.0 | 0.773 | 0.777 | 66.0 | — |

The glimmer runs were added at 16:36. The vs-consensus values above were computed without them. With glimmer in the consensus the order stays the same: gemma per_criterion 0.917, gemma single 0.889, sonnet 0.868, luna 0.864, glimmer single 0.839.

Cost per evaluation:
- **Self-hosted:** about $0.001, computed as H200 $5.35/h × GPU-seconds ÷ concurrency.
- **Sonnet:** $0.024 at $2/$10 per Mtok.
- **Luna:** $0.001.

## Findings

1. **Valid output.** gemma (both modes), Sonnet and Luna never needed a retry.
   - All failed dialogs (kz 1, alemllm 3) were one rule: «Да» or «Нет» on c05/c06 with no cited turn.
   - Since commit "keep verdict with warning when evidence is missing after retry", such items are kept with `Item.warnings`, and bench reports `evidence_fallback_rate`. A soft criterion no longer drops the whole dialog.
2. **Totals split into two clusters.**
   - gemma and kz-single score high, around 92–93.
   - gptoss, Sonnet and alemllm score lower, around 70–79.
   - On the call `p4-ru-003` the totals ranged from 46 (gptoss) to 100 (kz). Gold must decide which side is right; Sonnet sits in the middle.
3. **Where models disagree.** This is the share of smoke dialogs on which the single-mode runs disagree, by criterion:

   | c01 | c02 | c03 | c04 | c05 | c06 | c07 | c08 |
   |---|---|---|---|---|---|---|---|
   | 0.00 | 0.58 | 0.50 | 0.75 | 0.33 | 0.42 | **0.83** | 0.00 |

   - **c07 «Завершение»** disagrees most. The organizer rule «одно прощание — «Нет»» (#2814) is in the checklist notes, but the models apply it inconsistently. This is the first target for B7 prompt work.
   - **c04** (scale 0–20) and **c02/c03** (N/A versus Да/Нет) come next.
4. **Mode.** Per-criterion calls help gemma: agreement rises from 0.884 to 0.913 and the total drops from 93.4 to 88.5, which is less lenient. They hurt gptoss (from 0.794 to 0.715). Per-criterion costs about 6× the prompt tokens and is about 6× slower for gemma (39 s per dialog at concurrency 4).
5. **Thinking variants** were spot-checked on 2 dialogs.
   - gemma-think once ran 436 s and produced 12.8k output tokens. Not usable.
   - kz-think took 25–31 s and still gave 100 on the call.
   - gptoss-med gave 51 on the call, against 46 for low.
   - No thinking variant goes into phase 2.

## Phase 2 plan (B6, once gold labels exist)

- Candidates: `h200-gemma` single and per_criterion, `aigw-sonnet` single, `aigw-luna` single, `h200-gptoss` single, plus `muse-glimmer` if its endpoint comes up.
- Choose by weighted per-criterion agreement with gold. The organizers compare per criterion (#2978).
- Prefer self-hosted unless a paid model leads by more than 5 pp.
- For reproducibility (#2981), the control run uses temperature 0 with k=1, or k=3 with a fixed seed if voting wins.
