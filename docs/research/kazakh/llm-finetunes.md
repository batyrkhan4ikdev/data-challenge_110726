# Kazakh fine-tunes, LoRAs and merges of open LLMs (as of 2026-11-08)

Scope: **derivative** Kazakh models — continued-pretraining (CPT), SFT, LoRA/QLoRA and merges of
open bases (Qwen, Llama, Gemma, Mistral, mGPT, TinyLlama, Liquid, MT5…), plus the instruction
datasets they were trained on. Models trained from scratch are covered in `llm-foundation.md`;
benchmarks in `benchmarks.md`; speech in `speech.md`; RU/KZ telephony ASR in
`../asr-models.md`; DSML arena view in `../dsml-models.md`; judge candidates we already call in
`../llm-candidates.md`.

Every id below was resolved against the HF API (`/api/models/<id>`); `gated` = the API returns
401/`gated` to an anonymous caller, so the card body could not be read. `n/p` = nothing published.
Download counts are the HF `downloads` field (last-30-days) on 2026-11-08 and are only a rough
popularity signal. «доступна нам» = already callable by the team.

Legend for **type**: `CPT` = continued pretraining, `SFT` = full fine-tune / instruction tune,
`LoRA`/`QLoRA` = adapter, `merge` = task-vector / chat-vector merge, `quant` = quantisation of
another model (grouped under its original).

## 1. ISSAI (Nazarbayev University) — the only org publishing measured Kazakh fine-tunes

| Model | Org | Rel. | Type | Base | Size | Kazakh data | License | Published evals | Weights | Sources / downloads |
|---|---|---|---|---|---|---|---|---|---|---|
| `issai/Qwen3.5-4B-Base-Kazakh` | ISSAI | 2026-08 | CPT + tokenizer ext (+16K Kazakh tokens, 248,320 → 264,192, FVT init) | `Qwen/Qwen3.5-4B-Base` | 4.58B params (card/safetensors) | ~15.7B new-token total, 50/50 kk:en (≈7.85B kk); FineWeb-2, CulturaX, FinePDFs, FineWiki; 1 epoch, seq 32,768, 2×8×H100 | Apache-2.0 | n/p on this checkpoint (text-only base) | yes | [card](https://huggingface.co/issai/Qwen3.5-4B-Base-Kazakh) · 108 dl |
| `issai/Qwen3.5-9B-Base-Kazakh` | ISSAI | 2026-08 | CPT + +16K vocab (untied emb) | `Qwen/Qwen3.5-9B-Base` | 9.08B | ~15.9B tokens, 50/50 kk:en | Apache-2.0 | n/p | yes | [card](https://huggingface.co/issai/Qwen3.5-9B-Base-Kazakh) · 40 dl |
| `issai/Qwen3.5-35B-A3B-Base-Kazakh` | ISSAI | 2026-08 | CPT + +16K vocab (MoE, 256 experts, router aux-loss preserved) | `Qwen/Qwen3.5-35B-A3B-Base` | 34.7B (~3B active) | ~15.9B tokens, 50/50 kk:en, curated Kazakh cultural/QA sets upsampled 3× | Apache-2.0 | n/p | yes | [card](https://huggingface.co/issai/Qwen3.5-35B-A3B-Base-Kazakh) · 17 dl |
| `issai/Qwen3.5-4B-Kazakh` | ISSAI | 2026-08 | **merge** (chat-vector `θ_cpt + (θ_inst − θ_base)`, special-token pinning, vision branch re-attached) — no SFT/RLHF | `issai/Qwen3.5-4B-Base-Kazakh` + `Qwen/Qwen3.5-4B` | 4.58B | inherits the CPT mix above | Apache-2.0 | KazMMLU **78.5** (stock 72.5), KazCulture **55.4** (42.3), Belebele-kk 85.6 (84.6), MMLU-kk 78.5, GSM8K-kk 89.0; EN MMLU 84.2 (85.9), GPQA-Diamond 72.2 (76.8) | yes | [card](https://huggingface.co/issai/Qwen3.5-4B-Kazakh) · 462 dl |
| `issai/Qwen3.5-9B-Kazakh` | ISSAI | 2026-08 | merge (as above; untied emb) | `issai/Qwen3.5-9B-Base-Kazakh` + `Qwen/Qwen3.5-9B` | 9.54B | idem | Apache-2.0 | KazMMLU **83.1** (77.0), KazCulture **63.4** (49.5), Belebele-kk 87.9 (87.3), MMLU-kk 82.8, GPQA-kk 63.9; EN MMLU 86.9 (88.4), GPQA-Diamond 76.3 (84.3) | yes | [card](https://huggingface.co/issai/Qwen3.5-9B-Kazakh) · 380 dl |
| `issai/Qwen3.5-35B-A3B-Kazakh` — **доступна нам** (`qwen3.5-35b-a3b-kazakh`, self-hosted) | ISSAI | 2026-08 | merge | `issai/Qwen3.5-35B-A3B-Base-Kazakh` + `Qwen/Qwen3.5-35B-A3B` | 35.17B (~3B active) | idem, 50/50 kk:en, **no Russian** in the CPT mix | Apache-2.0 | KazMMLU **84.0** (82.6), KazCulture **68.7** (60.3), Belebele-kk 88.9 (89.4), MMLU-kk 84.4 (87.2), GSM8K-kk 89.3; EN MMLU 89.3 (91.2), GPQA-Diamond 82.3 (86.9). Card warns reasoning chains get shorter: PolyMath −5.8, GPQA-D −4.5 | yes | [card](https://huggingface.co/issai/Qwen3.5-35B-A3B-Kazakh) · 268 dl |
| `issai/LLama-3.1-KazLLM-1.0-8B` | ISSAI | 2024-12 | CPT of Llama 3.1 (Kazakh/Russian/English/Turkish); 8×DGX H100 | `meta-llama/Llama-3.1-8B` | 8B | >150B tokens total in the 8B+70B programme, 95% ISSAI-curated; Kazakh from kk web/news/libraries + translated English | CC-BY-NC-4.0, **gated** | ISSAI suite (ARC/MMLU/GSM8K/HellaSwag/Winogrande/DROP in kk), figures only on the [ISSAI page](https://issai.nu.edu.kz/kazllm/). Third-party: KazMMLU avg **41.7** ([KazMMLU, ACL 2025, Table 4](https://arxiv.org/html/2502.12829v2)); 37.0 KazMMLU + Belebele 27.8 in the [Sherkala paper Table 3](https://arxiv.org/html/2503.01493v2); Vicuna-kk 4.88 vs Llama-3.1-8B-Instruct 3.75; generation judged *worse* than Sherkala | yes (gated) | [card](https://huggingface.co/issai/LLama-3.1-KazLLM-1.0-8B) · 172 dl |
| `issai/LLama-3.1-KazLLM-1.0-70B` | ISSAI | 2024-12 | CPT | `meta-llama/Llama-3.1-70B` | 70.55B | idem | CC-BY-NC-4.0, gated | AlemLLM vendor table puts KazLLM-70B at 0.766 Kazakh avg (unreproduced); no independent 70B KazMMLU number found | yes (gated) | [card](https://huggingface.co/issai/LLama-3.1-KazLLM-1.0-70B) · 6 dl |
| `issai/foggen` | ISSAI | 2026-05 (mod 2026-11) | SFT, LoRA r16/α32, 14 continual rounds | `Qwen/Qwen3-0.6B` | 0.6B | `issai/foggen-data` + `issai/KazCulture`; 1,800 rows/round, 7 domains incl. Kazakh culture | Apache-2.0 | Kazakh-culture MCQ: edge-only 90.9, FogGen system 91.5, cloud-only 96.2, 1.1% routed (τ=0.5). Mean over 7 domains 75.0 vs 70.6 random routing | yes | [card](https://huggingface.co/issai/foggen) · 453 dl |
| `issai/foggen-qwen3-1.7b` | ISSAI | 2026-05 | SFT/LoRA (same recipe, bigger edge) | `Qwen/Qwen3-1.7B` | 1.7B | idem | Apache-2.0 | Kazakh culture: edge 90.3, FogGen 92.3, routed 7.4%; mean 79.1 | yes | [card](https://huggingface.co/issai/foggen-qwen3-1.7b) · 400 dl |
| `issai/foggen-gemma3-1b`, `issai/foggen-gemma3-270m`, `issai/foggen-r15-oe` | ISSAI | 2026-05 | SFT/LoRA (same recipe, Gemma-3 edge / +1 open-ended round) | `google/gemma-3-1b`, `-270m` | 1B / 270M | idem | Apache-2.0 | same suite, per-checkpoint tables on the `issai/foggen` card | yes | [foggen-gemma3-1b](https://huggingface.co/issai/foggen-gemma3-1b) · 409 dl, [foggen-gemma3-270m](https://huggingface.co/issai/foggen-gemma3-270m) · 414 dl, [foggen-r15-oe](https://huggingface.co/issai/foggen-r15-oe) · 8 dl |
| `issai/Qolda` | ISSAI | 2025-11 (mod 2026-08) | SFT (InternVL framework) | `OpenGVLab/InternVL3_5-4B` (+ `Qwen/Qwen3-4B` LM) | 4.3B | kk/ru/en; benchmark suite in the [Qolda collections](https://huggingface.co/collections/issai/qolda-language-benchmarks) | Apache-2.0 | KazMMLU 66.14 (think) / 58.11 (no-think), KazCulture 53.0, Belebele-kk 82.9, INCLUDE-kk 46.0, INCLUDE-ru 56.5 | yes | [card](https://huggingface.co/issai/Qolda) · 132 dl |
| `issai/Qolda-AVL-5B` / `-9B` / `-34B` | ISSAI | 2026-04 / 06 / 06 | SFT of VL bases | `Qwen/Qwen3-VL-4B-Thinking` / `-8B-Thinking` / `-32B-Thinking` | 5B / 9.5B / 34.1B | n/p (card gives evals, not token counts) | Apache-2.0 | KazMMLU 69.27 / 73.04 / **78.98**; KazCulture 44.75 / 56.39 / 62.37; Belebele-kk 88.78 (34B); MMLU-kk 81.94 (34B); Russian rows: MMLU-Pro-ru 76.34, GPQA-ru 59.36, GSM8K-ru 94.31 (34B) | yes | [Qolda-AVL-5B](https://huggingface.co/issai/Qolda-AVL-5B) · 133 dl, [-9B](https://huggingface.co/issai/Qolda-AVL-9B) · 18, [-34B](https://huggingface.co/issai/Qolda-AVL-34B) · 80 |

ISSAI has no other Kazakh text LLMs on HF — the full author list is 38 repos, the rest are
TTS/ASR/vision ([author page](https://huggingface.co/issai/models)). `issai/math_qolda` and
`issai/Qolda_GGUF` (914 dl) are quantisations/derivatives of the Qolda line.

## 2. Fine-tunes of other open bases (non-ISSAI)

| Model | Org / author | Rel. | Type | Base | Size | Kazakh data | License | Published evals | Weights | Sources / downloads |
|---|---|---|---|---|---|---|---|---|---|---|
| `inceptionai/Llama-3.1-Sherkala-8B-Chat` (mirror: `inception42/…`, **gated**) | Inception + MBZUAI + Cerebras | 2025-02 | CPT then SFT | `meta-llama/Llama-3.1-8B` | 8.29B | **45.3B tokens: 19.45B kk + 19.45B en + 6.4B ru/tr**; own expanded vocab 128,256 → 159,766, Kazakh "fertility" 4.73 → 2.04 (−56.8%); SFT = translated instructions + a Kazakhstan-specific set built with GPT-4o and manually verified + kk safety data; seq 8,192 | CC-BY-NC-SA-4.0 | Sherkala-Chat: KazMMLU-kk 41.4, MMLU-kk 34.6, Belebele-kk 30.6, PIQA 65.9, ARC 42.9, AVG 47.6 (best of the ≤10B field in that table); Vicuna-kk 7.39 ±1.89 (KazLLM-8B 4.88, GPT-4o 9.32); RU KazMMLU 36.8 | yes (gated) | [paper](https://arxiv.org/html/2503.01493v2) · [card](https://huggingface.co/inceptionai/Llama-3.1-Sherkala-8B-Chat) · 47 dl |
| `RedBullet12/LFM3-1.7B-Kazakh` | RedBullet12 (ind.) | 2026-11 | SFT, **LoRA r16/α32 merged** | `LiquidAI/LFM3-1.7B` | 1.7B | `AmanMussa/kazakh-instruction-v2`, 52,123 train rows (machine-translated Alpaca + manual fixes), 1 epoch, lr 2e-4, 1×A100 ≈1 h | LFM Open License v1.0 (inherited) | n/p — no benchmark; author states facts are unreliable ("named Beijing as the capital") | yes | [card](https://huggingface.co/RedBullet12/LFM3-1.7B-Kazakh) · 497 dl |
| `Darmm/darmm-chat-kazakh-8b` | Darmm (Rakhat Zhumabek) | 2026-09 | **QLoRA** r32/α64, all attn+MLP, merged | `Qwen/Qwen3-8B` | 8B (+ adapter 59.9M trainable) | **105k pairs: 65k kk + 25k ru + 15k en** — `AmanMussa/kazakh-instruction-v2` (51k), `sabinaasker/kazakh_dolly` (15k), `d0rj/alpaca-cleaned-ru` (25k), `yahma/alpaca-cleaned` (15k); 1 epoch, seq 1,024, 1×A100 | Apache-2.0 | Belebele kaz_Cyrl **39.8** (base 27.2), KazMMLU kk subjects **38.3** (27.9) — option log-prob, non-thinking | yes | [card](https://huggingface.co/Darmm/darmm-chat-kazakh-8b) · 16 dl |
| `Darmm/darmm-chat-kazakh-8b-lora` | Darmm | 2026-09 | LoRA adapter (~170 MB), vLLM multi-LoRA compatible | `Qwen/Qwen3-8B` | 8B | idem | Apache-2.0 | identical to the merged model | yes | [card](https://huggingface.co/Darmm/darmm-chat-kazakh-8b-lora) · 12 dl |
| `Darmm/darmm-text-generation-kazakh-v2` | Darmm | 2026-02 | QLoRA adapter (~646 MB) | `Qwen/Qwen2.5-Coder-7B-Instruct` | 7B | n/p (kk instruction data) | Apache-2.0 | n/p | yes | [card](https://huggingface.co/Darmm/darmm-text-generation-kazakh-v2) · 0 dl |
| `rsyrlybay/qwen2.5-3b-history-kazakhstan` | Ramazan Syrlybay | 2026-01 | **QLoRA** r32/α64, merged | `Qwen/Qwen2.5-3B` | 3.09B | 660 question–answer pairs from an 11th-grade Kazakhstan-history textbook (kk/ru/en), 3 epochs | MIT | n/p | yes | [card](https://huggingface.co/rsyrlybay/qwen2.5-3b-history-kazakhstan) · 8 dl |
| `TSaltanat/Qwen2.5-3B-Kazakh-History-LoRA` | TSaltanat | 2026-10 | LoRA adapter (Unsloth/TRL) | `unsloth/Qwen2.5-3B-Instruct-unsloth-bnb-4bit` | 3B | Kazakhstan-history QA (card is the Unsloth template: dataset/hparams not filled in) | n/p (no license field) | n/p | yes | [card](https://huggingface.co/TSaltanat/Qwen2.5-3B-Kazakh-History-LoRA) · 15 dl |
| `RakhatM/qwen3-1.7b-kazakh-text-to-sql-sft` | Rakhat Masat | 2026-10 | QLoRA SFT | `Qwen/Qwen3-1.7B-Base` | 1.7B | `RakhatM/kazakh-text-to-sql`, 3,744 kk question–SQL pairs | Apache-2.0 | execution-accuracy table on the card (text-to-SQL only) | yes | [card](https://huggingface.co/RakhatM/qwen3-1.7b-kazakh-text-to-sql-sft) · 25 dl |
| `RakhatM/qwen3-1.7b-kazakh-text-to-sql-dpo` / `-grpo` | Rakhat Masat | 2026-10 | DPO+RPO (1,568 pref. pairs) then GRPO (1,650 q, execution reward) on the SFT model | → stage-1 model | 1.7B | idem | Apache-2.0 | idem; 3-stage curriculum code: [github.com/RakhatMM/llm-finetuning-course](https://github.com/RakhatMM/llm-finetuning-course) | yes | [dpo](https://huggingface.co/RakhatM/qwen3-1.7b-kazakh-text-to-sql-dpo) · 22, [grpo](https://huggingface.co/RakhatM/qwen3-1.7b-kazakh-text-to-sql-grpo) · 23 |
| `loqira/Qwen3.5-0.8B-GEC-KAZ-RUS-ENG` | Loqira Labs | 2026-07 | QAT (4/8/16-bit) fine-tune, GGUF-only | `Qwen/Qwen3.5-0.8B` | 0.8B (≈537 MB Q4_0) | GEC/proofreading pairs, kk+ru+en, ~1,600 tok/sample, train ctx 2,048; single-turn | Apache-2.0 | GEC metrics on the card; not a chat/judge model | yes | [card](https://huggingface.co/loqira/Qwen3.5-0.8B-GEC-KAZ-RUS-ENG) · 340 dl |
| `ai-forever/mGPT-1.3B-kazakh` | AI Forever (Sber) | 2023-08 | CPT (+150k steps, bs 4, ctx 2,048, 1×A100) | `ai-forever/mGPT` (1.3B) | 1.3B | Kazakh web + corpus text (Wikipedia/C4-derived, not itemised) | MIT | val **perplexity 3.38** | yes | [card](https://huggingface.co/ai-forever/mGPT-1.3B-kazakh) · 100 dl |
| `AmanMussa/llama2-kazakh-7b-ver2` | Mussa Aman | 2023-12 | SFT (full, self-instruct) | `meta-llama/Llama-2-7b-hf` | 6.74B | `AmanMussa/kazakh-instruction-v2` (translated Stanford Alpaca + kk history/culture items) | MIT (v1/v2 dataset is MIT) | n/p; method paper: [Parameter-Efficient Fine-Tuning of LLaMA 2 for the Kazakh Language](https://huggingface.co/datasets/AmanMussa/kazakh-instruction-v2) (Springer 2025) | yes | [card](https://huggingface.co/AmanMussa/llama2-kazakh-7b-ver2) · 11 dl |
| `TilQazyna/llama-kaz-instruct-8B-1` (Til Qazyna / NCRT) | TilQazyna | 2024-09 | CPT + instruction tune | `meta-llama/Meta-Llama-3-8B` | 8B | n/p (kk web/morpho corpora from the same org) | Apache-2.0 | n/p | yes, **gated** | [card](https://huggingface.co/TilQazyna/llama-kaz-instruct-8B-1) · 0 dl |
| `TilQazyna/Til-2B-instruct`, `Til-2B-GEC`, `Til-Core-1B-Instruct`, `Til-Core-1B-GEC`, `Til-kk-0.5B-256k-*` | TilQazyna | 2026-05 → 2026-08 | SFT / GEC fine-tunes of their own small bases | `TilQazyna/Til-2B`, `Til-Core-1B`, `Til-0.5B/1B-multilingual-base` | 0.5–2B | n/p (QazGramma GEC corpora, `kazakh-morpho-corpus`, kk web corpora) | Apache-2.0 (base line AFL-3.0 for `llama-1.9B-kaz`) | n/p | yes, mostly gated | [Til-2B-GEC](https://huggingface.co/TilQazyna/Til-2B-GEC) · 20 dl, [Til-2B-instruct](https://huggingface.co/TilQazyna/Til-2B-instruct), [Til-Core-1B-Instruct](https://huggingface.co/TilQazyna/Til-Core-1B-Instruct) |
| `TilQazyna/Til-GEC-Gemma4-exp087` | TilQazyna | 2026-08 | fine-tune (GEC) | `google/gemma-4-E4B-it` / `-12B-it` / `-26B-A4B-it` / `-31B-it` | n/p | kk GEC | Gemma license, **gated** | n/p | yes (gated) | [card](https://huggingface.co/TilQazyna/Til-GEC-Gemma4-exp087) |
| `nur-dev/llama-1.9B-kaz` | nur-dev | 2024-08 | from-scratch Llama (listed for completeness; no kk fine-tune of it is public) | — | 1.94B | kk text | AFL-3.0, gated manual | n/p | yes (gated) | [card](https://huggingface.co/nur-dev/llama-1.9B-kaz) · 0 dl |
| `Eraly-ml/Kimi-K3-0.40B-Kazakh-CPT-59M` (+ `-step200`) | Yeraly Gainulla | 2026-07 | CPT | `inference-optimization/Kimi-K3-0.40B` (hybrid KDA+MLA+MoE, 388.6M LM params) | 0.4B | **59M cumulative Kazakh tokens** — `kazakhBooks.csv` of `kz-transformers/multidomain-kazakh-dataset`; 7,200 steps, seq 512, 1×T4, 417 min | MIT | val loss 3.35 / PPL 28.51 (50 batches), extended 2.86 / 17.43; base model, no instruction tuning | yes | [card](https://huggingface.co/Eraly-ml/Kimi-K3-0.40B-Kazakh-CPT-59M) · 27 dl |
| `stukenov/sozkz-fix-qwen-500m-kk-gec-v1..v4` | Saken Tukenov | 2026-04 | iterative SFT + preference optimisation (GEC) | `sozkz-core-qwen-500m-kk-base` (own from-scratch) | 447.5M | synthetic + mixed kk GEC corpora | MIT, gated manual | GEC only | yes (gated) | [v4](https://huggingface.co/stukenov/sozkz-fix-qwen-500m-kk-gec-v4) |
| `stukenov/sozkz-core-tinyllama-1b-kk-ru-v1` | Saken Tukenov | 2026-04 | CPT (tokenizer extension + progressive multi-stage) | `TinyLlama/TinyLlama-1.1B-intermediate-step-1431k-3T` | 1.14B | kk + ru | Apache-2.0, gated manual | n/p | yes (gated) | [card](https://huggingface.co/stukenov/sozkz-core-tinyllama-1b-kk-ru-v1) |
| `stukenov/sozkz-mgpt-1.3b-translate-kkru-v1` | Saken Tukenov | 2026-04 | fine-tune for kk↔ru translation | `ai-forever/mGPT-1.3B-kazakh` | 1.42B | kk↔ru parallel | MIT, gated manual | translation metrics on card | yes (gated) | [card](https://huggingface.co/stukenov/sozkz-mgpt-1.3b-translate-kkru-v1) |
| `Evgenii/gemma-3-27b-it-kazrus-2`, `gemma-3-12b-it-kazrus-1`, `gemma-3-27b-it-kazrus-syn-n-2_10-v2-bf16` | Evgenii (ind.) | 2025-05/06 | fine-tunes of Gemma-3 for kk/ru (card is the auto template: base/data/hparams **not documented**) | `google/gemma-3-27b-it`, `-12b-it` | 27B / 12B | n/p | n/p (no license field) | n/p | yes | [kazrus-2](https://huggingface.co/Evgenii/gemma-3-27b-it-kazrus-2) · 4 dl, [syn-v2](https://huggingface.co/Evgenii/gemma-3-27b-it-kazrus-syn-n-2_10-v2-bf16) · 8 |
| `procrastipredator/gemma-3-kazakh-finetuned` | ind. | 2025 | LoRA/SFT via Unsloth+TRL | `unsloth/gemma-3-4b-it-unsloth-bnb-4bit` | 4B | kk (card metadata says `language: en`; dataset unstated) | Apache-2.0 | n/p | yes | [card](https://huggingface.co/procrastipredator/gemma-3-kazakh-finetuned) · 12 dl |
| `armanibadboy/llama3.2-kazllm-3b-by-arman` (+ `-gguf`, `llama3.1-kazllm-8b*` ver1–4) | armanibadboy | 2025-01 | Unsloth/TRL fine-tunes of the KazLLM bases | `unsloth/llama-3.2-3b-instruct-bnb-4bit`, `unsloth/Meta-Llama-3.1-8B-bnb-4bit` | 3B / 8B | n/p | Apache-2.0 | n/p | yes | [3B](https://huggingface.co/armanibadboy/llama3.2-kazllm-3b-by-arman) · 35 dl |
| `sbekova/ertegilerim-kk-llama3.1-kazllm-8b-qlora-v` | sbekova | 2025-12 | QLoRA adapter on **KazLLM** | `issai/LLama-3.1-KazLLM-1.0-8B` | 8B | kk fairy-tale corpus ("Eртегілерім"); card is the PEFT template, sizes n/p | n/p | n/p | yes | [card](https://huggingface.co/sbekova/ertegilerim-kk-llama3.1-kazllm-8b-qlora-v) · 8 dl |
| `shayekh/kazakh-summarization-Llama-3.2-3B-Instruct` | Shayekh Bin Islam (Adaption project) | 2026-06 | LoRA adapter | `meta-llama/Llama-3.2-3B-Instruct` | 3B | kk news summarization (paired dataset: `shayekh/kazakh-news-summarization-20k-adapted`, 10k–100k rows) | n/p | n/p | yes | [card](https://huggingface.co/shayekh/kazakh-summarization-Llama-3.2-3B-Instruct) · 15 dl |
| `shayekh/kazakh-cultural-gpt-oss-20b` | same | 2026-06 | LoRA adapter | `togethercomputer/gpt-oss-20b-bf16` | 20B | kk cultural data (`issai/KazCulture` family) | n/p | n/p | yes | [card](https://huggingface.co/shayekh/kazakh-cultural-gpt-oss-20b) · 7 dl |
| `Damilya/qwen3-4b-kazakh-lora` | Damilya | 2026-08 | LoRA | `Qwen/Qwen3-4B-Instruct-2507` | 4B | n/p (card empty; listed on [Featherless](https://featherless.ai/models/Damilya/qwen3-4b-kazakh-lora) as 4B/BF16/32k ctx) | CC-BY-NC-4.0 | n/p | yes | [card](https://huggingface.co/Damilya/qwen3-4b-kazakh-lora) · 2 dl |
| `Tohirju/qwen38-27b-kazakh-sft`, `qwen38-27b-kazakh-tool`, `qwen38-27b-kazakh-tool-grpo` | Tohir Saidzoda (Saidzoda Lab) | 2026-08 | SFT / tool-calling / GRPO, part of a tt-uz-ky-kk series | `Qwen/Qwen3.8-27B` (tool variant declares it; SFT repo shows no base field) | ≈27B | `Tohirju/Kazakh_SFT_ChatML` (100k–1M rows, license "other", gated) | n/p (no license) | n/p | yes, **gated** | [sft](https://huggingface.co/Tohirju/qwen38-27b-kazakh-sft), [tool](https://huggingface.co/Tohirju/qwen38-27b-kazakh-tool) · 0 dl each |
| `SaidzodaEng/qwen38-27b-kazakh-sft` | same lab, English-facing | 2026-08 | SFT | n/p (empty card) | ≈27B | n/p | n/p | n/p | yes, gated | [card](https://huggingface.co/SaidzodaEng/qwen38-27b-kazakh-sft) · 0 dl |
| `Gen2B/Irbis-7b-v0.1` (= `IrbisAI/Irbis-7b-v0.1`, same weights) | Gen2B | 2024-03 | CPT with tokenizer extension 32k → 60k | Mistral-7B architecture (`MistralForCausalLM`, 7.47B) | 7.47B | ~20 GB predominantly kk + some ru text (token count n/p) | MIT | Sherkala paper Table 3: KazMMLU 29.5, Belebele-kk 26.1, AVG 37.7; MDPI 2025 QA eval includes it | yes | [card](https://huggingface.co/Gen2B/Irbis-7b-v0.1) · 466 dl · [Habr write-up](https://habr.com/ru/articles/825574/) |
| `Gen2B/Irbis-7b-Instruct_lora` | Gen2B | 2024-03 | LoRA adapter (instruction) | `Irbis-7b-v0.1` | 7B | n/p | MIT | n/p | yes | [card](https://huggingface.co/Gen2B/Irbis-7b-Instruct_lora) · 5 dl |
| `astanahub/alemllm` — **доступна нам** (`alemai/astanahub/alemllm`) | Astana Hub | 2025-07/08 | fine-tune; **exact base not stated on the (gated) card** — press says built on the YuAI Lightning platform, "over 246 billion parameters" | n/p | ~246B (press figure) | kk/ru/tr/en; token counts n/p | Apache-2.0 (field) | Vendor table: Kazakh avg 0.826, Russian avg 0.848 — see `../dsml-models.md` §1 | yes (gated) | [card](https://huggingface.co/astanahub/alemllm) · [Astana Times](https://astanatimes.com/2025/08/alemllm-kazakh-language-model-now-publicly-available/) · 2 dl |

Not Kazakh despite the name: `Gen2B/HyGPT-10b`/`-it` (Armenian/Russian/English — same team as
Irbis, easy to confuse), `Inv/Kazbek-7B` (English; only the GGUF mirror is public),
`Kazuya-Nomura-zer0/CYBER-FROST-3.8-GGUF`, `kz-*` user handles (`kazzand`, `kazar…*`) — checked and
excluded.

## 3. Quantisations / GGUF mirrors — group under the original, not separate models

| Repo | Is a quant of | Format | Notes / dl |
|---|---|---|---|
| `mradermacher/Qwen3.5-4B-Kazakh-GGUF` · `-9B-` · `-35B-A3B-` · `-4B-Base-` · `-9B-Base-` · `-35B-A3B-Base-` | the six `issai/Qwen3.5-*-Kazakh` models | GGUF (imatrix/i1 + plain) | **highest-traffic Kazakh LLM repos on HF**: 1,501 / 1,108 / 395 / 165 / 98 / 249 dl |
| `cashmere-cat/Qwen3.5-9B-Kazakh-oQ4` | `issai/Qwen3.5-9B-Kazakh` | MLX oQ4 | 12 dl |
| `issai/LLama-3.1-KazLLM-1.0-8B-AWQ4` / `-70B-AWQ4` | KazLLM 8B / 70B | AWQ 4-bit | gated, 13 dl each |
| `issai/LLama-3.1-KazLLM-1.0-8B-GGUF4` / `-70B-GGUF4` | KazLLM 8B / 70B | GGUF 4-bit | gated, 112 / 12 dl |
| `daemonstate/KAZLLM_8B_fp16.gguf`, `chambette/KazLLM`, `chambette/sherkala`, `DiDustin/sherkala_gguf` | KazLLM-8B / Sherkala-8B | GGUF | 6 / 12 / 14 / 45 dl, no license metadata |
| `NikolayKozloff/Irbis-7b-v0.1-Kazakh-Q8_0-GGUF`, `QuantFactory/Irbis-7b-v0.1-GGUF`, `RichardErkhov/IrbisAI_-_Irbis-7b-v0.1-gguf`, `mradermacher/Irbis-7b-v0.1*-GGUF` | `Irbis-7b-v0.1` | GGUF Q8/Q4/i1 | 17 / 38 / 18 / 2,062+818 dl |
| `featherless-ai-quants/TilQazyna-llama-kaz-instruct-8B-1-GGUF` (+ `RichardErkhov/…8bits`, `…awq`) | `TilQazyna/llama-kaz-instruct-8B-1` | GGUF IQ4→Q8 | 120 / 8 / 7 dl |
| `mradermacher/gemma-3-27b-it-kazrus-2-GGUF` | `Evgenii/gemma-3-27b-it-kazrus-2` | GGUF | 55 dl |
| `issai/Qolda_GGUF`, `issai/Qolda-AVL-5B-GGUF` | Qolda / Qolda-AVL-5B | GGUF | 914 / 782 dl |
| `Sherkhan243/alemllm-GGUF` | `astanahub/alemllm` | GGUF | 0 dl; **useful because it mirrors the AlemLLM benchmark tables verbatim** |

Also in this bucket: `mradermacher/qwen2.5-3b-history-kazakhstan-GGUF` (58 dl) of the
`rsyrlybay` history model, and `Ernaz/llama2-kazakh-7b-GGUF` (7 dl).

## 4. Kazakh SFT/instruction datasets behind these fine-tunes

| Dataset | Rows / size | Language | License | Used by | Source |
|---|---|---|---|---|---|
| `AmanMussa/kazakh-instruction-v2` | 10k–100k (52,123 train + 50 held-out per the LFM3 card) | kk | MIT | `RedBullet12/LFM3-1.7B-Kazakh`, `Darmm/darmm-chat-kazakh-8b`, `AmanMussa/llama2-kazakh-7b*` | [card](https://huggingface.co/datasets/AmanMussa/kazakh-instruction-v2) · 18,352 dl — the single most-used kk instruction set |
| `issai/kazqad` | 100k–1M (68k Q-C-A triples per the MDPI paper) | kk | CC-BY-SA-4.0, gated | QA/E5 fine-tunes (`Nurlykhan/KazEmbed-V5`, `R3iwan/kazakh-question-answering`) | [card](https://huggingface.co/datasets/issai/kazqad) · [repo](https://github.com/IS2AI/KazQAD) |
| `issai/KazCulture` | 10k–100k | kk | CC-BY-4.0 | `issai/foggen*`, `shayekh/kazakh-cultural-gpt-oss-20b`; also a benchmark | [card](https://huggingface.co/datasets/issai/KazCulture) |
| `issai/foggen-data` | 100k–1M (16,217 eval questions + per-round training files, 1,800 rows/round) | kk, en | Apache-2.0 | the whole FogGen family | [card](https://huggingface.co/datasets/issai/foggen-data) |
| `Tohirju/Kazakh_SFT_ChatML` | 100k–1M | kk | other, gated manual | `Tohirju/qwen38-27b-kazakh-*` | [card](https://huggingface.co/datasets/Tohirju/Kazakh_SFT_ChatML) |
| `nurkhan5l/kazakh-ift` | 10,600 samples, manually verified, government/cultural domain | kk | Apache-2.0, gated manual | the Qwen/Falcon/Gemma fine-tunes in [Instruction Tuning on Public Government and Cultural Data… (ACL 2025)](https://arxiv.org/abs/2502.13647) — **no public model checkpoints found under the authors' HF handles** | [card](https://huggingface.co/datasets/nurkhan5l/kazakh-ift) |
| `sabinaasker/kazakh_dolly` | 10k–100k (15k used) | kk | CC-BY-SA-3.0 | `Darmm/darmm-chat-kazakh-8b` | [card](https://huggingface.co/datasets/sabinaasker/kazakh_dolly) |
| `saillab/alpaca-kazakh-cleaned` | 100k–1M ("Kazakh alpaca-52k", Google-translated Stanford Alpaca, TaCo paper) | kk | CC-BY-NC | TaCo cross-lingual CoT experiments | [card](https://huggingface.co/datasets/saillab/alpaca-kazakh-cleaned) · [paper](https://openreview.net/forum?id=02MLWBj8HP) |
| `saillab/alpaca_kazakh_taco` | 10k–100k | kk | n/p | same | [card](https://huggingface.co/datasets/saillab/alpaca_kazakh_taco) |
| `DarkyMan/powerful-kazakh-dialogue` | 10,000 synthetic long-answer dialogues (Grok-generated) | kk | Apache-2.0 | general kk instruction tuning | [card](https://huggingface.co/datasets/DarkyMan/powerful-kazakh-dialogue) · 44 dl |
| `mangi-llm/kazakh-customer-support-qa` | 406 public rows (~10k full), banking/telecom/retail support QA with `{{ORG}}` slots | kk | CC-BY-4.0 | closest public proxy for our call-centre domain | [card](https://huggingface.co/datasets/mangi-llm/kazakh-customer-support-qa) |
| `mangi-llm/Kazakh_Multi-Task_corpus` | 1k–10k, 7 tasks (IF, QA, translation, sentiment, grammar) | kk/ru/en | CC-BY-4.0 | Mäñgi ÜTM community models | [card](https://huggingface.co/datasets/mangi-llm/Kazakh_Multi-Task_corpus) |
| `RakhatM/kazakh-text-to-sql` | 1k–10k (3,744 SFT + 1,568 pref + 1,650 GRPO) | kk | Apache-2.0 | the text-to-SQL chain | [card](https://huggingface.co/datasets/RakhatM/kazakh-text-to-sql) |
| `shayekh/kazakh-news-summarization-20k-adapted` | 10k–100k | kk | n/p | the Llama-3.2-3B summarization LoRA | [card](https://huggingface.co/datasets/shayekh/kazakh-news-summarization-20k-adapted) |
| `kz-transformers/multidomain-kazakh-dataset` | 10M–100M rows (25 GB, formal + conversational) | kk/ru | Apache-2.0 | CPT corpora (`Eraly-ml/Kimi-K3-…`, Kaz-RoBERTa line) | [card](https://huggingface.co/datasets/kz-transformers/multidomain-kazakh-dataset) · 437 dl |
| Sherkala pretraining corpus | 45.3B tokens (19.45B kk) | kk/en/ru/tr | not released as a single dataset | Sherkala-8B | [paper §2](https://arxiv.org/html/2503.01493v2) |
| ISSAI KAZ-LLM corpus | >150B tokens (kk/ru/en/tr), 95% ISSAI-curated | kk/ru/en/tr | not released | KazLLM 1.0 | [ISSAI page](https://issai.nu.edu.kz/kazllm/) |
| `issai/KazLLM_Benchmark_Dataset` | n/p | kk | CC-BY-NC-4.0 | the KazLLM eval suite (ARC/MMLU/GSM8K/HellaSwag/Winogrande/DROP in kk) | [card](https://huggingface.co/datasets/issai/KazLLM_Benchmark_Dataset) |

Catalogues worth diffing against monthly:
[alenisaw/awesome-kaz-models](https://github.com/alenisaw/awesome-kaz-models) (63 text/NLP entries,
updated 2026-11) and [Allessyer/awesome-kaz-datasets](https://github.com/Allessyer/awesome-kaz-datasets).

## 5. Что стоит протестировать

Baseline to beat: our own gold-set measurement of `gemma-4-31B` on Kazakh chats —
**0.957 overall** vs `issai/Qwen3.5-35B-A3B-Kazakh` **0.858** (0.710 per criterion),
`bench/results/20261108-005401/005403`. The Kazakh-specialised flagship therefore **loses** head-to-head
as a judge and is dropped from the candidate list; the fine-tunes below are worth a slot precisely
because none of them has been tried and each attacks a different failure mode of Gemma on kk
[INFERENCE].

1. **`issai/Qwen3.5-9B-Kazakh`** (self-host, thinking on) — [INFERENCE] the strongest *published*
   small-model Kazakh numbers of anything in this file (KazMMLU 83.1, KazCulture 63.4 vs 77.0/49.5
   for stock Qwen3.5-9B), yet it is 4× cheaper to serve than the 35B we just lost with. If the 35B's
   failure was the merge (degraded reasoning chains, PolyMath −5.8) rather than Kazakh tuning in
   general, the 9B is the cheapest way to find out; it also fits beside the other judges on one H200.
2. **`Darmm/darmm-chat-kazakh-8b`** (or its 170 MB LoRA on top of an existing Qwen3-8B) —
   [INFERENCE] the only third-party kk chat fine-tune with reproducible eval scripts (`eval_chat.py`)
   *and* retained Russian + English in the mix (65k kk / 25k ru / 15k en), which is exactly our
   trilingual judge distribution; Belebele-kk 27.2 → 39.8 over base Qwen3-8B shows the tuning moved
   the language, not just the style. Multi-LoRA serving means we could judge kk and ru chats from one
   process without a second model deployment.
3. **`inceptionai/Llama-3.1-Sherkala-8B-Chat`** — [INFERENCE] still the community's reference Kazakh
   *generator* (2nd place in the Kaz Offline Arena, best Vicuna-kk score of any open 8B, 7.39 vs
   KazLLM 4.88). Judging is generation-heavy (write a rationale, then a verdict), and the model was
   explicitly safety-aligned on Kazakh data — relevant if the judge has to flag policy violations in
   kk. Caveats: CC-BY-NC-SA (non-commercial — legal sign-off needed) and it loses 30 points when the
   chat is Latin-script Kazakh.
4. **`issai/Qolda-AVL-34B`** — [INFERENCE] the only Kazakh fine-tune family with published
   *Russian* rows in the same table as the Kazakh ones (KazMMLU 78.98 / MMLU-Pro-ru 76.34 /
   GSM8K-ru 94.31), Apache-2.0 and ungated, so it is the single checkpoint that could judge both of
   our languages with one set of numbers behind it. Its Kazakh knowledge score is below the 35B-A3B
   we just measured, but it is a different lineage (Qwen3-VL-32B-Thinking, real SFT, not a chat-vector
   merge), so it is a genuine alternative hypothesis rather than a rerun.
5. **A merge/quant to reuse rather than a new test: the `issai/Qwen3.5-*-Kazakh` GGUFs from
   `mradermacher`** — [INFERENCE] if we want the 4B or 9B Kazakh model on CPU/edge (e.g. a cheap
   pre-filter before the main judge), the 1,501-download `Qwen3.5-4B-Kazakh-GGUF` is already packaged;
   no extra training work needed. Test only after (1) or (2) shows the Kazakh line can beat Gemma at
   all — a smaller quant of a losing family is unlikely to win.

Notes for whoever runs this: (a) every one of these was tuned on machine-translated Alpaca-style
data (`kazakh-instruction-v2`, `alpaca-kazakh-cleaned`), which the authors themselves say reads as
translated — that may hurt a judge that must compare natural kk agent replies; (b) none of them has
any published LLM-as-judge number, Kazakh or otherwise — the only measuring stick is our own
gold set (B5); (c) `Tohirju/qwen38-27b-kazakh-*` and `Evgenii/*-kazrus*` are the two kk fine-tune
families on a comparable-parameter base to Gemma-4-31B but have empty model cards, so they are test
candidates only if we are willing to evaluate blind.
