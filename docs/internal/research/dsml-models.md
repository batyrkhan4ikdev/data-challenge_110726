# Which open-weight models the KZ community rates best for Kazakh/Russian (2026)

Written 2026-11-07. Scope: pick a **judge** model for checklist scoring of KZ/RU/EN support chats
out of the models we can actually call. Every number below has a link; `n/p` = nothing published
that I could find. Sources I could not open are named in §4.

## 1. Model table

| Model (our id) | Kazakh evidence | Russian evidence | Source |
|---|---|---|---|
| `qwen3.5-35b-a3b-kazakh` (issai/Qwen3.5-35B-A3B-Kazakh) | **KazMMLU 84.0** (vs 82.6 stock Qwen3.5-35B-A3B), **KazCulture 68.7** (vs 60.3), **Belebele-kk 88.9** (vs 89.4), thinking mode on, card dated Aug 2026 | n/p — the card reports Kazakh + English only; the CPT corpus is 50/50 Kazakh:English, **no Russian** ([base card](https://huggingface.co/issai/Qwen3.5-35B-A3B-Base-Kazakh)). Russian therefore inherits plain Qwen3.5 | [model card](https://huggingface.co/issai/Qwen3.5-35B-A3B-Kazakh) |
| `gemma-4:31b` / `alemai/google/gemma-4-31B` | n/p on any Kazakh benchmark at 31B. The family is 140+ languages, MMMLU 88.4% (multilingual MMLU, not Kazakh). Kazakh-side sibling data: Gemma-4-E4B-it (think) **KazMMLU 69.2 / KazCulture 45.9** (Cyrillic), Oct 2026 EMNLP audit; DSML arena note (2025): "Модели Gemma … стабильно сильные" | **MERA Text 2.0 (RU) 0.369, rank 23/47**, `gemma-4-31B-it-non-reasoning`, 2026-08-25; IFBench-style RU instruction following is its weak spot (IFHardBench 0.585) | [card](https://huggingface.co/google/gemma-4-31B), [EMNLP 2026 audit Table 8](https://aclanthology.org/2026.emnlp-main.1479.pdf), [DSML #1121](https://t.me/dsmlkz_news/1121), [MERA submit 36](https://mera.a-ai.ru/en/text/submits/2.0/36) |
| `alemai/deepseek-ai/DeepSeek-V4.1-Flash` | n/p for V4.1-Flash specifically. Predecessor line is the strongest open model ever scored on KazMMLU: **DeepSeek V3 76.9 avg** (best open, GPT-4o 76.6) and **best of all models in Russian 81.4** at high-school level, ACL 2025 | **MERA Text 2.0 (RU) 0.581, rank 5/47** — best non-proprietary score on the board, submitted by an independent team 2026-10-11, MIT weights; IFHardBench 0.954, RUBIN 0.799 | [KazMMLU, ACL 2025, Table 4 + Fig. 6](https://arxiv.org/html/2502.12829v2), [MERA submit 158](https://mera.a-ai.ru/en/text/submits/2.0/158) |
| `alemai/astanahub/alemllm` (AlemLLM) | **Kazakh leaderboard avg 0.826** (MMLU-kk 0.757, ARC 0.949, GSM8k 0.917) — vendor's own table, ranks above DeepSeek-R1 0.798, GPT-4o 0.776, KazLLM-70B 0.766. Self-reported, not independently reproduced | **Russian leaderboard avg 0.848** — best on that table, ahead of DeepSeek-R1 0.845 / QwQ 0.840 / GPT-4o 0.808. Model languages: kk, ru, tr, en. Same caveat: vendor table | [astanahub/alemllm (gated card)](https://huggingface.co/astanahub/alemllm), numbers mirrored verbatim in [Sherkhan243/alemllm-GGUF](https://huggingface.co/Sherkhan243/alemllm-GGUF) |
| `alemai/Qwen/Qwen3.8-27B`, `qwen3.8-flash-next` | n/p Kazakh. Nearest published same-family Kazakh score is the 35B-A3B line (82.6 KazMMLU, ISSAI card above); Qwen3.5 is documented at 201 languages | **MERA Text 2.0: Qwen3.8-27B 0.394, rank 19/47** (2026); same board: Qwen3.6-27B 0.435 (#13), Qwen3.5-27B 0.422 (#16), Qwen3.6-35B-A3B 0.391 (#20), Qwen3.5-35B-A3B 0.330 (#24). No MERA entry for Qwen3.8-Flash-Next | [MERA Text 2.0 leaderboard](https://mera.a-ai.ru/en/text/leaderboard), [Qwen3.8-27B submit](https://mera.a-ai.ru/en/text/submits/2.0/200) |
| `alemai/Qwen/Qwen3.6-35B-A3B` | n/p (see row above) | **MERA 0.391, rank 20/47**; quantised w4a16 copy 0.387 (#21) | [MERA submit 22](https://mera.a-ai.ru/en/text/submits/2.0/22) |
| `muse-glimmer-30b` (meta-models/Muse-Glimmer-30B) | n/p on any public Kazakh board — the card has no Kazakh or Russian row, says "trained on more than 100 languages" and warns it "has not been evaluated on all languages". DSML.KZ, 2026-08-13: "модель хорошо работает на казахском языке", linking the kz-transformers leaderboard. Card lists **LLM-as-a-judge as an intended use**; IFBench 77.0 (EN) | n/p | [card](https://huggingface.co/meta-models/Muse-Glimmer-30B), [DSML #1256](https://t.me/dsmlkz_news/1256) |
| `gpt-oss:120b` / `alemai/openai/gpt-oss-120b` | **KazBench real-data run 2026-06-20: 71.7 overall** (ЕНТ knowledge_mc 56.7, Kazakh review sentiment 86.7, n=60/task, Groq endpoint). Same run: gemini-2.5-flash 87.5, gpt-4o-mini 71.7, llama-3.3-70b 74.2. Card itself makes no language claim (knowledge cutoff 2024-06) | n/p | [KazBench REAL_DATA_LEADERBOARD.md](https://github.com/Yersultan04/kazbench/blob/master/results/real/REAL_DATA_LEADERBOARD.md) |
| `alemai/moonshotai/Kimi-K2.6` | n/p — no Kazakh score in any board I could open | n/p — no Kimi entry on MERA Text 2.0 | [MERA board](https://mera.a-ai.ru/en/text/leaderboard) |
| `alemai/zai-org/GLM-5.3`, `GLM-5.3-Flash` | n/p | n/p — no GLM entry on MERA Text 2.0 | [MERA board](https://mera.a-ai.ru/en/text/leaderboard) |
| not available to us (context) | **Qwen3.5-9B (think) KazMMLU 74.5 / KazCulture 55.0 / GSM8k-kk 84.9** Cyrillic — the strongest open Kazakh numbers in the 2026 cross-script audit (3-benchmark mean 71.5). Sherkala-8B 57.2 mean but collapses to 26.8 on Latin. ISSAI **Qolda** 60.4 mean (best cross-script of the Kazakh-adapted set, Δ 11.5) | YandexGPT 60.2 KazMMLU avg (ACL 2025) | [EMNLP 2026 Tables 1/8/9/10](https://aclanthology.org/2026.emnlp-main.1479.pdf), [KazMMLU Table 4](https://arxiv.org/html/2502.12829v2) |

## 2. DSML.KZ community view

DSML.KZ does not run its own benchmark. Its channels amplify the **kz-transformers** leaderboards
(Sanzhar Murzakhmetov, Beksultan Sagyndyk, Kirill Yakunin — all DSML residents) and the
**Kaz Offline Arena**, where an LLM judge (GPT-4o) + Bradley–Terry ranks Kazakh free-form answers:

- Benchmarks announcement, 2024-12-01 — the MMLU/GSM8K-kk + Constitution/Dastur/ЕНТ MC suite that the
  leaderboard runs on: <https://t.me/dsmlkz_news/1092> (site mirror <https://dsml.kz/en/news/50e817b0-5e86-4040-8897-209542fa9dcc>).
- Kaz Offline Arena results, 2025-05: «Модели **Gemma** от Google DeepMind **стабильно сильные**;
  **Sherkala-8B (MBZUAI) — второе место**, обошёл даже большие модели; **ISSAI (Nazarbayev University) —
  хорошие MC-баллы, но одни из самых слабых по генерации**»: <https://t.me/dsmlkz_news/1121>
  (arena: <https://huggingface.co/spaces/kz-transformers/kaz-offline-arena>, judge pipeline:
  <https://github.com/horde-research/Kaz-Offline-Arena>).
- Muse Glimmer release note, 2026-08-13 — «модель **хорошо работает на казахском языке**», citing
  <https://huggingface.co/spaces/kz-transformers/kaz-llm-lb2>, and crediting DSML resident Arman
  Zharmağambetov: <https://t.me/dsmlkz_news/1256>.
- Sherkala launch, 2025-03 — «лидирует на KazMMLU, Common Sense Reasoning … на Vicuna и MT Bench
  модель опережает KazLLM ISSAI по генерации»: <https://t.me/dsmlkz_news/1120>.
- DSML's AI Radar (2026-10-18) covers DeepSeek V4.1-Flash neutrally, on agentic cost, not language
  quality: <https://t.me/dsmlkz_news/1277>.

Note the tension: the arena (generation) liked **Gemma**, the MC leaderboards like the
**Kazakh-tuned Qwen** line — and the community itself flags exactly this split ("хорошие MC-баллы,
но одни из самых слабых по генерации"). Neither board measures judging.

## 3. Ranking for our judge (ids from our list only)

1. **`alemai/deepseek-ai/DeepSeek-V4.1-Flash`** — the only model on our list with strong *independent*
   evidence in **both** languages: best open score ever published on KazMMLU for its family line
   (76.9, ACL 2025) and rank 5/47 on the Russian MERA Text 2.0 board (0.581), where it also posts
   IFHardBench 0.954 — i.e. it follows hard checklists in Russian. *[Inference: I am extrapolating
   from V3→V4.1 family continuity plus MERA; V4.1-Flash has no published Kazakh number.]*
2. **`qwen3.5-35b-a3b-kazakh`** — best measured Kazakh scores of anything we can call (KazMMLU 84.0,
   KazCulture 68.7) and it is a native reasoner, which suits rubric-scoring of Kazakh chats. Weakness
   is Russian, which is untested for this checkpoint and not in its training mix; keep it as the
   Kazakh specialist, not the single judge.
3. **`alemai/astanahub/alemllm`** — highest vendor-reported averages on both languages (kk 0.826 /
   ru 0.848), built specifically for this market. Evidence quality is the lowest on the list
   (self-published, gated card, no third-party reproduction), so it ranks third despite the numbers.

**Runners-up:** `gemma-4:31b` — the community's favourite Kazakh generator, but weak Russian
(0.369, #23 on MERA) and no Kazakh score at 31B. `muse-glimmer-30b` — DSML's positive anecdote plus
"LLM-as-a-judge" as a documented intended use, but zero numbers.
**Avoid as judge:** `gpt-oss:120b` (2024-06 cutoff, thin Kazakh), Kimi-K2.6 and GLM-5.3 (no KZ/RU
evidence at all).

Methodological warning for phase 1: the EMNLP 2026 cross-script audit shows *every* open model loses
5.6–30.4 points the moment Kazakh is written in Latin, and its authors deliberately **excluded
LLM-as-judge scoring from Latin Kazakh because judge reliability there is unestablished**
(<https://aclanthology.org/2026.emnlp-main.1479.pdf>, §3.2). If any chat in the gold set is Latin- or
code-mixed Kazakh, our judge choice has to be validated on our own 24-dialog gold set (B5), not on
these boards. Benchmarks measure knowledge, not judging.

## 4. Sources I could not open

- `kz-transformers/kaz-llm-lb` live leaderboard state (private datasets
  `kaz-llm-lb-metainfo`, `s-openbench-eval` → HTTP 401). Only the committed **seed** is public:
  gpt-4o 0.742 / claude-3-5-sonnet 0.734 / gemini-1.5-pro 0.738 on `mmlu_translated_kk`, no
  2026 open-weight entries: <https://huggingface.co/spaces/kz-transformers/kaz-llm-lb/raw/main/data/leaderboard.json>
- `kz-transformers/offline-data-results` (arena submissions) → HTTP 401; the arena Space is sleeping
  and the per-model ELO could not be read.
- `astanahub/alemllm` card body → gated (HTTP 401); the AlemLLM tables quoted in §1 come from the
  unmodified mirror in `Sherkhan243/alemllm-GGUF`.
- Dias Ilyas, "We benchmarked 9 modern opensource LLMs on Kazakh" (LinkedIn) → 404 to anonymous
  fetch, so the numbers behind it are not cited here.
- HuggingFace model pages for `Tohirju/qwen38-27b-kazakh-sft` and Kimi/GLM language lists were not
  checked for Kazakh rows; treated as n/p rather than assumed.
