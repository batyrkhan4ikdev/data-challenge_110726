# LLM judge for contact-center QA: conventions, failure modes, mitigations, metrics

Issue #34. Scope: judge RU/KZ/EN chats and calls against `docs/CQA_Chat_Quality_Checklist.md`; compare with hidden human GT. Claims marked **[INF]** are my inference, not a cited finding.

## 1. How human QA applies «Нет» / N/A / fatal flags

| Common convention | Source | Our rule (wins on conflict) |
|---|---|---|
| N/A = criterion did not apply; **removed from numerator and denominator**, never counts against the agent. Score = passed weight / applicable weight × 100. | [Ema QA docs §5.1, 5.5](https://builder-docs.ema.ai/agent-qa/scores) | Same: step 4 of «Порядок расчёта» redistributes weights proportionally. Agrees. |
| «No/Fail» = the action was needed and missed; N/A = precondition absent (e.g. no hold → hold-time N/A). | Ema 5.5; checklist p.3 | Same wording. Where required identification is not in the chat → «Нет», never N/A. |
| Edge: all criteria N/A. Ema returns **100**. | Ema 5.1 | **Differs:** ours is «итог не рассчитывается» (null). Ours wins. |
| Fatal/critical flag as **auto-fail** (whole form → 0; Ema 5.3; AWS «automatic fail»), as a **cap** (e.g. ≤50), or as a **separate measure** (score unchanged, count shown). Vexvon recommends a separate measure plus human confirmation, since one false flag under auto-fail zeroes a call. [Vexvon](https://vexvon.ai/en/blog/critical-errors-call-qa) | | **Differs from auto-fail:** C8 has «БЕЗ БАЛЛОВ»; the score is not changed, the flag is reported separately. Matches the "separate measure" model. |
| Critical list should be short, defined as behaviour, with an explicit not-applicable condition; transcript-based flags give false positives (speaker mix-ups, quoted text). Vexvon | | C8 = 3 listed violations only. Offer alone suffices (checklist p.3); revealing data requires confidential data **and** no prior identification (organizer-answers #2814). Require a verbatim quote from an **operator** turn. |
| Low-confidence / insufficient-data results are sent to a human review queue (Ema 5.1). | | Not in the rubric. Useful for our UI: surface confidence/disagreement between samples. |

Organizer overrides binding for the prompt: C2 N/A when everything (incl. details given to the bot) was supplied up front; C7 = (summary OR offer of help) AND goodbye, a bare goodbye is «Нет»; C3 «Нет» when data was revealed before identification.

## 2. LLM-as-judge failure modes (one source each)

| Failure mode | Evidence |
|---|---|
| Position bias | Zheng et al. 2023, [MT-Bench / Chatbot Arena](https://arxiv.org/abs/2306.05685): GPT-4 flips verdicts on swapped order; systematic study: [Shi et al., ACL IJCNLP 2025](https://aclanthology.org/2025.ijcnlp-long.18). We judge pointwise, so the analogue is criterion order and where in the transcript the evidence sits **[INF]**. |
| Leniency / positivity bias | Thakur et al. 2024, [Judging the Judges](https://arxiv.org/abs/2406.12624): judges are lenient and inflate scores versus humans, notably on ambiguous cases. |
| Evidence / quote hallucination | General LLM hallucination ([Huang et al. survey](https://arxiv.org/abs/2311.05232)). No QA-specific measurement found; fabricated "quotes" are a risk that a substring check detects **[INF]**. |
| Over-use of N/A | No source found for rubric judges. Closest: models over-abstain when given an "unanswerable" escape hatch **[INF]**. Measure it ourselves (N/A rate vs GT). |
| Language bias against Kazakh | Fu et al., [How Reliable is Multilingual LLM-as-a-Judge?, EMNLP Findings 2025](https://aclanthology.org/2025.findings-emnlp.587): judge consistency is markedly lower for low-resource languages. |
| Long-transcript attention loss | Liu et al., [Lost in the Middle](https://arxiv.org/abs/2307.03172): accuracy drops for facts in the middle of long context. Our transcripts are short, so low risk except long calls. |
| Mid-scale clustering | Stureborg et al., [LLMs are Inconsistent and Biased Evaluators](https://arxiv.org/abs/2405.01724): scores concentrate on a few values, with low variance. Our 5-step (0/5/10/15/20) and 4-step (0/4/7/10) scales invite the "15" and "7" default. |

## 3. Mitigations and expected effect

- **Rubric quoting** (put the checklist wording and scale-step descriptions in the prompt verbatim): Prometheus ([Kim et al.](https://arxiv.org/abs/2310.08491)) shows per-criterion rubrics with step descriptions raise human correlation. Effect: fewer interpretation drifts; cheap.
- **Evidence-first**: ask for explanation before the verdict. [Chiang & Lee 2023](https://aclanthology.org/2023.findings-emnlp.599) found that asking the LLM to explain its rating consistently improves correlation with humans, and number-only output is suboptimal. Put `quote` and `turn_index` before `verdict` in the JSON schema so the field order enforces it. Also gives us the checklist-required "подтверждающий фрагмент".
- **Per-criterion vs one call**: no controlled study found for this checklist. G-Eval ([Liu et al.](https://arxiv.org/abs/2303.16634)) scores each aspect with its own prompt. **[INF]** One call with all 8 criteria is cheaper and sees shared context, but is prone to halo effect (one bad turn drags every criterion) and mid-scale defaults. Choose by benchmark; keep the prompt module able to do both.
- **Self-consistency / majority vote**: [Wang et al. 2022](https://arxiv.org/abs/2203.11171) gives gains on reasoning by sampling several chains and taking the mode. For judging: vote on yes/no/N-A, take the median for scales, and use the disagreement as a confidence signal. Gain is usually small versus cost; spend it on the criteria with highest weight or disagreement (C3, C4).
- **Temperature**: [Renze & Guven 2024](https://arxiv.org/abs/2402.05201) find temperature in 0–1.0 does not significantly change problem-solving accuracy. Use 0 for the single run; ~0.7 only when sampling n>1 for voting.
- **Few-shot**: Zheng et al. report that few-shot examples raised GPT-4's position consistency (about 65% → 77%) at higher cost and some added bias. For us: 1–2 short examples on the hardest rules (C2 N/A, C7, C3-before-data), not for scale levels, to avoid anchoring.
- **Explicit N/A procedure**: **[INF]** no direct evidence. Force a two-step decision, "(a) is the condition for N/A true? quote it; (b) otherwise yes/no", with N/A allowed only on the criteria that have it.
- **Reasoning language**: Shi et al., [Language models are multilingual CoT reasoners](https://arxiv.org/abs/2210.03057), show native-language CoT works, but English reasoning is often equal or better. For Kazakh, the Fu et al. paper above shows weaker judging in the source language. **[INF]** Recommendation: reason in Russian (the checklist language, strong in all our models), but quote evidence verbatim in the source language. Validate on KZ dialogs.

## 4. Agreement metrics for mixed nominal + ordinal labels

- **Exact agreement** per criterion: easy to read, but inflated by prevalence (most C1 labels are «Да»). Report with the majority-class baseline.
- **Cohen's kappa** ([1960](https://doi.org/10.1177/001316446002000104)) for nominal criteria (C1, C2, C3, C5, C7, C8, including N/A as a third class); chance-corrected. Beware the kappa paradox at skewed prevalence ([Feinstein & Cicchetti 1990](https://doi.org/10.1016/0895-4356(90)90158-L)); report it next to raw agreement. On 10 control dialogs per-criterion kappa is very noisy, so also pool across dialogs.
- **Quadratic-weighted kappa** ([Cohen 1968](https://doi.org/10.1037/h0026256)) for C4 and C6 (ordinal steps, N/A as a separate category excluded or handled by a separate N/A-agreement). Penalises 0-vs-20 more than 15-vs-20.
- **MAE of the total** (and signed bias = mean(pred − gold)): this is what the organizers actually compare, so it is the primary outcome. The signed bias directly reveals leniency.
- **N/A confusion**: a 2×2 (N/A vs applicable) per criterion, because wrong N/A changes the total through reweighting.

## Recommendations for this repo

Prompt rules for `server/evaluator/prompt.py` (text in Russian):

1. Порядок полей в JSON: `evidence` (turn_index + дословная цитата) → `reasoning` → `verdict`/`score`. Вердикт нельзя писать раньше цитаты.
2. «Цитата должна быть дословной подстрокой реплики. Если критерий не выполнен, укажи место, где действие ожидалось. Если подтверждения нет, ставь «Нет», а не придумывай цитату.» Код проверяет подстроку и снижает уверенность или перезапускает вызов.
3. «N/A допустим только для критериев 2, 3, 4, 7. Сначала ответь: выполнено ли условие N/A из чек-листа (процитируй его)? Если нет — оцени «Да»/«Нет». Сомневаешься между N/A и «Нет» при пропущенном обязательном действии — выбирай «Нет».»
4. C2: «N/A, если клиент назвал все данные сразу, включая данные, сообщённые боту.» C7: «Да только при итоге ИЛИ предложении помощи И прощании; одно прощание — «Нет».» C3: «Данные раскрыты до идентификации — «Нет».»
5. C8: «Флаг ставится только за три перечисленных нарушения, только по репликам оператора; цитата обязательна. Флаг не меняет баллы.» По умолчанию «Нет».
6. Шкалы: «Выбирай только указанные ступени. Опиши, чем твоя ступень лучше соседней сверху и снизу. Не выбирай среднюю ступень по умолчанию.» Для C4 и C6 дай описания всех ступеней дословно из чек-листа.
7. «Будь строгим: оценивай только то, что есть в переписке; не засчитывай намерения и вежливость, не подтверждённые репликой.» (антиснисходительность)
8. «Рассуждай по-русски; цитаты приводи на языке оригинала (RU/KZ/EN).» Проверить на KZ-диалогах отдельно.
9. Вызовы: temperature 0 для одного прогона; при голосовании n≥3 temperature ≈0.7, мода по да/нет/N/A, медиана по шкале, расхождение → низкая уверенность в UI. Few-shot: 1–2 коротких примера на C2/C7/C3, без примеров шкальных оценок. Дать возможность переключаться между «один вызов» и «вызов на критерий», выбор по бенчмарку.

Metrics to add to `bench/metrics.py` (besides weight-weighted agreement):

1. Per-criterion exact agreement plus the majority-class baseline.
2. Cohen's kappa for nominal criteria (N/A as a class), pooled over dialogs; show raw agreement next to it.
3. Quadratic-weighted kappa for C4 and C6.
4. MAE of the total and the signed bias (mean pred − gold) of the total.
5. N/A confusion per criterion (predicted vs gold N/A rate).
6. C8 precision/recall (rare class; accuracy is meaningless).
7. Breakdown by language (RU/KZ/EN) and channel, to catch the Kazakh gap.
8. Citation validity rate: share of quotes that are exact substrings of the transcript.
