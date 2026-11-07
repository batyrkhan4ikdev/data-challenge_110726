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

## Phase 2, preliminary (5 consensus-gold dialogs, 2026-11-07 17:04)

The gold labels are `bench/gold/labels.consensus.csv` (e79aaab, Batyrkhantzy111): 4 blind LLM labelings plus manual checks, with disputes settled by the organizer rules. It covers 5 dialogs: p1-ru-007, p1-ru-017, p1-en-011, p1-kz-010 and the call p4-ru-005. Raw results are in `bench/results/20261107-170403/` and `…-170753/`.

| run | weighted agreement | total MAE | bias | s/dialog | c01 | c02 | c03 | c04 | c05 | c06 | c07 | c08 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| h200-gemma · per_criterion | **0.911** | 4.8 | −1.1 | 57 | 0.8 | 0.8 | 1.0 | 1.0 | 1.0 | 0.8 | 0.8 | 1.0 |
| h200-gemma · single | 0.851 | 7.4 | +7.4 | 4.8 | 0.8 | 0.8 | 1.0 | 1.0 | 0.8 | 0.6 | 0.8 | 1.0 |
| aigw-sonnet · single | 0.832 | 10.2 | −10.2 | 8.2 | 1.0 | 1.0 | 0.8 | 0.6 | 1.0 | 0.8 | 0.6 | 1.0 |
| h200-glimmer · single | 0.822 | **4.6** | +1.5 | 9.3 | 0.8 | 0.8 | 0.8 | 0.8 | 0.8 | 1.0 | 0.6 | 1.0 |
| aigw-luna · single | 0.782 | 13.5 | −12.9 | 18.2 | 1.0 | 0.4 | 0.8 | 0.8 | 1.0 | 0.8 | 0.6 | 1.0 |
| h200-gptoss · single | 0.780 | 14.5 | −14.5 | 10.5 | 0.8 | 1.0 | 0.8 | 0.6 | 0.8 | 0.8 | 0.6 | 0.8 |
| h200-kz · single | 0.772 | 9.8 | +9.6 | 43.3 | 1.0 | 0.6 | 1.0 | 0.8 | 0.8 | 0.6 | 0.2 | 1.0 |
| h200-glimmer · per_criterion | 0.683 | 24.0 | −24.0 | 12.4 | 0.8 | 0.8 | 0.4 | 0.8 | 0.6 | 0.8 | 0.6 | 1.0 |

- **Ranking.** It matches the phase-1 consensus ranking: gemma per_criterion first, then gemma single and Sonnet. Bias splits the models into two groups:
  - lenient: gemma single, kz;
  - strict: Sonnet, Luna, gptoss, and glimmer per_criterion.
- **Gross errors.** All 6 single-mode profiles flag the gross error in p1-en-013 (turn [11], «I charge for private advice»).
- **Caveat: this gold is LLM-derived.** Opus 5.5 and GPT-6 Astra produced it; only p1-ru-007 has a manual label, and it matched the consensus on all 8 criteria. LLM-made gold can favour LLM judges, especially Sonnet and Luna from the same families. Since 17:25, human rows in `labels.<login>.csv` override `labels.consensus.csv`, and the final choice (B6) is made on human labels.
- **Control-run failover:** `scripts/run_batch.py` re-runs any dialog that failed on the primary profile with `FALLBACK_PROFILE=aigw-sonnet`, and records the profile per dialog in `out/<group>.results.*`.
- **Interim default for the control run:** `LLM_PROFILE=h200-gemma`, `EVAL_MODE=per_criterion`, `EVAL_K=1`. It runs at about 1 min per dialog, so 10 control dialogs take about 3 min at concurrency 4. With n=5 this is provisional; re-run on the full gold set (B6) when the 24 labeled dialogs are filled.

## Reproducibility of the control settings (2026-11-07 18:40)

There were two independent full DEV runs with `h200-gemma · per_criterion · k=1`, at temperature 0: the rehearsal at 17:30 and the `--submit dev` run at 18:10. I compared the latest two evaluations per dialog in `data/store`. 64 dialogs were compared; p1-ru-016 was left out because one of its runs was scored on the fallback model.

| criterion | c01 | c02 | c03 | c04 | c05 | c06 | c07 | c08 | all |
|---|---|---|---|---|---|---|---|---|---|
| same verdict | 63/64 | 63/64 | 63/64 | 64/64 | 64/64 | 62/64 | 64/64 | 64/64 | **507/512 (99.0%)** |

- 59/64 dialogs were identical. No gross-error flag changed. The total moved by 0.73 on average, and by at most 18.75, when p4-ru-005 c01 went «Да»→«Нет» on a call.
- The 5 changes were borderline calls:
  - p1-ru-026 c06 4→7;
  - p4-ru-004 c06 7→10;
  - p1-ru-003 c02 N/A→«Нет»;
  - p1-kz-012 c03 «Нет»→N/A;
  - p4-ru-005 c01.

  vLLM at temperature 0 is not bit-exact under batching, so this residual is expected. It is small next to the disagreement with gold.
- **Real run times:** 420 s and 507 s of wall time for 65 dialogs at `EVAL_CONCURRENCY=4`, i.e. about 6.5–8 s per dialog. The «1 min per dialog» above is the per-dialog latency measured without parallelism.

## Phase 2 on the full consensus gold (65 DEV dialogs, 2026-11-07 20:00)

The gold is `bench/gold/labels.consensus.csv`, rounds 1 and 2 by Batyrkhantzy111 (65ecd9d, e955e19). Each dialog has 4 blind LLM labelings: GPT-6 Astra and Claude Opus 5.5 at xhigh, in batches of 10 and one at a time. All 4 agree on 422 of 480 verdicts. Ties go to the lower median of the scale, or to the checklist text; the 16 disputed verdicts are listed in `bench/gold/calibration/round2/README.md`. **There are no human rows yet**, so `--gold human` is empty.

Results are on the 60 chats, because the control set is chats only (#2978). All runs use the same final notes: the C8 rule (#3106) and the C7 rule below.

| run | weighted agreement | total MAE | bias | c01 | c02 | c03 | c04 | c05 | c06 | c07 | c08 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **h200-gemma · per_criterion** | **0.918** | **4.83** | −1.77 | 60 | 56 | 57 | 52 | 57 | 50 | 56 | 60 |
| aigw-luna · single | 0.884 | 6.48 | −2.74 | 60 | 48 | 59 | 50 | 54 | 47 | 56 | 60 |
| h200-glimmer · single | 0.845 | 8.18 | −2.89 | 58 | 46 | 59 | 45 | 54 | 45 | 45 | 60 |
| h200-gptoss · single | 0.832 | 9.21 | −5.24 | 60 | 44 | 53 | 44 | 54 | 49 | 47 | 59 |

Criterion columns are matches out of 60. Summaries: gemma in `bench/results/20261107-195213/summary.md`, the other three in `bench/results/20261107-195213-alt/summary.md`.

**B6 decision:** keep `h200-gemma · per_criterion · k=1`. It leads on every aggregate. The best cloud model (Luna) is 3.4 pp lower, so the «self-hosted unless cloud is more than 5 pp better» rule holds. The fallback chain stays `aigw-sonnet,aigw-luna,h200-glimmer`.

**B7 prompt iterations** (general rules in the checklist `notes`, not per-dialog fixes):

| change | c07 | c04 | c06 | weighted agreement | MAE | kept? |
|---|---|---|---|---|---|---|
| baseline (C8 rule only) | 47 | 51 | 49 | 0.900 | 6.12 | — |
| **C7: a short recap of the result or next step plus a goodbye is «Да»; courtesy alone («Рад был помочь») is not** | **56** | 52 | 50 | **0.918** | **4.83** | **yes**: 9 fixed, 0 broken |
| C6/C4: «0 only if the dialog is incoherent / no answer at all», partial answers get 5–15 | 55 | 52 | 48 | 0.916 | 4.90 | **no**: 3 fixed, 5 broken, c06 drifted lenient (4→10 ×3); reverted |
| **C3 scope: identification only before disclosing this client's data or a protected action; otherwise N/A, even if the question is about the account** (20:44, on top of C7) | 55 | 52 | 50 | **0.930** | 4.87 | **yes**: c03 57 → **60/60**. It fixed all 3 misses where the labelers were unanimous (p1-kz-012, p1-ru-002, p1-ru-018); c08 stayed 60/60, and the other flips are c06 noise |

**Caveats:**
- **These numbers are in-sample.** The same 65 DEV dialogs shaped the C7 rule and scored it, and the gold is LLM-made. Two of the labelers (Opus, Astra) belong to the same families as our cloud fallbacks. Don't read 0.918 as the expected accuracy on the control set. What carries over is the ranking, and that the C7 rule is general: it fixed 9 dialogs across RU and KZ and broke none.
- The run-to-run noise is about 1% of verdicts (507/512 above), so differences of 1–2 verdicts per criterion are inside it.
- c04 and c06 remain the main gap: 8 and 10 misses. Most of them are 2:2 ties in the gold (see the notes column in `labels.consensus.csv`), so they need a human decision rather than another rule.

**Leak check of the C7 rule (20:36).** The C7 note gives four example phrases, and they are taken verbatim from DEV dialogs. For this check I replaced them with paraphrases that occur nowhere in DEV, then re-ran: c07 52/60 (instead of 56), weighted agreement 0.910, MAE 5.02 (`bench/results/20261107-203620/`).
- So about 4 of the 9 c07 gains came from the model matching the exact DEV phrases (p1-ru-007, p1-ru-009, p1-ru-013, p1-ru-002).
- The rule on its own is still worth +5 verdicts (47 → 52).
- **The more honest estimate for unseen chats is therefore ~0.91, not 0.918.**
- The control run keeps the realistic examples. They are correct applications of the organizers' rule («итог или предложение помощи + прощание»), so they can't hurt.
- Changing only the notes also moved c06 by 3 verdicts. Any notes edit perturbs every criterion, because the whole notes text goes into each call; treat ±3 verdicts per criterion as noise.

## Round 3: more models, voting, more GPUs (2026-11-07 21:00–21:20)

All runs use the final notes (C3, C7 and C8 rules) and are scored on the 60 chats of the 65-dialog consensus gold. Hits are matching criterion verdicts out of 480.

| run | weighted agreement | hits | total MAE | bias |
|---|---|---|---|---|
| **h200-gemma · per_criterion**, 3 runs | **0.929** (0.927–0.930) | 450–451 | 4.91 | −1.1 |
| h200-gemma · per_criterion · k=3 (t=0.7, median vote) | 0.924 | 449 | 4.91 | −1.7 |
| Qwen3.8-27B · single (Alem and hk-q27) | 0.901–0.919 | 437–446 | 5.4–6.4 | +2.8 |
| Qwen3.8-27B · per_criterion | 0.880 | 429 | 7.06 | −4.0 |
| Qwen3.8-Flash-Next · single (aigw and hk-big1) | 0.908–0.915 | 444–446 | 4.5–5.4 | +4.3 |
| Qwen3.8-Flash-Next · per_criterion | 0.903 | 441 | 5.54 | −1.5 |
| DeepSeek-V4.1-Flash · single | 0.896 | 439 | 6.22 | −2.3 |
| Kimi-K2.6 · single | 0.851 | 422 | 7.63 | +0.3 |
| **ensemble** gemma-pc + Qwen-27B + Flash-Next (per-criterion majority, median on scales), 12 offline combinations of the runs above | **0.928** (0.918–0.940) | 452 | **4.55** | +2.3 |
| ensemble, live: 2 runs (Qwen members via aigw, then self-hosted) | 0.924, 0.926 | 449, 451 | 4.53, 4.54 | +2.5 |

All models ran with thinking off. GLM-5.3 ignores `enable_thinking=false` (4.9k reasoning characters on a one-line probe), so it was not benchmarked.

**Decision: the control stays on `h200-gemma · per_criterion · k=1`.**
- The ensemble ties it on agreement (0.928 against 0.929). The first offline figure of 0.940 was a lucky combination of runs.
- The ensemble has a lower total error, but it needs three endpoints. It is also more lenient (bias +2.3 against −1.1).
- Gemma alone repeats 99.6% of its verdicts between runs (477–479 of 480), which matches the organizers' stress on reproducibility (#2981). It also needs a single endpoint.
- The `ensemble` profile stays available for the demo; the UI shows the vote per criterion. hk-big1 and hk-q27 were released at 21:20.
- Neither k=3 voting nor thinking mode helped.

**What external benchmarks say** (`docs/research/dsml-models.md`, m3 research): DeepSeek-V4.1-Flash leads on the Russian MERA board, and DeepSeek V3 has the best open KazMMLU score. On our task, though, it is 3 pp below gemma. DSML.KZ's Kazakh arena rates the Gemma family «стабильно сильные». General-language leaderboards don't predict rubric-judging accuracy here.

**Where the remaining errors are.** 28 verdicts are wrong in all 3 gemma runs.
- 19 of them sit where the gold itself is split (2:2 or 3:1), so only a human decision can settle them.
- The other 9 are single cases spread over c02, c04, c05, c06 and c07, with no shared pattern; a rule for any of them would be fitted to one DEV dialog.
- **Further prompt tuning on this gold is at its noise floor.**

**Frontier models via OpenRouter (21:27, $2.38 of the $5 test budget).** Single mode, same notes. OpenRouter reserves credit for `max_tokens` on every request, so at 8 concurrent requests per model part of each run was refused with HTTP 402. The comparison below is therefore **paired**: on the chats each model did score, gemma per_criterion is measured on exactly the same dialogs.

| model | chats scored | its hits | gemma hits on the same chats |
|---|---|---|---|
| Gemini 3.8 Flash (reasoning low) | 49 | 363/392 (0.926) | **367/392 (0.936)** |
| Gemini 4 Argon (reasoning low) | 33 | 243/264 (0.920) | **249/264 (0.943)** |
| Grok 4.7 (reasoning low) | 36 | 264/288 (0.917) | **267/288 (0.927)** |
| DeepSeek-V4-Pro (reasoning off) | 50 | 360/400 (0.900) | **371/400 (0.927)** |

None of the frontier models beats the self-hosted gemma on our task; the gap is 1–2 pp in gemma's favour. These models are from families independent of the gold labelers, which removes the worry that the gold simply favours gemma's family.

## Round 4: human arbitration (Batyrkhantzy111, cfefd8e, 21:27)

There are now **20 human rows** in `bench/gold/labels.Batyrkhantzy111.arbitration.csv`: the 12 disputed chat verdicts plus a manual labelling of p1-ru-007. They override the consensus. Two of the human decisions change general rules:
- **C7:** a recap counts only if the client has no open question left. p1-ru-007 «Путь к обновлению я указал» and p1-ru-009 «Передам вопрос на проверку» are «Нет», because the client's last question stayed unanswered. Both phrases were examples in our earlier C7 note, which taught the model the wrong thing.
- **C4:** an account restriction confirmed without a reason or a deadline, then forwarded for checking, scores 5. The same scenario appears in RU, EN and KZ.

| notes | weighted agreement (60 chats) | human rows | c04 | c07 | MAE |
|---|---|---|---|---|---|
| C3 + C7 (old examples) + C8, 4 runs | 0.927–0.930 | 11–12 / 20 | 52 | 55 | 4.9–5.0 |
| + human C7 rule («open question → Нет») + C4 = 5 rule | 0.936 | 16 / 20 | 55 | 56 | 4.84 |
| + courtesy is not a recap («Рада, что получилось» → Нет) | **0.931** | **16 / 20** | 54 | **57** | **4.53** |

The last row is the control setting. Its examples are paraphrases that occur nowhere in DEV. The 0.936 → 0.931 difference is c06 noise: it moves ±2 verdicts on every notes edit.
