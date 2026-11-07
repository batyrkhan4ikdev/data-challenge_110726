# Kazakh LLM benchmarks and leaderboards (read 2026-11-08)

Map of every published Kazakh-language evaluation we could find, with the best published scores on each.
Scope: knowledge/reading, culture, safety, instruction-following and dialogue, translation, plus the
leaderboards that rank models on them. `n/p` = nothing published that we could open. `unverified (HTTP xxx)`
= the page exists but would not open for an anonymous reader.

Companion docs (do not repeat them): [`../dsml-models.md`](../dsml-models.md) (arena/community view),
[`../asr-models.md`](../asr-models.md) (RU/KZ telephony ASR), [`../llm-candidates.md`](../llm-candidates.md),
[`../benchmark-phase1.md`](../benchmark-phase1.md) (our own CQA judge bench).

Models already callable by us are marked **доступна нам**: `alemai/astanahub/alemllm`,
self-hosted `issai/Qwen3.5-35B-A3B-Kazakh` (`qwen3.5-35b-a3b-kazakh`), `kuspeech:multilingual`.

## 0. Five things this survey says

1. **For LLMs, the only native Kazakh benchmark suite is KazMMLU + KazCulture + KazBench-KK + Qorgau.**
   Almost everything else sold as a "Kazakh benchmark" is a machine-translated port of an English set (MMLU,
   MMLU-Pro, ARC, GSM8K, GPQA, Belebele, IFBench, RAGBench, PolyMath) published by ISSAI as the **Qolda** suite
   ([collection](https://huggingface.co/collections/issai/qolda-language-benchmarks)), a localized IFEval port
   (Marco-Bench-MIF kk), or a community re-run. The genuinely native older resources are task-level classical NLP
   sets (KazNERD 2022 NER, KazSAnDRA 2024 sentiment, KazQAD 2024 QA, KazParC 2024 parallel corpus) — not LLM suites.
2. **No Kazakh leaderboard is live.** All four boards (`kz-transformers/kaz-llm-lb`, `kaz-llm-lb2`,
   `kaz-offline-arena`, `Yersultan03/kazbench-leaderboard`) are paused/sleeping and their live state sits in
   gated HF datasets (HTTP 401). The only readable numbers are committed seed files and paper tables (§3).
3. **There is no Kazakh human-preference data at all** — no Kazakh Chatbot Arena, no Kazakh MT-Bench release,
   no Kazakh DPO preference set used for evaluation (§4). "Kaz Offline Arena" is an *LLM-judged* arena, not a
   human one, and its ELO table is unreadable.
4. **Kazakh-specific tuning buys a lot on Kazakh MC knowledge and nothing on judging.** `issai/Qwen3.5-35B-A3B-Kazakh`
   posts the highest KazMMLU number we can find anywhere (84.0) yet it lost to `gemma-4-31B` on our own
   60-chat gold (§7, [`../benchmark-phase1.md`](../benchmark-phase1.md)).
5. **Script is the biggest single variable.** Every open model loses 5.6–30.4 points the moment Kazakh is
   written in Latin; GPT-5 loses 1.4 (§1.3). Any of our chats in Latin or code-mixed Kazakh invalidates these boards.

---

## 1. Knowledge, reading and culture

### 1.1 KazMMLU — the reference Kazakh knowledge benchmark

| Field | Value |
|---|---|
| What it measures | MMLU-style MC subject knowledge from Kazakh/Russian school and university exams (itest.kz, oltest.kz, ymnik.kz), 5 groups: STEM, Social Science, Humanities, Language, Other |
| Size | 23,000 questions total; **9,870 Kazakh-language** items (12 high-school subjects) — the Russian part is separate; 37 subject configs on HF |
| Authors / link | Togmanov, Mukhituly, Turmakhan et al. (MBZUAI / Horde), **ACL 2025** — [arXiv 2502.12829v2](https://arxiv.org/html/2502.12829v2), [ACL](https://aclanthology.org/2025.acl-long.701/), [dataset `MBZUAI/KazMMLU`](https://huggingface.co/datasets/MBZUAI/KazMMLU) |
| License | CC-BY-NC-4.0 (dataset, HF API) |
| Scoring | accuracy, log-likelihood over options; **English prompt** (Table 4) and **Kazakh prompt** (Table 7); zero-shot and few-shot |

Top published scores — **English prompt, zero-shot** (paper Table 4, v2 revised 2025-07-21):

| Model | STEM | Soc.Sci | Human. | Language | Other | **Average** |
|---|---:|---:|---:|---:|---:|---:|
| **DeepSeek V3** | 77.6 | 81.3 | 78.9 | 61.2 | 65.1 | **76.9** |
| GPT-4o | 70.0 | 81.9 | 83.3 | 73.4 | 62.1 | 76.6 |
| YandexGPT | 54.8 | 70.6 | 63.7 | 42.6 | 57.0 | 60.2 |
| Gemma-2-27B-it | 57.3 | 60.5 | 63.2 | 39.1 | 48.3 | 57.4 |
| Llama-3.1-70B | 58.0 | 59.1 | 57.4 | 41.8 | 49.3 | 56.2 |
| Qwen-2.5-7B-instruct | 47.5 | 51.0 | 51.4 | 33.9 | 42.3 | 47.8 |
| Sherkala-Chat-8B | 43.1 | 49.8 | 50.0 | 34.9 | 38.3 | 45.6 |
| Llama-3.1-70B-instruct | 51.2 | 48.1 | 51.3 | 33.9 | 45.6 | 48.3 |
| KazakhLLM-8B (KazLLM-1.0) | 40.3 | 45.6 | 44.0 | 31.3 | 38.6 | 41.7 |
| Mistral-7B-Instruct-v0.3 | 37.6 | 47.4 | 43.3 | 30.0 | 40.6 | 41.0 |

Same set with a **Kazakh prompt** (paper Table 7): GPT-4o 76.7 (unchanged), **DeepSeek V3 collapses 76.9 → 45.5**,
Llama-3.1-70B 59.9, Gemma-2-27B 58.7, Gemma-2-27B-it 58.8, Sherkala-Chat-8B 38.2, KazakhLLM-8B 38.9.
Language-level split (paper Fig. 6, high-school only): GPT-4o best in **Kazakh 76.90**, DeepSeek V3 best in
**Russian 81.4**.

2026-era numbers, Cyrillic. Rows marked *(audit)* come from the EMNLP 2026 re-run
([Table 8](https://aclanthology.org/2026.emnlp-main.1479.pdf), exact-match JSON scoring, English instruction preamble);
rows marked *(card)* are ISSAI's own model-card tables (generation scoring, thinking on) and are **not measured by a
third party**:

| Model | KazMMLU (Cyrillic) | Δ to Latin avg |
|---|---:|---:|
| GPT-5 *(audit)* | **92.5** | −0.4 |
| Gemini-3.1-Flash *(audit)* | 87.4 | −9.0 |
| Gemini-2.5-Flash *(audit)* | 78.8 | −11.8 |
| **issai/Qwen3.5-35B-A3B-Kazakh *(card)*** | **84.0** | n/p |
| stock Qwen3.5-35B-A3B *(card)* | 82.6 | n/p |
| GPT-4o *(audit)* | 76.1 | −15.3 |
| Qwen3.5-9B (think) *(audit)* | 74.5 | −11.3 |
| Gemma-4-E4B-it (think) *(audit)* | 69.2 | −15.6 |
| Sherkala-8B *(audit)* | 48.8 | −16.4 |
| KazLLM-8B *(audit)* | 44.7 | −12.2 |

Other published KazMMLU numbers we can source: `issai/Qwen3.5-9B-Kazakh` **83.1** vs stock 77.0,
`issai/Qwen3.5-4B-Kazakh` **78.5** vs stock 72.5 ([cards](https://huggingface.co/issai/Qwen3.5-9B-Kazakh), 2026-08-19);
`issai/Qolda-AVL-34B` 78.98, `Qolda-AVL-9B` 73.04, `Qolda-Think` 66.14, `Qolda-NoThink` 58.11
([card](https://huggingface.co/issai/Qolda-AVL-34B)); Sherkala's own harness reports KazMMLU kk-sherkala base 51.6 /
Sherkala-Chat 41.4 / KazLLM-8B 37.0 — a different prompt and log-likelihood scorer, so **not comparable** with the
rows above ([arXiv 2503.01493v2, Table 4](https://arxiv.org/pdf/2503.01493)).

### 1.2 KazCulture — Kazakh cultural knowledge (ISSAI, 2026)

| Field | Value |
|---|---|
| What it measures | Kazakh customs, traditions, beliefs, cuisine, household practice; MC with a letter answer |
| Size | **16,137** human-crafted Passage-Question-Answer triplets; the **test split used for scoring is 1,334 items** |
| Link | [dataset `issai/KazCulture`](https://huggingface.co/datasets/issai/KazCulture) (gated, auto), [ISSAI announcement 2026-03-19](https://issai.nu.edu.kz/2026-03-19/introducing-cultural-knowledge-in-language-models-kazculture-dataset-for-kazakh-culture), [IEEE Access doi 10.1109/ACCESS.2026.3676919 / record 11443272](https://ieeexplore.ieee.org/document/11443272) |
| License | n/p on the gated card |
| Headline finding (authors, 2026-03) | 36 LLMs evaluated; proprietary GPT-5 / Gemini-2.5-Pro reach **up to 80%**, open models "struggle significantly"; two-stage SFT lifts Qwen3-32B **39.51 → 64.54** |

Published scores:

| Model | KazCulture | Source |
|---|---:|---|
| GPT-5 | **77.3** | [EMNLP 2026 audit, Table 9](https://aclanthology.org/2026.emnlp-main.1479.pdf) |
| Gemini-3.1-Flash | 74.2 | same |
| GPT-4o | 68.9 | same |
| **issai/Qwen3.5-35B-A3B-Kazakh** | **68.7** (stock Qwen3.5-35B-A3B 60.3) | [card](https://huggingface.co/issai/Qwen3.5-35B-A3B-Kazakh), 2026-08 |
| Qwen3-32B after ISSAI-SFT + KazCulture SFT | 64.54 (from 39.51 baseline) | [ISSAI blog, 2026-03-19](https://issai.nu.edu.kz/2026-03-19/introducing-cultural-knowledge-in-language-models-kazculture-dataset-for-kazakh-culture) |
| issai/Qwen3.5-9B-Kazakh | 63.4 (stock 49.5) | [card](https://huggingface.co/issai/Qwen3.5-9B-Kazakh) |
| issai/Qolda-AVL-34B | 62.37 | [card](https://huggingface.co/issai/Qolda-AVL-34B) |
| Gemini-2.5-Flash | 58.4 | EMNLP 2026 audit |
| Qwen3.5-9B | 53.8 | same |
| Sherkala-8B | 53.8 (Δ to Latin −27.7, the worst drop in the study) | same |

### 1.3 Cross-script audit — the same benchmarks in Latin Kazakh

Askar, Mukhametkali, Maxutov, Makhataeva, Medeu, Varol (ISSAI/NU/Al-Farabi), **EMNLP 2026 main**,
["Do LLMs Cross Alphabets?"](https://aclanthology.org/2026.emnlp-main.1479.pdf), [code](https://github.com/IS2AI/Do-LLMs-cross-alphabets_code).
13 models × 3 benchmarks (KazMMLU 9,870 / KazCulture 1,334 / GSM8k-Kazakh 1,319) × 5 scripts.
Mean-of-three Cyrillic baselines and drop to the four Latin proposals:

| Model | Cyrillic avg | Latin avg | Δ |
|---|---:|---:|---:|
| GPT-5 | **88.3** | 86.9 | **−1.4** |
| Gemini-3.1-Flash | 84.5 | 75.9 | −8.6 |
| GPT-4o | 78.5 | 63.5 | −15.0 |
| Gemini-2.5-Flash | 75.5 | 63.4 | −12.1 |
| Qwen3.5-9B (think) | 71.5 | 57.4 | −14.1 |
| Qwen3.5-4B (stock) | 57.1 → 66.7 (think) | 37.4 → 49.3 | −19.7 → −17.4 |
| issai/Qwen3.5-*-Kazakh line | **not run in this audit** (only stock Qwen3.5, KazLLM, Sherkala, Qolda among the Kazakh-adapted set) | — | — |
| Qolda (Kazakh VLM) | 60.4 | 48.9 | **−11.5** (best cross-script of the Kazakh-adapted set) |
| Sherkala-8B | 57.2 | 26.8 | **−30.4** |
| KazLLM-8B | 47.4 | 25.6 | −21.8 |
| Gemma-4-E4B-it (think) | 65.8 | 44.6 | −21.2 |
| Llama-3.1-8B-Instruct | 43.6 | 22.4 | −21.2 |

Mitigations they tested: prompt hint/mapping recovers ≈+1 point; a per-variant **LoRA recovers up to +20
points on Latin (Qwen3.5-4B think: 42.6 → 62.6) but only on large reasoning-capable bases** (Tables 3–4).
Statistical floor (their Eq. 4): ±0.99 KazMMLU, ±2.68 KazCulture, ±2.70 GSM8k-Kazakh.
**They deliberately excluded LLM-as-judge scoring from Latin Kazakh because judge reliability there is
unestablished** (§3.2 of that paper) — that constraint applies to us too.

### 1.4 KazBench-KK — 7,111 cultural MC questions (Horde Research)

| Field | Value |
|---|---|
| What it measures | Culturally grounded Kazakh knowledge across 17 domains (pastoral traditions, kinship/hierarchy, swearing, proverbs, cinema, politics, food) |
| Size | 7,111 MCQ, 4 options; logit-level scoring, offline-only (open weights only, no API models) |
| Link | [ACL Anthology, FieldMatters 2025](https://aclanthology.org/2025.fieldmatters-1.4.pdf), [dataset `kz-transformers/kk-socio-cultural-bench-mc`](https://huggingface.co/datasets/kz-transformers/kk-socio-cultural-bench-mc) |
| License | CC-BY-4.0 |
| Note | This is what ISSAI's Qolda model cards call the column "KazBench" — three different things share that name (§8) |

Published accuracy (paper Table 5, 2025; and Qolda card, 2026):

| Model | Accuracy |
|---|---:|
| google/gemma-3-27b-it | **0.7216** |
| meta-llama/Llama-3.3-70B-Instruct | 0.7090 |
| meta-llama/Llama-3.1-70B-Instruct | 0.7030 |
| nvidia/Llama-3_3-Nemotron-Super-49B-v1 | 0.6936 |
| inceptionai/Llama-3.1-Sherkala-8B-Chat | 0.6909 |
| issai/LLama-3.1-KazLLM-1.0-70B | 0.69 (prose) / 0.5746 on the lb board |
| mistralai/Mistral-Small-24B-Instruct-2501 | 0.6761 |
| Qwen/Qwen2.5-32B-Instruct | 0.6334 |
| issai/LLama-3.1-KazLLM-1.0-8B | 0.5656 |
| nvidia/Llama-3.1-Nemotron-Nano-8B-v1 | 0.3542 |
| TilQazyna/llama-kaz-instruct-8B-1 | 0.2768 |
| issai/Qolda-AVL-34B | **0.7005** (Qolda card) |

Weak categories for *every* model: Kazakh Literature (mean 52.3%), Cinema (63.2%), Sports; easiest:
World History (87.5%), Math, Chemistry — a training-data gap, not a capability gap
([Dias Ilyas / NITEC post](https://www.linkedin.com/posts/diasilyas_we-benchmarked-9-foreign-open-source-llms-activity-7500170267021873152-rYFh), ~2026-09).

### 1.5 Belebele (kk) — reading comprehension

[`facebook/belebele`](https://huggingface.co/datasets/facebook/belebele), config `kaz_Cyrl`, test split
**900 items**, CC-BY-SA-4.0; parallel human-translated passages + question + 4 options
([paper, ACL 2024](https://arxiv.org/abs/2308.16884)). Scores:

| Model | Belebele-kk | Setting | Source |
|---|---:|---|---|
| Qwen3.5-4B-Kazakh | **85.6** (stock 84.6) | gen, thinking | [card](https://huggingface.co/issai/Qwen3.5-4B-Kazakh) |
| Qwen3.5-9B-Kazakh | 87.9 (stock 87.3) | gen, thinking | [card](https://huggingface.co/issai/Qwen3.5-9B-Kazakh) |
| Qwen3.5-35B-A3B-Kazakh | 88.9 (stock **89.4**) | gen, thinking | [card](https://huggingface.co/issai/Qwen3.5-35B-A3B-Kazakh) |
| issai/Qolda-AVL-34B | 88.78 | gen | card |
| GPT-4 (2024) | 0.85 (kk prompt) / 0.87 (en) | prompted | [SIGTURK 2024 Table 4](https://aclanthology.org/2024.sigturk-1.8.pdf) |
| Gemini 1.5 Pro | 0.86 | prompted | same |
| Sherkala-Chat-8B | 30.6 | log-likelihood, lm-eval-harness | [arXiv 2503.01493 Table 4](https://arxiv.org/pdf/2503.01493) |
| Qwen-2.5-Instruct-7B | 31.1 | log-likelihood | same |
| Darmm/darmm-chat-kazakh-8b | 39.8 (Qwen3-8B base 27.2) | log-prob MC | [card](https://huggingface.co/Darmm/darmm-chat-kazakh-8b), 2026-09 |

The 30 vs 88 spread is a **scoring-method artefact** (log-likelihood over options vs free-form answer
extraction), not a model difference. Do not mix these columns.

### 1.6 INCLUDE (kk) — regional knowledge/reasoning

INCLUDE ([arXiv 2411.19799](https://arxiv.org/abs/2411.19799)) covers 44 languages, 197,243 QA pairs; Kazakh is
flagged Cyrillic / Turkic / Western / low-resource with **5,736 samples**. GPT-4o 5-shot in-language:
**Humanities 80.4 (n=500), Other 46.0 (n=250)** (paper Table 9); the per-language summary in Table 6 reports a
Kazakh average of **80.40** computed over the Humanities column only (its Other cell is blank), so do not read 80.4
as a whole-language score. Output-length budget barely matters (79.2 → 80.4 from k=50 to k=512, paper Table 12).
ISSAI's own runs: Qolda-AVL-34B **61.80**, AVL-9B 57.20, AVL-5B 53.80, Qolda-Think 46.00,
Qolda-NoThink 45.20 ([card](https://huggingface.co/issai/Qolda-AVL-34B)). It is *not* an MT benchmark — the brief's
"INCLUDE kk translation" premise was wrong.

### 1.7 KazQAD — open-domain QA (ISSAI, LREC-COLING 2024)

| Field | Value |
|---|---|
| What it measures | Kazakh open-domain QA over ~815,000 Kazakh Wikipedia passages (dump 2023-01-20): retrieval, reading comprehension, end-to-end ODQA |
| Size | 5,964 annotated questions — train 3,487 (from NQ), dev 548 (UNT), **test 1,929 (UNT)**; RC pairs 3,163/764/2,713; corpus 11,820 labelled passages |
| Link | [arXiv 2404.04487](https://arxiv.org/abs/2404.04487), [ACL](https://aclanthology.org/2024.lrec-main.843/), [GitHub IS2AI/KazQAD](https://github.com/IS2AI/KazQAD), [`issai/kazqad`](https://huggingface.co/datasets/issai/kazqad) (gated, HTTP 401 anonymous) |
| License | CC BY-SA 4.0 |

Published scores:

| System | Retrieval NDCG@10 | RC EM/F1 | ODQA EM/F1 | Source |
|---|---:|---|---:|---|
| XLM-R re-ranker (fine-tuned) | **0.3892** | — | — | KazQAD paper Table 4 |
| BM25 | 0.1446 | — | 7.7 / 12.6 | Tables 4, 6 |
| XLM-V (NQ-translated + KazQAD) | — | **38.52 / 54.18** | **17.8 / 28.7** (with fusion) | Tables 5, 6 |
| GPT-4 | — | open-book F1 0.57 (en) / 0.36 (kk) | closed-book recall 0.33, 695/1,927 answered | [SIGTURK 2024 Table 4](https://aclanthology.org/2024.sigturk-1.8.pdf) |
| AYA-101 | — | **0.61 (en)** / 0.48 (kk) | 0.09 (114) | same |
| Gemini 1.5 Pro | — | 0.10 | answered only 10–13% | same |
| gpt-3.5-turbo-0125 | — | 0.42 / 0.16 | 9% of questions at recall ≥0.5 | KazQAD paper |
| KazLLM-8B + Snowflake retriever (best end-to-end RAG) | — | — | **0.754** answer correctness (LLM-judged) vs GPT-4o 0.632; ideal-RAG with gold passages 0.867 / 0.869; closed-book KazLLM 0.427 | Mansurova et al., *Information* 16(11):943, 2025-10-30, [doi](https://doi.org/10.3390/info16110943) — abstract only, **full table unverified (HTTP 403)** |
| issai/Qolda-AVL-34B / Qolda-NT | — | judged score | **70.36** / 70.99 | [Qolda card](https://huggingface.co/issai/Qolda) |

### 1.8 The ISSAI **Qolda** port suite (Kazakh translations of the standard set)

Collection: <https://huggingface.co/collections/issai/qolda-language-benchmarks> (9 datasets, updated 2026-04-30).
All are machine-translated, Kazakh questions and options, MIT or apache-2.0/CC-BY-4.0, funded by Kazakhstan MSHE
grant **BR24993001**. Sizes verified from the HF API:

| Dataset | Items | License | Kazakh score, best published |
|---|---:|---|---|
| `issai/MMLU_Kazakh` | 14,042 | MIT | Qwen3.5-35B-A3B-Kazakh 84.4 vs stock 87.2 ([card](https://huggingface.co/issai/Qwen3.5-35B-A3B-Kazakh)); Qolda-AVL-34B 81.94 |
| `issai/MMLU-Pro_Kazakh_Russian` | 12,032 kk (+12,032 ru) | MIT | 76.1 (stock 79.3); AVL-34B 73.67 |
| `issai/MMLU_Redux_2.0_Kazakh` | ~5,700 (57 subjects) | CC-BY-4.0 | 85.9 (stock 88.4); AVL-34B 84.39 |
| `issai/ARC_Kazakh_Russian` | 3,548 kk test items (ARC easy+challenge) | MIT | ARC-E 97.5 / ARC-C 95.5 (Kazakh 35B); AVL-34B 96.76 combined |
| `issai/GSM8k_Kazakh_Russian` | 1,319 kk (+1,319 ru) | MIT | Qwen3.5-4B-Kazakh 89.0; stock 9B 88.0; AVL-34B 90.52; GPT-5 95.0 ([audit Table 10](https://aclanthology.org/2026.emnlp-main.1479.pdf)) |
| `issai/GPQA_Kazakh_Russian` | 1,192 kk | CC-BY-4.0 | 69.8 (stock 70.9); AVL-34B 58.77 |
| `issai/PolyMath_Kazakh` | n/p (PolyMath subset, `*-kk-*` ids) | not stated | ISSAI card warns Kazakh-35B is −5.8 pts vs stock |
| `issai/RAGBench_Kazakh` | 11,431 (12 subsets, incl. 2,144 finqa + 3,258 tatqa) | CC-BY-4.0 | judge-scored; AVL-34B 69.98, Qolda-NT 54.95 |
| `issai/IFBench_Kazakh` | 444 | apache-2.0 | **no published scores** — see §4.1 |

Vision ports live in [`issai/qolda-vision-benchmarks`](https://huggingface.co/collections/issai/qolda-vision-benchmarks)
(AI2D_Kazakh 3,088; RealWorldQA kk/ru 1,530; MathVista_Kazakh 1,000; OCRBench-Kazakh 441).

### 1.9 Small/classical Kazakh task sets

| Benchmark | What | Size | Metric | Best published | Source |
|---|---|---:|---|---|---|
| **KazSAnDRA** | review sentiment: polarity (PC, binary) + star score (SC, 1–5), 4 domains | 180,064 reviews; PC test 16,797 (82.2% positive) | macro-F1 | PC **0.81** (XLM-R, RemBERT), SC **0.39** (same) | [LREC-COLING 2024](https://aclanthology.org/2024.lrec-main.844.pdf), [GitHub IS2AI/KazSAnDRA](https://github.com/IS2AI/KazSAnDRA), [HF `issai/kazsandra`](https://huggingface.co/datasets/issai/kazsandra) (gated), CC BY 4.0 |
| **KazNERD** | NER, 25 entity classes, IOB2, TV news | 112,702 sentences / 1,302,352 tokens / 136,333 entities; test 11,307 | micro-F1 (seqeval) | **XLM-RoBERTa 97.22** test (P 97.09 / R 97.35); macro-F1 89.53 | [LREC 2022](https://aclanthology.org/2022.lrec-1.44.pdf), [GitHub](https://github.com/IS2AI/KazNERD), CC BY 4.0 |
| KazNERD1/2, KazNERD_H | *speech* re-recordings of KazNERD sentences (ASR, not NER) | 48,786 synth utt; **531 human utt** | WER | n/p (IEEE full text closed) | [HF `issai/KazNERD_H`](https://huggingface.co/datasets/issai/KazNERD_H), MIT, UBMK 2025 doi 10.1109/UBMK67458.2025.11242232 |
| **NIS Math** | grade-6 Kazakh school math, 4 options | 100 | accuracy (chance 0.25) | Qolda-AVL-34B **98.00**; GPT-4 0.48; Qwen-2.5-Instruct-7B 38.0 | [SIGTURK 2024 Table 4](https://aclanthology.org/2024.sigturk-1.8.pdf), [Sherkala Table 4](https://arxiv.org/pdf/2503.01493); data [`issai/LLM_Eval_Using_Kazakh`](https://huggingface.co/datasets/issai/LLM_Eval_Using_Kazakh) (no license declared). Item #44 is a known bad key |
| **kkCOPA** | causal commonsense, 2-way | 500 | accuracy (chance 0.5) | GPT-4 0.82 (kk prompt), Gemini 0.81; AVL-34B 79.60 | same; items #574/#992 mistranslated |
| **kkWikiSpell** | spelling correction | 160 | token Jaccard | 0.08 for all 7 models (36/160 ideal, GPT-4) | same |
| TruthfulQA-kk / CrowS-Pairs-kk | truthfulness / bias, Google-translated | 817 / 1,508 | accuracy | Sherkala-Chat 52.5 / Sherkala-base 54.3; almost everything sits near 50% — barely separating | [Sherkala Tables 3–4](https://arxiv.org/pdf/2503.01493); hosted location **unverified**, no license |
| **KazLawBench v0.3** | first bilingual RU+KK legal benchmark on adilet.zan.kz codes + Supreme Court bulletins, 7 tasks / 3 cognitive levels | 3,098 records (**1,296 kk**); test kk: 100 + 39 + 98 + 20 + 2 + 1 + 1 | ROUGE-L+EM, F1, accuracy, MRR/Hit@k | Claude Opus 4.7 direct: bar-MCQ kk **1.000**, article recall kk 0.111 (ru 0.200), term definition BERTScore kk 0.892, case retrieval Hit@10 kk 0.000 (n=1) | [`raiym76/kazlawbench`](https://huggingface.co/datasets/raiym76/kazlawbench), CC-BY-NC-SA-4.0, 2026-05-18 |
| **KazLLM 1.0 ISSAI suite** | ARC, GSM8K, HellaSwag, MMLU, Winogrande, DROP in kk/ru/en | n/p numerically (results are PNGs on the page) | accuracy | only mirrored as numbers inside AlemLLM's tables (§3.4) | <https://issai.nu.edu.kz/kazllm/>, 2024-12-24; dataset `issai/KazLLM_Benchmark_Dataset` CC-BY-NC-4.0 |
| FRAPPE / stereotype-bias / culturally-aware MMT (Turmakhan et al., ACL 2025–2026) | framing & propaganda in kk; bilingual stereotype bias; cultural MMT | see papers | — | n/p per-model, not LLM boards | [author page](https://aclanthology.org/people/diana-turmakhan/) |

---

## 2. Safety benchmarks (Kazakh)

### 2.1 Qorǵau — Kazakh/Russian bilingual safety (ACL Findings 2025)

| Field | Value |
|---|---|
| What it measures | share of *safe* responses to risk prompts, 6 risk areas / 17 harm types, incl. **Kazakhstan-specific sensitivities** (politics, history, legal/rights) and original/indirect-attack/over-sensitivity variants |
| Size | **3,786 Kazakh** + 4,383 Russian prompts (plus a 500-pair kk↔ru code-switched subset); 41,646 Kazakh responses collected; English source set 939 questions (count from [Sherkala §4.3](https://arxiv.org/pdf/2503.01493), which reuses the same resource) |
| Link | [ACL Findings 2025](https://aclanthology.org/2025.findings-acl.507.pdf) (Goloburda, Turmakhan et al.); no HF dataset we could open (search `qorgau` → 0 hits). Runs inside QoldaEvalKit as `qorgau` |
| Scoring | GPT-4o automatic judge against a per-risk question set; human agreement with GPT-4o labels **70.7% on Kazakh** (71% Russian) |

Top published safety rates (% safe, Kazakh prompts — Qorgau paper Table 2, 2025):

| Rank | Model | Kazakh | Russian | English |
|---:|---|---:|---:|---:|
| 1 | **Claude (3.5 Sonnet)** | **96.5** | 93.5 | 98.6 |
| 2 | GPT-4o | 95.8 | 87.6 | 95.7 |
| 3 | YandexGPT | 90.7 | **93.6** | 80.3 |
| 4 | **issai/LLama-3.1-KazLLM-1.0-70B** | 88.1 | 87.5 | 97.2 |
| 5 | Llama-3.1-70B | 88.0 | 85.5 | 95.7 |
| 6 | Sherkala-Chat (8B) | 87.1 | 85.0 | 96.0 |
| 8 | Qwen-2.5-7B | 86.2 | 85.1 | 88.1 |
| 10 | KazLLM-1.0-8B | 74.8 | 78.0 | 94.5 |
| 11 | Aya-101 | **72.4** | 84.5 | 96.6 |

Code-switching (Table 5, 500 pairs): GPT-4o 492 safe / 8 unsafe (kk) vs 481 / 19 (code-switched);
Claude 491 / 9 → 484 / 16; YandexGPT 435 / 65 → 464 / 36. **Kazakh is where all models are weakest, and
mixing in Russian changes which model is safest** — directly relevant to a Freedom Broker judge that sees kk/ru
mixed transcripts.

Sherkala's own paper (COLM 2025) re-ran essentially this dataset with **relaxed criteria (1–3 violations allowed)**
and got different absolute numbers — Claude 98.6, GPT-4o 98.1, YandexGPT 93.4, Sherkala-Chat 91.9,
KazLLM-8B 81.2, Aya-101 78.8 ([Table 5](https://arxiv.org/pdf/2503.01493)). Treat the two tables as **different
metrics with the same ranking order**, not as replication.

### 2.2 KZ-SafetyPrompts (LREC 2026 SIGUL workshop)

5,717 prompts **written natively in Kazakh** (Cyrillic), 11 categories, youth/teen register, English
translations included; keyword-based refusal detection. Only baseline published: GPT-4o overall refusal
**28.2%** (range 5.5% Family → 53.8% Regulated goods; Health 50.5, Self-harm 47.3, Violence 44.0,
Child exploitation 25.3, Racist content 8.8) on a stratified 1,001-prompt sample (91/category) —
[Zaghouani et al., 2026](http://www.lrec-conf.org/proceedings/lrec2026/workshops/sigul/pdf/2026.sigul-1.12.pdf), Table 5.
The authors flag the detector as coarse: it cannot separate harmful compliance from over-refusal.

Also: `farabi-lab/Content_Moderation_and_Safety_Kazakh_Context`
([HF](https://huggingface.co/datasets/farabi-lab/Content_Moderation_and_Safety_Kazakh_Context), CC-BY-NC-4.0,
gated=manual, 2026-07-30) — 10K–100K rows, no published per-model numbers we could open.

---

## 3. Leaderboards that rank models on Kazakh

### 3.1 `kz-transformers/kaz-llm-lb` / `kaz-llm-lb2` (Horde / DSML)

* Space: <https://huggingface.co/spaces/kz-transformers/kaz-llm-lb> (12 likes, created 2024-12-10, last modified
  2026-08-12, **PAUSED, "Flagged as abusive"**); [`kaz-llm-lb2`](https://huggingface.co/spaces/kz-transformers/kaz-llm-lb2)
  is a code copy, **SLEEPING**. Live state lives in gated datasets `kaz-llm-lb-metainfo` and `s-openbench-eval`
  (**HTTP 401**), so the committed seed is the only public snapshot.
* Tasks (zero-config MC, 4–8 options): `mmlu_translated_kk` ([14,038 test](https://huggingface.co/datasets/kz-transformers/mmlu-translated-kk)),
  `kk_constitution_mc` ([414](https://huggingface.co/datasets/kz-transformers/kazakh-constitution-mc)),
  `kk_dastur_mc` ([1,005](https://huggingface.co/datasets/kz-transformers/kazakh-dastur-mc)),
  `kk_*_unt_mc` — 8 ЕНТ subjects
  ([kazakh_and_literature 4,688 / history_of_kazakhstan 3,260 / english 2,197 / geography 1,718 / biology 1,536 / world_history 1,228 / human_society_rights 223](https://huggingface.co/datasets/kz-transformers/kazakh-unified-national-testing-mc)).
  apache-2.0. Submission harness: [`horde-research/horde-common`](https://github.com/horde-research/horde-common)
  `scripts/mc-eval-simplified-inference.py`, "must not be modified", anti-cheat policy deletes edited files.
* Scores — mean over the 10 MC tasks from
  [`seed_models.json`](https://huggingface.co/spaces/kz-transformers/kaz-llm-lb2/raw/main/seed_models.json) (22 unique
  models, read 2026-11-08). **This is a static seed, not the live board**:

| Model | mean | mmlu_kk | constitution | dastur | kk&lit | biology |
|---|---:|---:|---:|---:|---:|---:|
| gpt-4o | **0.728** | 0.742 | 0.841 | 0.798 | 0.679 | 0.698 |
| claude-3-5-sonnet | 0.718 | 0.734 | 0.862 | 0.795 | 0.655 | 0.669 |
| gemini-1.5-pro | 0.684 | 0.738 | 0.816 | 0.738 | 0.557 | 0.667 |
| amazon nova-pro-v1 | 0.641 | 0.679 | 0.775 | 0.718 | 0.466 | 0.620 |
| gpt-4o-mini | 0.627 | 0.562 | 0.790 | 0.755 | 0.495 | 0.607 |
| gemini-1.5-flash | 0.614 | 0.634 | 0.749 | 0.706 | 0.476 | 0.622 |
| meta-llama/Llama-3.3-70B-Instruct | 0.609 | 0.611 | 0.795 | 0.708 | 0.413 | 0.563 |
| google/gemma-3-27b-it | 0.581 | 0.607 | 0.739 | 0.661 | 0.406 | 0.553 |
| **issai/LLama-3.1-KazLLM-1.0-70B** | 0.575 | 0.615 | 0.795 | 0.699 | 0.293 | 0.545 |
| RedHatAI/Llama-3.3-70B-w8a8 | 0.563 | 0.583 | 0.790 | 0.674 | 0.381 | 0.506 |
| **inceptionai/Llama-3.1-Sherkala-8B-Chat** | 0.528 | 0.474 | 0.479\* | 0.722 | 0.417 | 0.440 |
| yandex-gpt | 0.525 | 0.398 | 0.703 | 0.616 | 0.495 | 0.437 |
| **issai/LLama-3.1-KazLLM-1.0-8B** | 0.506 | 0.461 | 0.737 | 0.656 | 0.335 | 0.419 |
| google/gemma-2-9b-it | 0.497 | 0.465 | 0.645 | 0.539 | 0.334 | 0.444 |
| meta-llama/Llama-3.1-8B-Instruct | 0.476 | 0.389 | 0.679 | 0.658 | 0.323 | 0.399 |
| Qwen/Qwen2.5-7B-Instruct | 0.396 | 0.383 | 0.543 | 0.425 | 0.260 | 0.333 |
| IrbisAI/Irbis-7b-v0.1 | 0.286 | 0.251 | 0.413 | 0.466 | 0.281 | 0.141 |
| TilQazyna/llama-kaz-instruct-8B-1 | 0.267 | 0.246 | 0.394 | 0.321 | 0.267 | 0.251 |
| dummy-random-baseline | 0.219 | 0.230 | 0.251 | 0.245 | 0.209 | 0.223 |

\* the Sherkala and DeepSeek-R1-distill rows have visibly mis-assigned keys in the seed file; read those two rows
as indicative only. **Nothing newer than Llama-3.3/Gemma-3/Qwen-2.5 is on this board** — no 2026 model, no
Gemma-4, no Qwen3.5.

### 3.2 Kaz Offline LLM Arena (Horde Research) — the only Kazakh "arena"

* Space: <https://huggingface.co/spaces/kz-transformers/kaz-offline-arena> (11 likes, last modified 2025-04-30,
  runtime unusable: host **HTTP 502**, `runtime/stats` **HTTP 404**).
* Method ([repo](https://github.com/horde-research/Kaz-Offline-Arena),
  [`src/about.py`](https://huggingface.co/spaces/kz-transformers/kaz-offline-arena/raw/main/src/about.py)): for each of
  500 arena questions a model answers 5 question types (WHY / WHAT / HOW / DESCRIBE / ANALYZE), an
  **LLM judge returns chain-of-thought + a 0–100 score** as Pydantic-validated JSON, and rankings come from a
  **Bradley–Terry (Elo) model** computed in the Space. Judge model in the code defaults to
  `gpt-4o` ([`judge.py`](https://raw.githubusercontent.com/horde-research/Kaz-Offline-Arena/master/judge.py)).
* Question set: [`kz-transformers/arena-offline-qa`](https://huggingface.co/datasets/kz-transformers/arena-offline-qa)
  — splits train 4,666 / test 1,499 / **arena 500**, columns `group/category/subcategory/source/text/*_QS/*_ANS/reward`;
  rows are Kazakh Wikipedia/government prose with generated questions (`source: "wiki parsing"`). No license declared.
* Standings: **unreadable**. Results live in gated `kz-transformers/offline-data-results` (**HTTP 401**); no result
  JSONs are committed in the repo. The only public statements are the DSML Telegram summaries
  (2025-05: Gemma «стабильно сильные», Sherkala-8B second, ISSAI good MC / weak generation —
  [t.me/dsmlkz_news/1121](https://t.me/dsmlkz_news/1121)) — qualitative, no numbers.
* It is **not human preference** and not multi-turn: single-turn, offline, LLM-judged.

### 3.3 KazBench (Yersultan04, community) — 6-task Kazakh benchmark + sleeping board

* Repo <https://github.com/Yersultan04/kazbench> (MIT code), data
  [`Yersultan03/kazbench`](https://huggingface.co/datasets/Yersultan03/kazbench) (CC-BY-4.0),
  Space <https://huggingface.co/spaces/Yersultan03/kazbench-leaderboard> (**SLEEPING**, static JSONs only).
* Tasks: `knowledge_mc`, `reading_comprehension`, `grammar_morphology`, `sentiment` (accuracy),
  `translation` (chrF kk→en/kk→ru), **`instruction_following` (LLM-judge 0–1, self-judge: "treat as soft")**;
  overall = macro-average ×100. Public DEV = 600 items (100/task) of which **296 native-validated**; private
  TEST = 180 held out for anti-contamination.
* DEV board (generated 2026-06-17, v0.1.0, provisional):

| Model | Overall | KMC | RC | GM | Sent | Trans | **IF** |
|---|---:|---:|---:|---:|---:|---:|---:|
| anthropic/claude-3.5-haiku | **91.50** | 96.0 | 100.0 | 97.9 | 88.2 | 86.1 | **80.7** |
| openai/gpt-4o-mini | 88.30 | 96.0 | 100.0 | 91.7 | 96.1 | 92.3 | 53.8 |
| meta-llama/llama-4-scout-17b | 87.53 | 96.0 | 87.5 | 87.5 | 100.0 | 92.1 | 62.0 |
| google/gemini-2.5-flash | 84.15 | 90.0 | 100.0 | 91.7 | 100.0 | 88.2 | 35.0 |
| qwen/qwen-2.5-72b-instruct | 74.54 | 88.0 | 97.9 | 75.0 | 84.3 | 79.8 | 22.1 |
| llama-3.1-8b-instant | 64.94 | 72.0 | 95.8 | 77.1 | 60.8 | 26.4 | 57.6 |
| dummy | 22.97 | 26.0 | 25.0 | 25.0 | 33.3 | 8.5 | 20.0 |

* **Real-data re-run 2026-06-20** ([REAL_DATA_LEADERBOARD.md](https://github.com/Yersultan04/kazbench/blob/master/results/real/REAL_DATA_LEADERBOARD.md),
  real ЕНТ items + real reviews, n=60/task, `validated:false`): gemini-2.5-flash **87.5** (KMC 86.7, sentiment 88.3),
  llama-3.3-70b 74.2, gpt-4o-mini 71.7, gpt-oss-120b 71.7, llama-4-scout 70.8, claude-haiku-4.5 70.0,
  while **qwen3-32b (25.0) and llama-3.1-8b (26.7) collapse to the 25% chance floor**. The maintainers' own point:
  synthetic DEV inflates; the leader changes on real data.

### 3.4 AlemLLM / Astana Hub vendor board

`astanahub/alemllm` ([HF](https://huggingface.co/astanahub/alemllm), gated **HTTP 401**, created 2025-07-29,
28 likes, 247B/22B-active DeepSeek-MoE, kk/ru/tr/en) publishes its tables in the unmodified mirror
[`Sherkhan243/alemllm-GGUF`](https://huggingface.co/Sherkhan243/alemllm-GGUF). Benchmarks are the ISSAI KazLLM suite
(ARC, GSM8K, HellaSwag, MMLU, Winogrande, DROP), no prompt/few-shot/judge details:

| Model | Kazakh avg | MMLU | ARC | GSM8k | HellaSwag | Winogrande | DROP |
|---|---:|---:|---:|---:|---:|---:|---:|
| **AlemLLM** | **0.826** | 0.757 | 0.949 | 0.917 | 0.775 | 0.837 | 0.719 |
| Yi-Lightning | 0.812 | 0.720 | 0.940 | 0.880 | 0.820 | 0.852 | 0.660 |
| DeepSeek-R1 | 0.798 | 0.753 | 0.868 | 0.937 | 0.680 | 0.764 | 0.784 |
| GPT-4o | 0.776 | 0.730 | 0.940 | 0.900 | 0.830 | 0.704 | 0.550 |
| **KazLLM-1.0-70B** | 0.766 | 0.660 | 0.920 | 0.770 | 0.790 | 0.806 | 0.650 |
| DeepSeek-V3 37A | 0.715 | 0.650 | 0.900 | 0.890 | 0.640 | 0.628 | 0.580 |
| Llama-3.1-70B-instruct | 0.639 | 0.610 | 0.820 | 0.780 | 0.520 | 0.585 | 0.520 |
| Russian average, for reference | AlemLLM **0.848** > DeepSeek-R1 0.845 > QwQ-32B 0.840 > GPT-4o 0.808 > KazLLM-70B 0.748 | | | | | | |

**Self-reported; no third-party reproduction anywhere.** It is also, of all the boards in this document, the only
one where a Kazakh-trained model ranks above both DeepSeek-R1 and GPT-4o in both languages. Note the suite contains
no Kazakh-specific knowledge at all — it is translated MMLU/ARC/GSM8K, so it measures the same thing as the Qolda
ports. License is contradictory between sources: the HF API tag says `apache-2.0`, the (gated) card's license link
declares an "astanahub-alemllm-license" that is research/non-commercial only.

### 3.5 NITEC / Alem.Cloud Kazakh benchmark (Dias Ilyas, ~2026-09)

The only published 2026-generation model ranking on Kazakh. Not a hosted board — a LinkedIn post with a
run description, credited to NITEC (Alibek Sailanbayev) with benchmark owner **Mukhammed Togmanov (Horde
Research)**, executed on the Alem.Cloud cluster
([post](https://www.linkedin.com/posts/diasilyas_we-benchmarked-9-foreign-open-source-llms-activity-7500170267021873152-rYFh),
[earlier "9 modern opensource LLMs" version](https://www.linkedin.com/posts/diasilyas_we-benchmarked-9-modern-opensource-llms-on-activity-7490731949439852544-EF3e)
— that second URL returns an empty body to an anonymous fetch, so only the first post's text is cited here.)
Data: **KazMMLU 9,870 + KazBench-KK 7,111**, zero-shot, **Kazakh-language prompts, temperature 0.0**, every model
in thinking and non-thinking mode; combined score is question-count-weighted.

| Rank | Model | Combined | Notes from the post |
|---:|---|---:|---|
| 1 | Kimi-K3 | **84.05** | KazMMLU 87.10 → 87.26 thinking (moves <0.2) |
| 2 | DeepSeek-V4-Pro | 83.28 | **+6 pp from thinking on KazMMLU** |
| 3 | GLM-5.2 | 82.46 | |
| 4 | Kimi-K2.6 | 80.41 | |
| 5 | Qwen3.6-35B-A3B | 78.20 | |
| 6 | DeepSeek-V4-Flash | 76.94 | |
| 7 | **Gemma-4-31B** | **74.75** | |
| 8 | GPT-OSS-120B | 69.02 | *loses* accuracy with thinking on, especially KazBench-KK |
| 9 | Qwen3-4B-Instruct | 53.45 | |

No Kazakh-adapted model (KazLLM, Sherkala, AlemLLM, issai Qwen-*-Kazakh) was run. Weights:
secondary source, no public result file — [INFERENCE-grade for exact numbers, solid for the ranking].

### 3.6 Boards that do **not** cover Kazakh

* **MERA** (<https://mera.a-ai.ru/en/text/leaderboard>) — Russian multi-task suite; the fetched leaderboard page
  contains no Kazakh mention and there is no kk track. Our Russian reference board only.
* **Open LLM Leaderboard / HF "leaderboard" Spaces** — no Kazakh task set.
* **DSML.KZ** runs no benchmark; it amplifies the kz-transformers boards and the arena
  ([news mirror](https://t.me/dsmlkz_news/1092), [site](https://dsml.kz/en/news/50e817b0-5e86-4040-8897-209542fa9dcc)).
  Its only benchmark-adjacent post is "Open datasets for Kazakh" (2026-08-18,
  [dsml.kz](https://dsml.kz/en/news/bafa032a-3687-4c19-9474-5b5037a93f58)) pointing at
  [`Allessyer/awesome-kaz-datasets`](https://github.com/Allessyer/awesome-kaz-datasets).
* **`stukenov/kaz-llm-lb`** — `unverified (HTTP 401)`; `/api/spaces?author=stukenov` returns nothing.

---

## 4. Instruction-following, chat and preference (closest to our task)

### 4.1 Marco-Bench-MIF — a real (localized, not translated) Kazakh IFEval

**This is the only Kazakh instruction-following benchmark with published per-model numbers.**
ACL 2025 long paper ([arXiv 2507.11882](https://arxiv.org/abs/2507.11882),
[ACL](https://aclanthology.org/2025.acl-long.1172.pdf)), data
[`ATH-MaaS/Marco-Bench-MIF`](https://huggingface.co/datasets/ATH-MaaS/Marco-Bench-MIF) (apache-2.0, not gated,
`kk.jsonl`). It **extends Google IFEval** (arXiv 2311.07911) to 30 languages, **541 instruction-response pairs per
language**, same `instruction_id_list` verifiable checks (`length_constraints:number_words`,
`punctuation:no_comma`, `detectable_format:json_format`, …) — rule-based, **no LLM judge**. Kazakh is one of the
24 languages with **full cultural localization** (prompts reference Panfilov Park, Kazakhstan's oblast system).
Paper Table 3, **Kazakh column** (average of prompt/instruction × strict/loose; paper's overall-language avg 60.8):

| Model | kk |
|---|---:|
| Claude 3.5 Sonnet | **75.6** |
| GPT-4o | 74.8 |
| GPT-4o-mini | 70.0 |
| Qwen-Max | 66.7 |
| Gemini 1.5 Flash | 66.4 |
| Qwen-Plus | 63.9 |
| LLaMA-3.3-70B | 64.2 |
| Qwen2.5-72B | 59.0 |
| Gemma2-27B | 57.3 |
| Mistral-Large | 49.2 |
| LLaMA-3.1-70B | 45.9 |
| Qwen2-72B | 44.2 |
| Qwen2.5-14B | 43.3 |
| Gemma2-9B | 42.5 |
| Qwen2.5-7B | 35.7 |
| Aya-expanse-32B | 32.4 |
| LLaMA-3.1-8B | 26.1 |
| Ministral-8B | 23.8 |
| EuroLLM-9B | 24.0 |
| Aya23-8B | **13.7** |
| *mean over models* | **44.8** (kk is the worst but one; Yoruba 29.2; all-language mean 60.8) |

Paper's reading: kk and yo are the "extremely-hard" languages where **even GPT-4o scores under 60%**; **Turkish
accuracy predicts Kazakh accuracy at r = 0.89** (transfer inside the Turkic family).
Caveat we could not resolve: the paper never states which of its four metrics (prompt-level / instruction-level ×
strict / loose) Table 3's per-language column reports, and its prose "<60% for GPT-4o on kk" does not match the
74.8 in the table — so treat the column as a relative ordering, not an absolute pass rate. Both readings agree on
the ordering: closed frontier > 70B open > 27B > 7–9B, and the Kazakh-tuned multilingual Aya family is at the bottom
(Aya-expanse-32B 32.4, Aya23-8B 13.7). No 2026 model (GPT-5, Claude 4/5, Gemini 3, Qwen3.x) has a published
number here.

### 4.2 IFBench_Kazakh — ISSAI's constraint set, unscored

[`issai/IFBench_Kazakh`](https://huggingface.co/datasets/issai/IFBench_Kazakh) — 444 samples, test-only,
apache-2.0, created 2026-03-26, machine-translated from **THU-KEG/IFBench** (an instruction-following *reward-model*
set, arXiv 2502.19328 — this is **not** AI2's IFBench and **not** Google IFEval). Fields: `instruction_kk`,
`original_instruction_kk`, `chosen_content_kk`, `rejected_content_kk`, `llm_constraints_kk`, `code_constraints_kk`.
QoldaEvalKit scores it with **one GPT judge answering 0/1 over the listed constraints**; the Kazakh "code
constraints" are text (`дәл 150 сөз | checkers: дәл 150 сөз`), and **nothing executes them**
([`core/scoring/judge.py`](https://raw.githubusercontent.com/IS2AI/QoldaEvalKit/main/core/scoring/judge.py)).
**Published scores: none** — not on the Qwen3.5-*-Kazakh cards, not on the Qolda cards.

### 4.3 Kazakh chat/dialogue generation (GPT-4o-as-judge, MT-Bench and Vicuna translated)

The only published Kazakh *generation* scores come from the Sherkala-Chat paper
([arXiv 2503.01493v2](https://arxiv.org/pdf/2503.01493), COLM 2025): Vicuna-Instructions-80 and
MT-Instructions-80 machine-translated to Kazakh/Russian, plus **Gov/Wiki, 1,000 new Kazakh generation samples**
from Cultural Wiki + gov.kz (from Laiyk et al., ACL 2025, [arXiv 2502.13647](https://arxiv.org/abs/2502.13647)).
Temperature 0.3, repetition penalty 1.2, **GPT-4o judges 0–10 (and judges itself)**. Paper Table 8:

| Model | MT-kk | Vicuna-kk | MT-ru | Vicuna-ru | MT-en | Vicuna-en |
|---|---:|---:|---:|---:|---:|---:|
| **GPT-4o (judge)** | **8.81 ±1.51** | **9.32 ±0.61** | 8.89 | 9.79 | 8.36 | 9.03 |
| Sherkala-Chat-8B | 5.99 ±2.73 | 7.39 ±1.89 | 1.02 | 0.97 | 5.78 | 6.55 |
| KazLLM-1.0-8B | 3.98 | 4.88 | 0.72 | 0.28 | 6.00 | 6.66 |
| Llama-3.1-8B-Instruct | 3.76 | 3.75 | 0.85 | 0.82 | 6.55 | 7.41 |
| Qwen-2.5-7B-Instruct | 3.52 | 3.23 | **5.81** | **6.05** | **7.40** | **8.06** |

Pairwise (their Fig. 4): Sherkala-Chat beats KazLLM-8B **60 wins / 1 tie / 19 losses** on MT-kk and
57 / 2 / 21 on Vicuna-kk. Reading: among 8B-class Kazakh models the ranking is Sherkala > KazLLM > Llama > Qwen,
but the best open Kazakh generator still sits ~2–3 points below GPT-4o, and **Sherkala is near-zero on Russian**.
Gov/Wiki bars are only in a figure — **unverified numerically**; the paper says every model scores lower there
than on MT/Vicuna.

Human evaluation exists only in Laiyk et al. (ACL 2025): 3 native-speaker annotators rating **generated training
instructions** on 1–5 Likert (GPT-4o 4.38 correctness / 4.29 completeness / 4.04 fluency; Gemini 1.5 3.85/3.64/3.32;
Claude 3.74/3.48/3.09; Llama-3.1-70B 3.54/3.45/3.07; inter-annotator Pearson 0.68–0.70), and a 100-conversation
multi-turn continuation preference test (figure only, no numbers). Task-level fine-tune results (ROUGE-L, 500-question
test, [`nurkhan5l/kazakh-ift`](https://huggingface.co/datasets/nurkhan5l/kazakh-ift), 10,600 manually verified pairs —
GovSet 6,200 + CultSet 4,400): Gemma-2-9b-it 15.76→24.87 (CultSet) and 16.12→25.10 (GovSet),
Falcon-3-10b 25.96→27.98 / 26.17→28.70, Qwen-2.5-7b **27.64→26.63 / 30.27→28.42 (it got worse)**.

### 4.4 What does not exist (negative results, searched in EN/RU/KK)

* No Kazakh **human-preference** arena; no Kazakh subset of LMArena/Chatbot Arena we could verify
  (`lmsys/arena-language-battles` → **HTTP 401**, language list unreadable).
* No released Kazakh **MT-Bench**, **AlpacaEval**, **Arena-Hard**/m-ArenaHard Kazakh, **FollowBench** Kazakh.
* No **KOBS / KazOpenBookScore** — the name returns nothing findable; treat as non-existent.
* No Kazakh reward-model / pairwise-preference benchmark. The nearest thing to preference data is
  `IFBench_Kazakh`'s chosen/rejected pairs (machine-translated, constraint-based).
* Closest vision-language analogue: m-RewardBench extension adding Kazakh to 23 languages,
  [Findings of ACL 2026](https://aclanthology.org/2026.findings-acl.1746.pdf) (multimodal judge, not text chat).
* A separate 23-language VL judge result aside, **no published Kazakh benchmark measures model-as-judge ability**.

---

## 5. Translation benchmarks (kk)

| Benchmark | What / size | Link | Best published |
|---|---|---|---|
| **FLORES-200 / FLORES+ `kaz_Cyrl`** | news-domain MT eval, 3,001 English sentences (997 dev / 1,012 devtest / 992 test) | [flores200 README](https://github.com/facebookresearch/flores/blob/main/flores200/README.md), [`facebook/flores`](https://huggingface.co/datasets/facebook/flores) (gated), successor [`openlanguagedata/flores_plus`](https://huggingface.co/datasets/openlanguagedata/flores_plus) CC-BY-SA-4.0 | see rows below |
| FLORES-101, 500 sentences, BLEU (0–1) | LLM MT, SIGTURK 2024 | [paper Table 5](https://aclanthology.org/2024.sigturk-1.8.pdf) | kk→en Google **0.35**, GPT-4 0.28–0.29, AYA 0.14–0.25, Gemini 0.22–0.23, LLaMA-2 0.00–0.04; kk→ru Google 0.24, GPT-4 0.20–0.21 |
| **KazParC** + Tilmash | human-translated kk/en/ru/tr corpus, **371,902 pairs** (HF card says 372,164 — unreconciled), domains: media 32.4% / general 25.5% / legal 20.8% / edu 12.4% / fiction 8.9%; test 4,750 lines per pair | [arXiv 2403.19399](https://arxiv.org/abs/2403.19399), [LREC-COLING 2024](https://aclanthology.org/2024.lrec-main.842/), [GitHub IS2AI/KazParC](https://github.com/IS2AI/KazParC), [`issai/kazparc`](https://huggingface.co/datasets/issai/kazparc) (gated, HTTP 401), [`issai/tilmash`](https://huggingface.co/issai/tilmash) | FLORES BLEU + chrF (BLEU / chrF): EN→KK Google 0.20 / 0.60 = Tilmash **0.20 / 0.60** > Yandex 0.18 / 0.58 > NLLB-distilled-1.3B 0.11 / 0.49; RU→KK Google 0.13 / 0.54 > Tilmash 0.13 / 0.54 > NLLB 0.08 / 0.49 |
| **NTREX-128 `kaz`** | en→kk news, 1,997 sentences / 42k words per language, CC BY-SA 4.0 | [paper, SUMEval 2022](https://aclanthology.org/2022.sumeval-1.4.pdf), [GitHub](https://github.com/MicrosoftTranslator/NTREX) | **No published per-model Kazakh score found (n/p).** The authors recommend NTREX for en→X only, so kk→en use is discouraged by design |
| **LoResMT 2026 (ru→kk)** | 4,626 sentence pairs (half public / half private), chrF1, zero-shot | [Shanshin, LoResMT 2026 pp. 213–216](https://aclanthology.org/2026.loresmt-1.19.pdf) | **`deepvk/kazRush-ru-kk` 76.77 public / 76.24 private (80.05 / 80.28 after cleaning)** ≫ `facebook/nllb-200-3.3B` 54.56 > `translategemma-27b-it` 51.48 > **`issai/LLama-3.1-KazLLM-1.0-8B` 51.38** > PolynomeAI/Llama-3.1-8B-kkru 50.35 > translategemma-12b 48.02 > 4b 39.59 > tencent/HY-MT1.5-7B 33.23 (emits Arabic-script Kazakh) > copy-the-Russian 21.61 |
| Kazakh MT + LoRA | FLORES zero-shot, Seed-X-Instruct-7B + adapter | [NLPIR 2025 / Springer](https://link.springer.com/chapter/10.1007/978-3-032-20897-2_1) | X→KK sub-1 BLEU → **17.1**, 18.03 with KK-LM + synthetic; full tables paywalled — `unverified` |

**Kazakh COMET/XCOMET on FLORES: no published per-model table found.** No `INCLUDE`-MT Kazakh table either.

---

## 6. Cross-benchmark summary

Empty cell = n/p. "arena" = the Kazakh generation/preference signal (§4.3, §3.2, DSML notes).
**доступна нам** = we can call it today.

| Model | KazMMLU | KazCulture | Belebele-kk | KazBench-KK | Marco-MIF-kk (IF) | Qorgau safety-kk | arena / generation | AlemLLM-suite avg |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| **GPT-5** | **92.5** | **77.3** | n/p | n/p | n/p | n/p | n/p | n/p |
| Gemini-3.1-Flash | 87.4 | 74.2 | n/p | n/p | n/p | n/p | n/p | n/p |
| **GPT-4o** | 76.6 (en prompt) / 76.1 (audit) | 68.9 | n/p | n/p | 74.8 | 95.8 | **judge model of every arena** | 0.776 |
| **GPT-4o-mini** | — | — | n/p | n/p | 70.0 | n/p | — | — |
| **Claude 3.5 Sonnet** | — | — | n/p | n/p | **75.6** | **96.5** | n/p | — |
| Claude 3.5 Haiku | n/p | n/p | n/p | n/p | n/p | n/p | KazBench DEV leader 91.5 | — |
| Claude Opus 5.5 / GPT-6 (our labelers) | n/p | n/p | n/p | n/p | n/p | n/p | our own bench only | — |
| Gemini 2.5 Flash | 78.8 | 58.4 | n/p | n/p | n/p | n/p | KazBench real-data leader **87.5** | — |
| Gemini 1.5 Pro | n/p (mmlu_translated_kk 0.738 on the lb seed) | — | — | — | — | — | weak KazQAD/Gov answers | — |
| DeepSeek V3 | **76.9** (en prompt) / **45.5** (kk prompt) | — | — | — | — | — | — | 0.715 |
| DeepSeek V4-Pro | 83.28 (KazMMLU+KazBench-KK combined) | (in the 83.28) | n/p | (in 83.28) | n/p | n/p | +6 pp from thinking | n/p |
| DeepSeek V4-Flash | 76.94 (combined) | n/p | n/p | n/p | n/p | n/p | n/p | n/p |
| Kimi-K3 | 87.10 KazMMLU alone; 84.05 combined — **top of the 2026 Kazakh board** | n/p | n/p | n/p | n/p | n/p | n/p | n/p |
| GLM-5.2 | 82.46 combined | n/p | n/p | n/p | n/p | n/p | n/p | n/p |
| **gemma-4-31B** (доступна нам) | **74.75 combined (KazMMLU+KazBench-KK)**; nothing at 31B on the Kazakh MC boards | n/p | MMMLU 88.4 (not kk) | n/p | n/p | n/p | DSML: «стабильно сильные» on Kazakh generation; **our own gold best 0.918–0.936** | n/p |
| Gemma-4-E4B-it (think) | 69.2 | 45.9 | n/p | n/p | n/p | n/p | n/p | n/p |
| Gemma-3-27B-it | 0.607 (kk MC board) | — | — | **0.7216** | — | — | n/p | — |
| Gemma-2-27B-it | 57.4 | — | — | — | — | — | n/p | — |
| Qwen3.6-35B-A3B | 78.20 combined | n/p | n/p | n/p | n/p | n/p | n/p | n/p |
| Qwen3.8-27B / 3.8-Flash (available to us) | n/p | n/p | n/p | n/p | n/p | n/p | n/p — but **our gold bench 0.901–0.919** | n/p |
| **stock Qwen3.5-35B-A3B** | 82.6 | 60.3 | **89.4** | n/p | n/p | n/p | n/p | n/p |
| **issai/Qwen3.5-35B-A3B-Kazakh** (доступна нам) | **84.0** | **68.7** | 88.9 | n/p | n/p | n/p | our gold: **0.842** single / 0.767 per_criterion; KZ chats 0.858 (gemma 0.957) | n/p |
| issai/Qwen3.5-9B-Kazakh | 83.1 | 63.4 | 87.9 | n/p | n/p | n/p | n/p | n/p |
| issai/Qwen3.5-4B-Kazakh | 78.5 | 55.4 | 85.6 | n/p | n/p | n/p | n/p | n/p |
| Qwen2.5-72B-Instruct | — | — | — | — | 59.0 | — | KazBench DEV 74.5 | — |
| Qwen2.5-7B (Instruct) | 47.8 | — | 31.1 (loglik) | — | 35.7 | 86.2 | MT-kk 3.52 | — |
| Llama-3.1-KazLLM-1.0-8B | 41.7 | — | 27.8 (loglik) | 0.5656 | — | 74.8 | MT-kk 3.98 | — |
| Llama-3.1-KazLLM-1.0-70B | 0.615 (kk MC board) | — | — | 0.69 | — | 88.1 | DSML: "хорошие MC, слабая генерация" | 0.766 |
| Llama-3.3-70B-Instruct | 0.611 (kk MC board) | — | — | 0.7090 | — | — | n/p | — |
| Sherkala-Chat-8B (MBZUAI) | 45.6 / 48.8 (audit) | 53.8 | 30.6 (loglik) | 0.6909 | — | 87.1 (91.9 under Sherkala's own criteria) | **MT-kk 5.99, Vicuna-kk 7.39** (best 8B) | — |
| **AlemLLM** (доступна нам) | n/p on KazMMLU proper | n/p | n/p | n/p | n/p | n/p | n/p | **0.826** (vendor) |
| issai/Qolda-AVL-34B (VLM) | 78.98 | 62.37 | 88.78 | **0.7005** | n/p | n/p | n/p | n/p |
| issai/Qolda-Think 4B | 66.14 | 47.45 | 82.91 | 0.6112 | n/p | n/p | n/p | n/p |
| gpt-oss-120b | n/p (KazBench real 71.7) | n/p | n/p | n/p | n/p | n/p | 69.02 combined; loses accuracy with thinking | n/p |
| Darmm/darmm-chat-kazakh-8b (QLoRA, 65k kk) | 38.3 (3,000-item sample) | n/p | 39.8 | n/p | n/p | n/p | n/p | n/p |
| Irbis-7b-v0.1 | 0.251 (kk MC board) | — | — | — | — | — | — | — |
| TilQazyna/llama-kaz-instruct-8B-1 | 0.246 | — | — | 0.2768 | — | — | — | — |
| Aya-101 | — | — | 0.63–0.70 | — | 13.7 (Aya23-8B) | 72.4 | strong open-book QA (0.61) | — |
| YandexGPT | 60.2 | — | — | — | — | 90.7 (ru 93.6) | answers only 10–13% of kk QA | — |
| Random / dummy floor | 22.1–25 | ~20 (chance) | 25 | 0.25 | — | — | — | 22.97 (KazBench) |

Reading the columns: **KazMMLU and KazCulture measure textbook knowledge; Marco-MIF measures constraint following;
Qorgau measures refusal behaviour; nothing here measures rubric-scoring of a dialogue.**

---

## 7. Что это значит для нас

**Evidence (sourced).**

1. **Which Kazakh model beats `gemma-4-31B`, and by how much.** The NITEC/Alem.Cloud run is the **only board that
   gives gemma-4-31B a Kazakh number** (KazMMLU 9,870 + KazBench-KK 7,111, Kazakh prompts, temp 0): gemma-4-31B 74.75,
   Kimi-K3 84.05, DeepSeek-V4-Pro 83.28, GLM-5.2 82.46, Kimi-K2.6 80.41, Qwen3.6-35B-A3B 78.20,
   DeepSeek-V4-Flash 76.94 — i.e. **the 2026 frontier open models beat it by 2–9 points on Kazakh knowledge**.
   Our own `issai/Qwen3.5-35B-A3B-Kazakh` was not run on that board, and gemma-4-31B has **no**
   KazMMLU/KazCulture/Belebele-kk score at 31B anywhere else; the only
   Gemma-4 numbers on Kazakh are the tiny E2B/E4B variants (KazMMLU 69.2 at best, three-benchmark mean 65.8)
   in the EMNLP 2026 audit. So on paper the Kazakh specialist beats gemma by ~+15 on KazMMLU and +22 on KazCulture.
   Its 84.0 is the **highest KazMMLU score published for any model we can call today** (only closed GPT-5 92.5 /
   Gemini-3.1-Flash 87.4 and open Kimi-K3 87.10 sit above it), and it is **доступна нам**.
2. **On our actual task, that advantage has not converted, not even on Kazakh chats.** Measured by the integrator on
   2026-11-08 01:00: the same checklist notes, the 60-chat consensus gold plus 20 human rows, runs in
   `bench/results/20261108-005401/` (single) and `…-005403/` (per criterion).

   | judge | all 60 chats | RU (30) | **KZ (15)** | EN (15) | total MAE |
   |---|---|---|---|---|---|
   | `h200-gemma · per_criterion` (control) | **0.939** | 0.921 | **0.957** | 0.957 | 4.51 |
   | `h200-kz` (`issai/Qwen3.5-35B-A3B-Kazakh`) · single | 0.842 | 0.821 | 0.858 | 0.868 | 11.90 |
   | `h200-kz` · per_criterion | 0.767 | 0.797 | 0.710 | 0.766 | 14.29 |

   The Kazakh specialist is **~10 points worse than gemma on judging Kazakh chats**, while being ~15 points better on
   KazMMLU. (The earlier 0.772 in `../benchmark-phase1.md` was a 5-dialog preliminary run.)
3. **Nothing on any Kazakh board measures judging.** ISSAI's harness alone runs 39 Kazakh-scored benchmarks
   (19 text + 8 vision + 5 audio + 1 safety + 6 translation directions, [QoldaEvalKit](https://github.com/IS2AI/QoldaEvalKit));
   we enumerated the published Kazakh suites in §1–§5: none of them scores a model as a judge. The closest
   proxies are Marco-Bench-MIF-kk (verifiable constraint following — the skill our checklist judge needs most,
   and where Claude 3.5 Sonnet 75.6 > GPT-4o 74.8 > … > 8B open models 24–26) and Qorgau safety (where **Claude is
   the safest model in Kazakh, 96.5, and GPT-4o second, 95.8, while KazLLM-8B is 74.8 and Aya-101 72.4**).
   The two LLM-judged Kazakh boards we have (Kaz Offline Arena, Sherkala's MT/Vicuna) use **GPT-4o as the judge**,
   which is a self-preference risk for exactly the models we are choosing between.
4. **The Kazakh-specific models are weak in Russian, the language of most of our chats.** Sherkala-Chat:
   MT-ru 1.02 / Vicuna-ru 0.97 out of 10 (vs 5.99 / 7.39 in Kazakh); Qorgau code-switching shows per-model
   safety flips between monolingual and mixed kk/ru prompts; the issai Qwen-*-Kazakh CPT corpus is
   **50/50 Kazakh:English with no Russian at all** ([base card](https://huggingface.co/issai/Qwen3.5-35B-A3B-Base-Kazakh)).
   `alemai/astanahub/alemllm` is the only Kazakh model whose vendor numbers are strong in **both** (kk 0.826 / ru 0.848),
   and those numbers are unreplicated and self-reported on a translated-English suite.
5. **Scripts can invalidate everything.** ΔCyrillic→Latin averages 16.8 points and reaches −30.4 for Sherkala and
   −21.8 for KazLLM; the audit's authors excluded LLM-as-judge from Latin Kazakh because judge reliability there is
   unestablished.

**[INFERENCE].**

- For a **judge** whose rubric is format-strict and language-mixed, the benchmark evidence that should move us
  is Marco-MIF-kk (constraint following) and Qorgau-kk (calibrated refusal), **not** KazMMLU. Both favour the
  closed frontier (Claude, GPT-4o) over every Kazakh fine-tune, and both are 2024/2025-era — so the honest summary is
  **"no Kazakh-specific model has demonstrated a judging-relevant advantage over gemma-4-31B."**
- The margin that would "matter" for us is set by our own noise, not by these boards: run-to-run reproducibility is
  99.0–99.6% of verdicts and any notes edit moves ±3 verdicts per criterion. On a 480-verdict scale that is
  ±0.6 pp, so a **KazMMLU +15 does not automatically buy ≥2 pp of agreement**, and on our data it bought −10 pp on the Kazakh chats themselves (table above).
- Expect a **split specialist design**, not one judge: a Kazakh-native scorer for the Kazakh-only slices
  (KazMMLU 84.0 / KazCulture 68.7 / Belebele 88.9, and it is free at ~$0.001/eval) plus a strong constraint-follower
  for rubric discipline (gemma per_criterion today, Sonnet/Luna as the cloud fallback). If a single judge must
  cover all three languages, no Kazakh model has evidence for that role today.
- The head-to-head on the Kazakh subset is **done** (table in item 2): gemma 0.957 against 0.858/0.710, so the
  «Kazakh-native scorer for Kazakh slices» design above is refuted on our task. The only open experiment is a
  Latin-Kazakh variant of a few dialogs, to measure the 16.8-point script cliff on our own task; the DEV chats are all in Cyrillic.

---

## 8. Open problems with these sources

- `kz-transformers/kaz-llm-lb-metainfo`, `s-openbench-eval`, `offline-data-results`, `astanahub/alemllm`,
  `issai/kazqad`, `issai/kazsandra`, `issai/kaznerd`, `issai/kazparc`, `issai/KazCulture`,
  `jafarisbarov/KazakhMMLU`, `farabi-lab/…Safety…`, `facebook/flores`, `lmsys/arena-language-battles`:
  **gated, HTTP 401** — quoted from the public mirror, paper table, or HF API metadata only.
- `kz-transformers/kaz-offline-arena` ELO standings: **unreadable** (host HTTP 502, results dataset HTTP 401).
- Mansurova et al. (MDPI *Information* 2025) full KazQAD/RAG table: **HTTP 403**; only abstract numbers cited.
- KazCulture full paper: IEEE Access, paywalled (`unverified`); numbers come from the ISSAI blog post and the
  EMNLP 2026 audit's independent re-run.
- NITEC/Alem.Cloud Kazakh board: LinkedIn post, no result file — **secondary source**.
- "KazBench" names three unrelated things: `kz-transformers/kk-socio-cultural-bench-mc` (KazBench-KK, 7,111),
  `Yersultan03/kazbench` (6-task, 600 DEV items), and ISSAI's "KazBench" column (which is the first of these).
  Check which one a citation means before quoting a number.
