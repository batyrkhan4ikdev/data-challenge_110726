# Kazakh foundation / national LLMs (as of 2026-11-08)

Scope: models **trained from scratch or by large continued pretraining (CPT) with Kazakh as a primary
language**, the national programmes behind them, and Kazakh encoder models. Fine-tunes of foreign
models on Kazakh instruction data are listed only where they are named products or where they carry
published Kazakh evals. Speech (ASR/TTS) and embeddings are covered in `../asr-models.md` and in the
encoder table below (encoders are in scope here because they are pretraining-scale, not fine-tune-scale).

Conventions. Every number links to a page we opened. `n/p` = nothing published that we could find.
`unverified` = the id could not be confirmed against the HF API. HF ids, creation dates, parameter
counts and licenses below were read from `https://huggingface.co/api/models/<id>` on 2026-11-08
(`created` / `params` columns come from that API, not from press coverage). «доступна нам» = already
callable from our stack (aigw or self-hosted).

Not repeated here (already covered elsewhere in the repo): the DSML.KZ arena view
(`../dsml-models.md`), RU/KZ telephony ASR (`../asr-models.md`), and the judge-model shortlist
(`../llm-candidates.md`).

---

## 1. Kazakh-primary generative LLMs (national programmes)

| Model (HF id / product) | Org | Released | Type | Base | Size | Kazakh data | License | Published Kazakh evals | Weights | Source |
|---|---|---|---|---|---|---|---|---|---|---|
| `issai/LLama-3.1-KazLLM-1.0-8B` (+ `-AWQ4`, `-GGUF4`) | ISSAI, Nazarbayev University | 2024-12 | CPT + SFT of an open model | Llama 3.1 8B | 8.03 B (70B: 70.55 B params by API) | part of a **>150 B token** kk/ru/en/tr corpus, 95 % curated by ISSAI ("Token Factory"); Kazakh-only share not published → n/p | CC-BY-NC-4.0 | ISSAI's own suite (ARC/GSM8K/HellaSwag/MMLU/Winogrande/DROP in Kazakh): charts on the project page, no per-number text. **KazMMLU (ACL 2025, independent): 41.7 (English prompt) / 38.9 (Kazakh prompt)** as "KazakhLLM-8B". AlemLLM's vendor table puts KazLLM-1.0-70B at 0.766 avg on its Kazakh leaderboard | yes (gated `auto`) | [ISSAI KazLLM page](https://issai.nu.edu.kz/kazllm/), [2026-02-13 explainer](https://issai.nu.edu.kz/2026-02-13/issai-explains-kazllm-why-kazakhstan-built-its-own-large-language-model/), [KazMMLU Table 4/7](https://arxiv.org/html/2502.12829v2), [HF](https://huggingface.co/issai/LLama-3.1-KazLLM-1.0-8B) |
| `issai/LLama-3.1-KazLLM-1.0-70B` (+ `-AWQ4`, `-GGUF4`) | ISSAI NU | 2024-12 | CPT + SFT | Llama 3.1 70B | 70.55 B | same 150 B-token corpus; trained on 8× NVIDIA DGX H100 nodes (donated by a telecom, per ISSAI) | CC-BY-NC-4.0 | ISSAI claims it "almost achieved the metrics of GPT-4o" at release (Table 2 image, no machine-readable numbers). Independent KazMMLU row for 70B: n/p | yes (gated) | [ISSAI](https://issai.nu.edu.kz/kazllm/), [HF](https://huggingface.co/issai/LLama-3.1-KazLLM-1.0-70B) |
| `astanahub/alemllm` — **AlemLLM** · «доступна нам» (`alemai/astanahub/alemllm`) | Astana Hub / Alem.AI (ministry-backed), technical support 01.AI | 2025-07 (HF repo created 2025-07-29; public access announced 2025-08-08) | CPT + post-train of an open MoE | **01.AI Yi-Lightning** — DeepSeek-MoE architecture (`MoYiForCausalLM`, 112 routed + 2 shared experts, 6 active/token, 56 layers, vocab 100 352, SentencePiece) | **247 B total / 22 B active** | n/p — neither the gated card nor the press releases publish a Kazakh token count | Apache-2.0 on the HF card; the GGUF mirror states "research and non-commercial use only" (contradiction, unresolved) | Vendor leaderboard only: **Kazakh avg 0.826** (MMLU 0.757, ARC 0.949, GSM8k 0.917, WSC 0.837, HellaSwag 0.775, DROP 0.719), above DeepSeek-R1 0.798, GPT-4o 0.776, KazLLM-70B 0.766. No KazMMLU row. No third-party reproduction we could find | yes (gated `auto`, form) | [HF card](https://huggingface.co/astanahub/alemllm), [GGUF mirror with the tables](https://huggingface.co/Sherkhan243/alemllm-GGUF), [Astana Times 2025-08-08](https://astanatimes.com/2025/08/alemllm-kazakh-language-model-now-publicly-available/), [QazInform on the 01.AI partnership](https://qazinform.com/news/kazakhstan-launches-its-language-model-alemllm-in-partnership-with-01ai-42b1b3) |
| `inception42/Llama-3.1-Sherkala-8B-Chat` (canonical `inceptionai/…` redirects here) — **Sherkala** | Inception (G42) + MBZUAI, on Cerebras | 2025-02 (repo 2025-02-07) / paper 2025-03, COLM 2025 | CPT + IFT + safety tuning | Llama-3.1-8B, tokenizer vocab +25 % (monolingual Kazakh/Russian/Turkish BPEs merged in) | 8.29 B | **45.3 B tokens total: 19.45 B Kazakh + 19.45 B English + 6.4 B Russian/Turkish**; 76 % of the Kazakh part is Wikipedia/CommonCrawl/CulturaX/Kazakh news, the rest machine-translated English Wikipedia | **CC-BY-NC-SA-4.0** | Own paper, zero-shot LM-Eval harness, Kazakh avg across the suite: **Sherkala (base) 45.7, Sherkala-Chat 47.6** vs KazLLM-1.0-8B 43.7, Irbis-v0.1 37.7, Llama-3.1 39.8, Qwen-2.5 38.5, BLOOM 37.6. Independent **KazMMLU: 45.6 (English prompt) / 38.2 (Kazakh prompt)**. Generation: beats KazLLM-8B on Vicuna/MT-Bench Kazakh per paper and per DSML | yes (gated `auto`) | [arXiv 2503.01493](https://arxiv.org/abs/2503.01493), [HTML v2](https://arxiv.org/html/2503.01493v2), [HF](https://huggingface.co/inception42/Llama-3.1-Sherkala-8B-Chat), [Cerebras press release](https://www.cerebras.ai/press-release/inception-and-mbzuai-launch-sherkala-transforming-the-llm-landscape-for-kazakhstan) |
| `Gen2B/Irbis-7b-v0.1` — **Irbis-7B / IrbisGPT** | Gen2B.ai (with MOST Holding); community initiative | 2024-06 (repo 2024-03-31), instruct LoRA 2025-03 | CPT (+ QLoRA instruct) | Mistral-7B (`MistralForCausalLM`) | 7.47 B | **~20 GB raw text, "predominantly Kazakh, 5–10 % Russian" ≈ 2 B tokens**; tokenizer 32k → 60k; trained 7 days on 2× H100; SFT on ~200k translated Alpaca/Dolly samples | MIT | Sherkala's Table 4: **37.7 avg** (worse than KazLLM-8B). No KazMMLU row (n/p). No published eval of its own — "метрики будут представлены позже", never published | yes (open) | [HF](https://huggingface.co/Gen2B/Irbis-7b-v0.1), [Habr write-up](https://habr.com/ru/articles/825574/), [Forbes.kz 2024-06-25](https://forbes.kz/articles/v-kazahstane-poyavilsya-svoy-chatgpt-na-kazahskom-yazyke-e860dd) |
| `ai-forever/mGPT-1.3B-kazakh` | Sber AI (AI Forever) | 2023-08 | CPT | mGPT-XL 1.3B (GPT-2 style, 61 languages) | 1.3 B | n/p tokens; "150 000 steps, batch 4, ctx 2048, 1× A100" → ≈ 1.2 B tokens by arithmetic [INFERENCE] | MIT | val perplexity **3.38** (self-reported, no downstream benchmark) | yes (open) | [HF](https://huggingface.co/ai-forever/mGPT-1.3B-kazakh) |
| `TilQazyna/llama-kaz-instruct-8B-1` | Til-Qazyna (National Scientific-Practical Center, Ministry of Culture) | 2024-09 (repo), card updated 2026-08 | CPT + IFT | Meta-Llama-3-8B | 8.03 B | n/p | Apache-2.0 (card) | n/p | gated `manual` | [HF](https://huggingface.co/TilQazyna/llama-kaz-instruct-8B-1) |
| `AmanMussa/llama2-kazakh-7b-ver2` | Mussa Aman (individual) | 2023-12 | SFT (self-instruct) | Llama-2-7b-hf | 6.74 B | n/p | n/p on card | n/p | yes (open) | [HF](https://huggingface.co/AmanMussa/llama2-kazakh-7b-ver2) |

### 1.1 ISSAI Qwen3.5-Kazakh — the current Kazakh SOTA line, 2026-08

Same recipe at three sizes: **+16 000 Cyrillic-Kazakh tokenizer entries** (248 320 → 264 192, new
rows initialised by FVT = mean of constituent sub-token embeddings), **full-parameter CPT** on
**~15.7–15.9 B tokens at a 50/50 Kazakh:English mix** (Kazakh half = deduplicated FineWeb-2 +
CulturaX + FinePDFs + FineWiki + curated cultural/QA sets upsampled 3×; English half = replay mix),
then re-alignment to the official instruct checkpoint by **chat-vector merge**
(θ_cpt + (θ_inst − θ_base)), no SFT/RLHF of their own, then re-attaching the official vision tower.
Training: 2 node-groups × 8× H100.
**No Russian in the CPT mix** — Russian capability is inherited from stock Qwen3.5.
([35B base card](https://huggingface.co/issai/Qwen3.5-35B-A3B-Base-Kazakh),
[9B base card](https://huggingface.co/issai/Qwen3.5-9B-Base-Kazakh),
[4B base card](https://huggingface.co/issai/Qwen3.5-4B-Base-Kazakh),
[method, 35B instruct card](https://huggingface.co/issai/Qwen3.5-35B-A3B-Kazakh))

| Model | Size (API) | Created | KazMMLU | KazCulture | Belebele-kk | GSM8K (kk table) | EN MMLU | License | Notes |
|---|---|---|---|---|---|---|---|---|---|
| `issai/Qwen3.5-4B-Base-Kazakh` | 4.58 B | 2026-08-05 | n/p (base) | n/p | n/p | n/p | n/p | Apache-2.0 | CPT at seq len 32 768, tied embeddings |
| `issai/Qwen3.5-4B-Kazakh` | 4.58 B | 2026-08-05 | **78.5** (stock 72.5) | **55.4** (42.3) | 85.6 (84.6) | 89.0 (87.9) | — | Apache-2.0 | [card](https://huggingface.co/issai/Qwen3.5-4B-Kazakh) |
| `issai/Qwen3.5-9B-Base-Kazakh` | 9.54 B | 2026-08-05 | n/p | n/p | n/p | n/p | n/p | Apache-2.0 | CPT at seq len 32 768 |
| `issai/Qwen3.5-9B-Kazakh` | 9.54 B | 2026-08-05 | **83.1** (77.0) | **63.4** (49.5) | 87.9 (87.3) | 89.4 (90.4) | 82.8 (82.6) | Apache-2.0 | [card](https://huggingface.co/issai/Qwen3.5-9B-Kazakh) |
| `issai/Qwen3.5-35B-A3B-Base-Kazakh` | 34.73 B (MoE, ~3 B active, 256 experts top-8 + 1 shared) | 2026-08-05 | n/p | n/p | n/p | n/p | n/p | Apache-2.0 | CPT at seq len 16 384, untied embeddings, router aux-loss preserved |
| `issai/Qwen3.5-35B-A3B-Kazakh` · **«доступна нам»** (`qwen3.5-35b-a3b-kazakh`) | 35.17 B | 2026-08-05 | **84.0** (82.6) | **68.7** (60.3) | 88.9 (89.4) | 89.3 (92.7) | 89.3 (91.2) | Apache-2.0 | Thinking on, temp 1.0 / top_p 0.95 / top_k 20 / presence 1.5 / max 81 920. Card warns chains-of-thought get **shorter** (PolyMath −5.8, GPQA-Diamond −4.5) and vision regresses (OCRBench 42.4 → 34.0) |

These are the **only** Kazakh-primary models with published native-Kazakh benchmark scores from an
identified lab in 2026, and the only ones whose base model is a current-generation MoE reasoner.

---

## 2. From-scratch / small Kazakh base models (research-grade, not national programmes)

All independent or academic; none has a published native-Kazakh benchmark score.

| Model | Author | Released | Type | Size | Kazakh data | License | Evals | Weights | Source |
|---|---|---|---|---|---|---|---|---|---|
| `nur-dev/llama-1.9B-kaz` | Kadyrbek Nurgali (nur-dev) | 2024-08 (repo 2024-08-05) | **from scratch**, Llama arch | 1.94 B | n/p (Kazakh) | AFL-3.0 | n/p | gated `manual` | [HF](https://huggingface.co/nur-dev/llama-1.9B-kaz) |
| `nur-dev/llama-1.9B-kaz-instruct` | nur-dev | 2024-09 (repo 2024-09-03) | SFT of the row above (`base_model: nur-dev/llama-1.9B-kaz`) | 1.94 B | n/p | AFL-3.0 | n/p | gated `manual` | [HF](https://huggingface.co/nur-dev/llama-1.9B-kaz-instruct) |
| `nur-dev/gpt-j-3.4B-kaz` | nur-dev | 2024-08 (repo 2024-08-11) | GPT-J-arch Kazakh LM, no base model listed → **from scratch** | 3.48 B | trained on `nur-dev/kaz-for-lm` (size n/p) | AFL-3.0 | n/p | gated `manual` | [HF](https://huggingface.co/nur-dev/gpt-j-3.4B-kaz) |
| `nur-dev/farabi-1.7b` | nur-dev | 2026-02 (repo 2026-02-23, updated 2026-05-28) | CPT/finetune (`base_model: Qwen/Qwen3-1.7B`) | 2.03 B | n/p; languages kk/ru/en | Apache-2.0 | n/p | gated `manual` | [HF](https://huggingface.co/nur-dev/farabi-1.7b) |
| `stukenov/sozkz-core-llama-1b-kk-base-v1` (family 8 M–1.08 B) | Saken Tukenov | 2026-03 | **from scratch**, Llama (GQA) | 8 M–1.08 B | n/p | MIT | n/p | gated `manual` | [HF](https://huggingface.co/stukenov/sozkz-core-llama-1b-kk-base-v1), [collection](https://huggingface.co/collections/stukenov/sozkz-core-kazakh-language-models) |
| `stukenov/sozkz-core-qwen-500m-kk-base-v1` | Saken Tukenov | 2026-04 (repo 2026-04-10) | **from scratch**, Qwen2 arch | 447.5 M | n/p (Kazakh-only) | MIT | n/p | gated `manual` | [HF](https://huggingface.co/stukenov/sozkz-core-qwen-500m-kk-base-v1) |
| `stukenov/ekitil-core-qwen3-600m-kkru-base-v1` (123 M/300 M/600 M) | Saken Tukenov | 2026-04 (repo 2026-04-06) | **from scratch**, Qwen3, bilingual kk-ru | 123–674 M | n/p | MIT | n/p | gated `manual` | [HF](https://huggingface.co/stukenov/ekitil-core-qwen3-600m-kkru-base-v1) |
| `stukenov/sozkz-core-tinyllama-1b-kk-ru-v1` | Saken Tukenov | 2026-04 | CPT + tokenizer extension | 1.14 B | n/p | MIT | n/p | gated | [HF](https://huggingface.co/stukenov/sozkz-core-tinyllama-1b-kk-ru-v1) |
| `Eraly-ml/Kimi-K3-0.40B-Kazakh-CPT-59M` | Yeraly Gainulla | 2026-07 (repo 2026-07-29) | CPT, experimental hybrid KDA+MLA+MoE | 395.6 M | **~59 M cumulative Kazakh tokens** (self-reported) | MIT | n/p | yes (open) | [HF](https://huggingface.co/Eraly-ml/Kimi-K3-0.40B-Kazakh-CPT-59M) |
| `RedBullet12/LFM3-1.7B-Kazakh` | individual | 2026 (repo, 1.7B Kazakh LoRA merged) | LoRA SFT merged | 1.7 B | `AmanMussa/kazakh-instruction-v2` 52 123 rows (machine-translated Alpaca) | LFM Open License v1.0 | n/p (card warns: "do not use for factual questions") | yes (open) | [HF](https://huggingface.co/RedBullet12/LFM3-1.7B-Kazakh) |
| `Darmm/darmm-chat-kazakh-8b` | Rakhat Zhumabek (Darmm) | 2026-09 (repo 2026-09-09) | QLoRA SFT (r=32 α=64) | 8.19 B | 105 k instruction pairs (65 k Kazakh, 25 k RU, 15 k EN) | Apache-2.0 | **KazMMLU (3 000-q sample) 38.3** vs stock Qwen3-8B 27.9; **Belebele-kk 39.8** vs 27.2 | yes (open) | [HF](https://huggingface.co/Darmm/darmm-chat-kazakh-8b) |
| `Tohirju/qwen38-27b-kazakh-sft` | Tohir Saidzoda | 2026-08 (repo 2026-08-19) | SFT + tool-calling + GRPO variants | 26.9 B | n/p | n/p on card | n/p | gated `auto` | [HF](https://huggingface.co/Tohirju/qwen38-27b-kazakh-sft) |
| `issai/foggen` (+ `-qwen3-1.7b`, `-gemma3-1b`, `-gemma3-270m`, `-r15-oe`) | ISSAI | 2026-05 (repo 2026-05-20), R14 2026-11-03 | LoRA SFT, continual-learning chain, edge-cloud router | 270 M–1.7 B | includes a **Kazakh-culture** domain (`issai/KazCulture`); 1 800 rows/round | Apache-2.0 | Kazakh-culture domain: edge 90.9 %, cloud 96.2 %, FogGen routing 91.5 % with 1.1 % routed (16 217 q, 7 domains) | yes (open) | [HF](https://huggingface.co/issai/foggen) |

`issai/math_qolda` (2026-03) is an ISSAI maths fine-tune of the Qolda line; no separate Kazakh numbers ([HF](https://huggingface.co/issai/math_qolda)).

---

## 3. Kazakh encoder / masked-LM models (pretraining-scale)

| Model | Author | Released | Arch / params | Kazakh corpus | License | Published evals | Weights | Source |
|---|---|---|---|---|---|---|---|---|
| `kz-transformers/kaz-roberta-conversational` (**Kaz-RoBERTa**) | Beeline KZ / QazCode (VEON) + kz-transformers | 2023-04 (repo 2023-04-27) | RoBERTa-base, 83.5 M, BPE 52 000 | **25 GB** = MDBKD (24 883 808 unique Kazakh texts) + Beeline KZ customer-support dialogs; MLM 15 %, 2× V100, 500 k steps, batch 128, ctx 512 | Apache-2.0 | n/p (MLM only; TechRxiv DOI on card) | yes (open) | [HF](https://huggingface.co/kz-transformers/kaz-roberta-conversational). VEON calls it "the first Kazakh-language AI model with 2 billion parameters" — that figure does not match the 83.5 M safetensors count from the API; treat as a press error |
| `amandyk/KazakhBERTmulti` | Amandyk Kartbayev | 2023-05 (repo 2023-05-26) | BERT, ≈163 M, 100 k Kazakh vocab | n/p (Kazakh-only despite "multi") | AFL-3.0 | n/p | yes (open) | [HF](https://huggingface.co/amandyk/KazakhBERTmulti) |
| `Eraly-ml/KazBERT` | Yeraly Gainulla | 2025-03 (repo 2025-03-11) | BERT, 110.7 M, WordPiece trained on Kazakh; base `bert-base-uncased` | Kazakh Wikipedia (`amandyk/kazakh_wiki_articles`) + Kazakh Common Crawl (`Eraly-ml/kk-cc-data`); 20 epochs, batch 16, fp16 | Apache-2.0 | n/p (MLM); Zenodo paper [10.5281/zenodo.15565394](https://doi.org/10.5281/zenodo.15565394) | yes (open) | [HF](https://huggingface.co/Eraly-ml/KazBERT) |
| `nur-dev/roberta-kaz-large` | Kadyrbek Nurgali | 2024-07 (repo 2024-07-24) | RoBERTa-large, 355.4 M | MDBKD, **>5.3 M examples**, 10 epochs, 208 100 steps, 2× A100 | AFL-3.0 | n/p; base for `roberta-large-kazqad` QA fine-tunes | yes (open) | [HF](https://huggingface.co/nur-dev/roberta-kaz-large) |
| `HPLT/hplt_bert_base_kk` | HPLT (EU) | 2024-04 (repo 2024-04-22) | LTG-BERT, 153.3 M, vocab 32 768 | HPLT v1.2 Kazakh monolingual web corpus (size per HPLT report) | Apache-2.0 | reported in the [HPLT D4.1 LM report](https://hplt-project.org/HPLT_D4_1___First_language_models_trained.pdf) | yes (open) | [HF](https://huggingface.co/HPLT/hplt_bert_base_kk) |
| XLM-R / mBERT as the de-facto Kazakh encoders | Meta / Google | — | `xlm-roberta-base/large`, `bert-base-multilingual-cased` | Kazakh included in multilingual pretraining | MIT / Apache-2.0 | Kazakh NER/QA fine-tunes report best results on XLM-R-large (e.g. [yeshpanovrustem/xlm-roberta-large-kaznerd](https://huggingface.co/yeshpanovrustem/xlm-roberta-large-kaznerd)); a 2026 comparison finds mBERT/XLM-R at 82–85 % on Kazakh morphological tasks while KazBERT/KazRoBERTa beat them on text correction ([PMC12741073](https://pmc.ncbi.nlm.nih.gov/articles/PMC12741073/)) | open | [Frontiers 2026](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2026.1986970/abstract) |

**Takeaway for encoders:** no Kazakh encoder has ever published a classification/NER score table
comparable to multilingual-e5 or XLM-R on a shared benchmark; they survive mostly as fine-tuning
bases. For our judge there is nothing here to use.

---

## 4. National programmes and compute

| Item | Who | Status as of 2026-11 | Key facts | Source |
|---|---|---|---|---|
| **KazLLM as state property** | ISSAI NU ↔ Ministry of Digital Development (now Ministry of AI and Digital Development), Astana Hub, QazCode/Beeline (VEON) | Built Apr–Dec 2024; **non-exclusive licence transferred to Astana Hub, Dec 2024**; ISSAI states "we were not asked to develop KazLLM further" | Consortium coordinated by the Ministry; QazCode the only private funder of compute (8× DGX H100) + a private fund paid the team — explicitly "without reliance on public or taxpayer funds". GSMA Foundry Excellence Award 2025; AmCham Awards 2026 (28 Oct 2026); Yann LeCun cited it at the Paris AI Action Summit 2025 | [ISSAI 2026-02 explainer](https://issai.nu.edu.kz/2026-02-13/issai-explains-kazllm-why-kazakhstan-built-its-own-large-language-model/), [VEON PR 2024-12-11](https://www.veon.com/newsroom/press-releases/kazakh-language-gets-its-national-llm-with-a-groundbreaking-partnership-of-kazakh-research-institutions-and-veons-qazcode), [standard.kz AmCham](https://standard.kz/ru/post/2026_10_ii-na-kazaxskom-iazyke-proekt-kazllm-udostoen-nagrady-amcham-awards-2026-433) |
| **AlemLLM / Alem.AI** | Astana Hub technopark + Alem.AI international centre, Ministry of Digital Development, 01.AI support | Weights on HF (gated) since 2025-08; callable to us via aigw | 247 B-parameter MoE, "largest domestic Kazakh model"; intended for eGov / e-Otinish integration | [Astana Times](https://astanatimes.com/2025/08/alemllm-kazakh-language-model-now-publicly-available/), [osn.kz](https://osn.kz/news/alemllm-kazakhstan-ai-model-kazakh-language-2025) |
| **National AI Platform + AlemGPT** | JSC NITEC, under the Ministry of AI and Digital Development | `ai.gov.kz` lists AlemGPT as **live**, described as "Kazakhstan's national large language model"; pilot for public services launched **2026-07-07** by ministry order of 2026-06-17, runs to 2027-05-01 | AlemGPT is a **multi-agent platform**, not a published model: no HF repo, no architecture, no size, no benchmark. LLM inference is planned to run on the national supercomputer **AlemCloud**; PII stays in the closed government contour. The platform's own landing page counts "**National models 3 — KazLLM, AlemLLM, Sherkala**" and "**Largest model 247 B (AlemLLM)**" | [ai.gov.kz](https://ai.gov.kz/en), [orda.kz 2026-06-30](https://orda.kz/alem-gpt-vmesto-chinovnika-chto-umeet-zapuschennyj-dlja-gosuslug-ii-v-kazahstane-416356/), [el.kz 2026-02-05 (ministry answer)](https://el.kz/ru/alemgpt-i-natsionalnye-yazykovye-modeli-kakim-budet-kazahstanskiy-chatgpt_400043935/), [adilet legal act G26IPM00326](http://insecure.zan.kz/rus/docs/G26IPM00326) |
| **Compute: two TOP500 systems** | Ministry of AI + Kazakhtelecom/Alem.AI + KazNU | "First country in Central Asia with two supercomputers on the TOP500", ranks **#86 and #103** | **Alem.Cloud** (HPE Cray XD670, Xeon Platinum 8568Y+, NVIDIA H200 SXM5 141 GB, 400 g Ethernet) — **Rmax 20.48 PFlop/s**, commissioned 2025-07 ([TOP500 180404](https://www.top500.org/system/180404/)). **AI-Farabium** (Supermicro SYS-821GE-TNHR, H200 SXM5, ConnectX-7 NDR) — **Rmax 17.93 PFlop/s** ([TOP500 180440](https://new.top500.org/system/180440/)). Also TPU + Habana accelerators on AlemCloud; Kazakhstan Data Center Valley near Ekibastuz (up to 1 GW) MoU signed 2026-05 at GITEX | [ai.gov.kz](https://ai.gov.kz/en), [el.kz 2026-07-20](https://el.kz/en/ai-year-in-kazakhstan-what-changed-in-the-first-half-of-2026_400050217/), [RUSI 2026](https://www.rusi.org/explore-our-research/publications/commentary/why-kazakhstan-joined-both-the-american-and-chinese-ai-initiatives) |
| **State research programme BR24993001** | Al-Farabi KazNU (PI Madina Mansurova) **in consortium with ISSAI** | "Creating an LLM to support the Kazakh language and technological progress", started 2024, closing 2026 | Deliverables from the project report: corpus of **400 million Kazakh words**, a pilot assistant on the **1.94 B-parameter Llama architecture** (`nur-dev/llama-1.9B-kaz`), open-source **8 B and 70 B** architecture work, hybrid tensor/model/pipeline parallelism, plus the first Kazakh HPC data centre as a shared lab. KazNU announced completion in 2026-08, highlighting **tool calling** as the shipped capability | [project report PDF](https://farabi.university/storage/files/2766837062687f828c0442d149835611_%D0%BE%D1%82%D1%87%D0%B5%D1%82-%D1%80%D1%83.pdf), [farabi.university news 2026-08-20](https://www.farabi.university/news/106430?lang=ru), [zakon.kz 2026-08-19](https://www.zakon.kz/nauka/6528643-kazakhskiy-yazyk-poluchit-sobstvennuyu-bolshuyu-iimodel.html), [ISSAI 2025 annual report](https://issai.nu.edu.kz/wp-content/uploads/2026/04/ISSAI-Annual-report-2025-March-19-1.pdf) |
| **ISSAI product line (closed weights)** | ISSAI NU | **Oylan** pilot 2025-01-17 → **Oylan 2.5** (July 2025, Latin-script support) → **Oylan 3** (2025-12-10, ISSAI Momentum): text+speech+image in kk (incl. Latin), ru, en, with web search, reasoning, RAG. No HF model, no published benchmark, no architecture | Oylan 1 training data was image-centric: **10 M images + 50 M QA pairs**, "the largest dataset ever created in Kazakhstan". Related: MangiSoz 3, TilSync 2, Beynele 2, Mangitas 02 inference server | [Oylan launch](https://issai.nu.edu.kz/2025-01-17/issai-launches-its-groundbreaking-language-vision-model-oylan-in-pilot-mode/), [ISSAI Momentum 2025-12-10](https://issai.nu.edu.kz/2025-12-10/issai-momentum-showcases-kazakhstans-homegrown-ai-innovations/), [2026-07-17 next-gen](https://issai.nu.edu.kz/2025-07-17/issai-unveils-kazakhstans-next-generation-of-ai-technologies), [oylan.nu.edu.kz](https://oylan.nu.edu.kz/oylan) |
| **ISSAI open-source position** | ISSAI | 2026-06-19 appeal to Kazakh companies to open-share Kazakh data/models | "18 open-source models and 50 datasets … the largest open-source collection of AI models and datasets in Central Asia"; **>500 000 downloads**, users in 38 countries; named users include Meta, OpenAI, Qwen, DeepSeek, Kaspi, **Freedom**, Beeline, AstanaHub, Halyk. Kazakh = **0.035 %** of Common Crawl 2026 (Estonia 0.168 %). ACL 2025 named Kazakhstan "The Rising Star" | [ISSAI 2026-06-19](https://issai.nu.edu.kz/2026-06-19/issai-invites-kazakhstani-companies-and-institutions-to-open-source-share-kazakh-language-datasets-and-models/) |
| **Qolda (Kazakh VLM + benchmark suite)** | ISSAI (IEEE Access 2026, DOI 10.1109/ACCESS.2026.3676919) | `issai/Qolda` 2025-11; **Qolda-AVL-5B/9B/34B** 2026-04→06; GGUFs 2026-08 | Qolda = InternVL3.5-4B vision tower + Qwen3-4B LM, 4.3 B, kk/ru/en. AVL = Qwen3-VL-Thinking + Whisper audio, all three modalities adapted to Kazakh | [Qolda card](https://huggingface.co/issai/Qolda), [Qolda-AVL-34B](https://huggingface.co/issai/Qolda-AVL-34B), [IEEE](https://ieeexplore.ieee.org/document/11454511), [deployment repo](https://github.com/IS2AI/Qolda-deployment) |

### 4.1 Qolda text scores (ISSAI's own benchmark suite, kk rows)

Useful here because it is the widest self-published Kazakh table for one lab
([card](https://huggingface.co/issai/Qolda)). Qolda No-Think/Think are the 4B model;
5B/9B/34B are Qolda-AVL variants (base `Qwen3-VL-4B/8B/32B-Thinking`, API-confirmed).

| Benchmark (Kazakh) | Qolda 4B no-think | Qolda 4B think | AVL-5B | AVL-9B | AVL-34B |
|---|---|---|---|---|---|
| KazMMLU | 58.11 | 66.14 | 69.27 | 73.04 | **78.98** |
| KazCulture | **53.00** | 47.45 | 44.75 | 56.39 | **62.37** |
| MMLU-kk | 58.39 | 69.28 | 73.07 | 73.89 | **81.94** |
| MMLU-Pro-kk | 40.62 | 57.68 | 62.21 | 64.28 | **73.67** |
| GPQA-kk | 31.89 | 38.60 | 47.91 | 46.97 | **58.77** |
| ARC-kk | 86.14 | 92.30 | 93.59 | 94.27 | **96.76** |
| GSM8K-kk | 73.01 | 83.00 | 85.75 | 83.17 | **90.52** |
| Belebele-kk | 81.07 | 82.91 | 81.70 | 84.76 | **88.78** |
| KazBench | 64.23 | 61.12 | 61.83 | 64.61 | **70.05** |
| KKCOPA | 70.00 | 73.79 | 76.60 | 78.11 | **79.60** |
| INCLUDE-kk | 45.20 | 46.00 | 53.80 | 57.20 | **61.80** |
| NIS Math-kk | 66.00 | 87.88 | 94.00 | 93.00 | **98.00** |
| RAGBench-kk | 54.95 | 66.81 | 52.12 | 62.91 | **69.98** |
| KazQAD | **70.99** | 67.40 | 42.28 | 65.76 | 70.36 |

MMLU-Pro / GPQA / ARC / INCLUDE also have Russian rows on the same card (RU best: 76.34 / 59.36 /
97.63 / 70.83 on AVL-34B) — the only Kazakh-lab table that reports Russian at all.

### 4.2 Independent KazMMLU scores for the national models

From the KazMMLU paper (ACL 2025, [arXiv 2502.12829](https://arxiv.org/html/2502.12829v2), 27 models,
zero-shot, 9 870 Kazakh questions; columns are STEM/SocSci/Humanities/Language/Other/**Average**):

| Model | English prompt | Kazakh prompt |
|---|---|---|
| KazakhLLM-8B (= `issai/LLama-3.1-KazLLM-1.0-8B`) | 40.3 45.6 44.0 31.3 38.6 **41.7** | 36.9 39.4 47.0 28.4 33.9 **38.9** |
| Sherkala-Chat-8B | 43.1 49.8 50.0 34.9 38.3 **45.6** | 36.6 39.5 43.4 30.0 34.6 **38.2** |
| Llama3.1-8B (control) | 37.9 44.6 41.7 28.9 38.3 **39.7** | 34.3 39.5 38.6 28.0 31.5 **36.0** |
| Llama3.1-70B (control) | 58.0 59.1 57.4 41.8 49.3 **56.2** | 58.8 64.3 64.5 44.4 50.3 **59.9** |
| GPT-4o | 70.0 81.9 83.3 73.4 62.1 **76.6** | — |
| DeepSeek V3 | 77.6 81.3 78.9 61.2 65.1 **76.9** | 45.4 48.0 47.8 37.4 33.3 **45.5** |
| YandexGPT | 54.8 70.6 63.7 42.6 57.0 **60.2** | — |
| Irbis-7B / AlemLLM / Qwen3.5-*-Kazakh | not evaluated in the paper (n/p) | — |

Read this together with §1: on the **native** KazMMLU, the 2024–2025 national Kazakh models score
38–46, while stock frontier models score 60–77. The 2026 ISSAI Qwen3.5-Kazakh line reports KazMMLU
78–84 — a different scale of result, and self-published by the lab that also owns the benchmark suite.

---

## 5. Линейка версий (chronology)

| Date | Release | Source |
|---|---|---|
| 2023-04-27 | **Kaz-RoBERTa** (`kz-transformers/kaz-roberta-conversational`) — first open Kazakh RoBERTa, 25 GB corpus, Beeline/QazCode | [HF](https://huggingface.co/kz-transformers/kaz-roberta-conversational) |
| 2023-05-26 | **KazakhBERTmulti** (`amandyk/KazakhBERTmulti`), 100 k Kazakh vocab | [HF](https://huggingface.co/amandyk/KazakhBERTmulti) |
| 2023-08-10 | **mGPT-1.3B-kazakh** (Sber) — Kazakh CPT of mGPT-XL | [HF](https://huggingface.co/ai-forever/mGPT-1.3B-kazakh) |
| 2023-10-10 | **Tilmash** (ISSAI) — NLLB-1.3B kk/tr/ru/en translation (encoder-decoder, pre-LLM era) | [HF](https://huggingface.co/issai/tilmash), [arXiv 2403.19399](https://arxiv.org/abs/2403.19399) |
| 2023-12-13 | `AmanMussa/llama2-kazakh-7b-ver2` — first community Kazakh self-instruct fine-tune | [HF](https://huggingface.co/AmanMussa/llama2-kazakh-7b-ver2) |
| 2024-03-31 | **Irbis-7B v0.1** repo created (Gen2B) | [HF](https://huggingface.co/Gen2B/Irbis-7b-v0.1) |
| 2024-06-25 | **IrbisGPT** public release + Habr write-up — "first national open-source Kazakh LLM" | [Forbes.kz](https://forbes.kz/articles/v-kazahstane-poyavilsya-svoy-chatgpt-na-kazahskom-yazyke-e860dd), [Habr](https://habr.com/ru/articles/825574/) |
| 2024-04-22 | **HPLT Kazakh BERT** (`hplt_bert_base_kk`) | [HF](https://huggingface.co/HPLT/hplt_bert_base_kk) |
| 2024-07-24 | **RoBERTa Kazakh Large** (`nur-dev/roberta-kaz-large`), 355 M from scratch | [HF](https://huggingface.co/nur-dev/roberta-kaz-large) |
| 2024-08-05 | **`nur-dev/llama-1.9B-kaz`** — 1.94 B Llama-arch Kazakh model from scratch (KazNU BR24993001 deliverable) | [HF](https://huggingface.co/nur-dev/llama-1.9B-kaz) |
| 2024-08-11 / 09-03 | `nur-dev/gpt-j-3.4B-kaz` (3.48 B, trained on `nur-dev/kaz-for-lm`) and `nur-dev/llama-1.9B-kaz-instruct` (SFT of the 1.9 B base) | [GPT-J](https://huggingface.co/nur-dev/gpt-j-3.4B-kaz), [instruct](https://huggingface.co/nur-dev/llama-1.9B-kaz-instruct) |
| 2024-09-17 | `TilQazyna/llama-kaz-instruct-8B-1` — Llama-3 8B CPT+SFT by the state language centre | [HF](https://huggingface.co/TilQazyna/llama-kaz-instruct-8B-1) |
| 2024-12-07…10 | **KazLLM 1.0**: `…-70B` (12-07), `…-8B` (12-08), AWQ4/GGUF4 quants (12-10). Presented to President Tokayev 2024-12-12 | [collection](https://huggingface.co/collections/issai/issai-kazllm-10-6732d58c81bcaf177442c362), [NU news](https://nu.edu.kz/news-en/nazarbayev-university-s-issai-presents-kazakh-large-language-model-kaz-llm), [VEON](https://www.veon.com/newsroom/press-releases/kazakh-language-gets-its-national-llm-with-a-groundbreaking-partnership-of-kazakh-research-institutions-and-veons-qazcode) |
| 2024-12 (end) | NU transfers a **non-exclusive KazLLM licence to Astana Hub**; ISSAI's mandate ends there | [ISSAI 2026-02-13](https://issai.nu.edu.kz/2026-02-13/issai-explains-kazllm-why-kazakhstan-built-its-own-large-language-model/) |
| 2025-01-17 | **Oylan** (language-vision assistant) pilot on `oylan.nu.edu.kz` | [ISSAI](https://issai.nu.edu.kz/2025-01-17/issai-launches-its-groundbreaking-language-vision-model-oylan-in-pilot-mode/), [Astana Times](https://astanatimes.com/2025/01/kazakhstan-launches-language-vision-ai-model-in-pilot-mode/) |
| 2025-01-21 | KazLLM GGUF4 quants published | [HF](https://huggingface.co/issai/LLama-3.1-KazLLM-1.0-8B-GGUF4) |
| 2025-02-07 | **Sherkala** repo created (Inception/MBZUAI), CC-BY-NC-SA-4.0 | [HF](https://huggingface.co/inception42/Llama-3.1-Sherkala-8B-Chat) |
| 2025-02-18 | **SHERKALA** public launch (Inception G42 + MBZUAI, Cerebras training) | [Cerebras PR](https://www.cerebras.ai/press-release/inception-and-mbzuai-launch-sherkala-transforming-the-llm-landscape-for-kazakhstan), [Middle East AI News](https://www.middleeastainews.com/p/inception-and-mbzuai-unveil-kazakh) |
| 2025-03-03 | Sherkala paper on arXiv (v2 2025-10-09; accepted **COLM 2025**). Weights published + GGUF (`DiDustin/sherkala_gguf`) | [arXiv 2503.01493](https://arxiv.org/abs/2503.01493) |
| 2025-02-24 / 2026-02-24 | `Sherkhan243/alemllm-GGUF` mirror created / last updated (BF16 461 GB, 11 parts) | [HF](https://huggingface.co/Sherkhan243/alemllm-GGUF) |
| 2025-06-19 | ISSAI + partners release Kazakh benchmark suite news cycle; KazMMLU underpins it | [KazMMLU](https://arxiv.org/abs/2502.12829) |
| 2025-07-17 | ISSAI "next generation" press briefing: **Oylan 2.5** (Latin script), MangiSoz 2.0, TilSync, Beynele, Mangitas | [ISSAI](https://issai.nu.edu.kz/2025-07-17/issai-unveils-kazakhstans-next-generation-of-ai-technologies), [ISSAI annual report 2025](https://issai.nu.edu.kz/wp-content/uploads/2026/04/ISSAI-Annual-report-2025-March-19-1.pdf) |
| 2025-07-29 | `astanahub/alemllm` created on HF | [HF](https://huggingface.co/astanahub/alemllm) |
| 2025-07 | **Alem.Cloud** supercomputer commissioned | [el.kz 2026-07-20](https://el.kz/en/ai-year-in-kazakhstan-what-changed-in-the-first-half-of-2026_400050217/) |
| 2025-08-07/08 | **AlemLLM opened to everyone** (minister Z. Madiyev); 247 B, "largest domestic Kazakh LLM" | [Astana Times](https://astanatimes.com/2025/08/alemllm-kazakh-language-model-now-publicly-available/) |
| 2025-11-14 | **Qolda** (`issai/Qolda`) repo created — 4.3 B Kazakh VLM | [HF](https://huggingface.co/issai/Qolda) |
| 2025-12-10 | **ISSAI Momentum**: **Oylan 3**, MangiSoz 3, TilSync 2, Beynele 2, Mangitas 02 | [ISSAI](https://issai.nu.edu.kz/2025-12-10/issai-momentum-showcases-kazakhstans-homegrown-ai-innovations/) |
| 2025-12-11 | `issai/Qolda_GGUF` | [HF](https://huggingface.co/issai/Qolda_GGUF) |
| 2026-03-26 | `issai/math_qolda` | [HF](https://huggingface.co/issai/math_qolda) |
| 2026-04-06 / 04-10 | **EkiTil** (kk-ru from-scratch Qwen3 123/300/600 M) and **SozKZ Core Qwen-500M** from-scratch base models | [EkiTil](https://huggingface.co/stukenov/ekitil-core-qwen3-600m-kkru-base-v1), [SozKZ](https://huggingface.co/stukenov/sozkz-core-qwen-500m-kk-base-v1) |
| 2026-04-27 → 06-02 | **Qolda-AVL-5B / -9B** repos created (audio-vision-language, Qwen3-VL-Thinking based) | [HF 5B](https://huggingface.co/issai/Qolda-AVL-5B), [HF 9B](https://huggingface.co/issai/Qolda-AVL-9B) |
| 2026-05-20 | **FogGen** (`issai/foggen`) edge-cloud confidence router incl. a Kazakh-culture domain; R14 refresh 2026-11-03 | [HF](https://huggingface.co/issai/foggen) |
| 2026-06-14 | **Qolda-AVL-34B** repo created (KazMMLU 78.98, best in the Qolda family) | [HF](https://huggingface.co/issai/Qolda-AVL-34B) |
| 2026-06-19 | ISSAI open-data/open-model appeal; states 18 models + 50 datasets, >500 k downloads, Freedom among named industrial users | [ISSAI](https://issai.nu.edu.kz/2026-06-19/issai-invites-kazakhstani-companies-and-institutions-to-open-source-share-kazakh-language-datasets-and-models/) |
| 2026-07-07 | **AlemGPT public-services pilot** starts (ministry order 2026-06-17), runs to 2027-05-01, LLMs on AlemCloud | [orda.kz](https://orda.kz/alem-gpt-vmesto-chinovnika-chto-umeet-zapuschennyj-dlja-gosuslug-ii-v-kazahstane-416356/), [adilet](http://insecure.zan.kz/rus/docs/G26IPM00326) |
| 2026-08-05 → 08-19 | **ISSAI Qwen3.5-Kazakh family**: Base + instruct at 4B / 9B / 35B-A3B published (tokenizer +16 k, ~15.7–15.9 B-token CPT, chat-vector merge) | [4B](https://huggingface.co/issai/Qwen3.5-4B-Kazakh), [9B](https://huggingface.co/issai/Qwen3.5-9B-Kazakh), [35B-A3B](https://huggingface.co/issai/Qwen3.5-35B-A3B-Kazakh) |
| 2026-08-19 | `Tohirju/qwen38-27b-kazakh-sft` (gated) | [HF](https://huggingface.co/Tohirju/qwen38-27b-kazakh-sft) |
| 2026-08-19 / 08-20 | KazNU announces completion of the **BR24993001** national Kazakh-LLM project (tool calling highlighted) | [zakon.kz](https://www.zakon.kz/nauka/6528643-kazakhskiy-yazyk-poluchit-sobstvennuyu-bolshuyu-iimodel.html), [farabi.university](https://www.farabi.university/news/106430?lang=ru) |
| 2026-09-09 | `Darmm/darmm-chat-kazakh-8b` (Qwen3-8B QLoRA, KazMMLU 38.3 vs 27.9 stock) | [HF](https://huggingface.co/Darmm/darmm-chat-kazakh-8b) |
| 2026-10-23 | Jensen Huang (NVIDIA) × minister Madiyev at Alem.AI, praises "Kazakhstan's own large language model"; ISSAI re-reports 150 B-token KazLLM figure | [ISSAI](https://issai.nu.edu.kz/2026-10-23/nvidia-ceo-jensen-huang-highlights-the-importance-of-kazakhstans-own-large-language-model/) |
| 2026-10-27 | ISSAI presents **Kazakh Latin-script LLM** work at **EMNLP 2026**; Qolda at the Kazakh speech-synthesis conference | [ISSAI EMNLP](https://issai.nu.edu.kz/2026-10-27/issai-researchers-present-research-on-kazakh-latin-script-and-large-language-models-at-emnlp-2026-an-a-conference/), [audit paper](https://aclanthology.org/2026.emnlp-main.1479.pdf) |
| 2026-10-27 | Inception ships **Jais 3** family (Arabic-first; **zero** Kazakh mentions in the 32B/375B cards) → no Kazakh successor to Sherkala from Inception | [Jais-3-32B](https://huggingface.co/inception42/Jais-3-32B), [Jais-3-375B-A23B](https://huggingface.co/inception42/Jais-3-375B-A23B) |
| 2026-10-28 | KazLLM project wins **AmCham Awards 2026** | [standard.kz](https://standard.kz/ru/post/2026_10_ii-na-kazaxskom-iazyke-proekt-kazllm-udostoen-nagrady-amcham-awards-2026-433) |
| 2026-11-03 | `issai/foggen` R14 + three sibling edge checkpoints refreshed | [HF](https://huggingface.co/issai/foggen) |

---

## 6. Names in the brief that we could NOT verify

- **«KazakhGPT»** — no HF model matches the name (`api/models?search=KazakhGPT` → empty). The closest
  real thing is the 2024 IrbisGPT community project (media called KazLLM "казахский ChatGPT"), plus
  `qazgpt.kz`, an unrelated private Kazakh-language wrapper around OpenAI models
  ([QazGPT](https://qazgpt.kz/blog.php?id=1)). Treat "KazakhGPT" as a media label, not a model id.
- **«Kaz-GPT»** — no such Kazakh model; HF hits are Russian-city (`mo-kazan/gpt-neo-2.7B`) and
  unrelated checkpoints. `issai/tilmash` is the actual ISSAI "GPT-era" Kazakh artefact.
- **«Barys»** — no Kazakh LLM by this name. The only HF hit is `ygtrpmkss/baryset` (created and last
  modified 2026-01-22, license OpenRAIL, 0 downloads, **empty card: no pipeline tag, no description, no
  metrics**), so it cannot be characterised at all, let alone as an LLM. The HF API search is the
  authority here and returns nothing else.
- **«Qolda»** is real but is a **vision-language** (and AVL audio-visual-language) family, not a text
  foundation model — §4.1.
- **«Sherkala 2» / Sherkala-70B** — n/p. Inception's 2026 output went into Jais 3 (Arabic); the only
  Kazakh Sherkala checkpoint in `api/models?author=inception42` and `?search=Sherkala` is the 8B Chat
  model, and the `inceptionai/…` id 301-redirects to `inception42/…`.
- **«KazLLM 2.0» / ISSAI text LLM after 1.0** — n/p. ISSAI's post-2024 text-LLM releases are the
  Qwen3.5-Kazakh family (§1.1); no 2.0 label exists on HF or in ISSAI news.
- **`astanahub/alemllm` card body** — still HTTP 401 for anonymous access; architecture and evals were
  reconstructed from the API (`MoYiForCausalLM`, `num_experts_per_tok: 6`) plus the verbatim GGUF mirror.

---

## 7. Вывод

1. **`issai/Qwen3.5-35B-A3B-Kazakh` (and the 9B/4B siblings, 2026-08) is the only Kazakh-primary model
   with strong, machine-readable native-benchmark numbers, and we already have it** — KazMMLU 84.0,
   KazCulture 68.7, Belebele-kk 88.9 against stock Qwen3.5-35B-A3B (82.6 / 60.3 / 89.4). Caveats from
   its own card: shorter chains-of-thought (PolyMath −5.8, GPQA-Diamond −4.5) and **no Russian in the
   CPT mix** — Russian is whatever stock Qwen3.5 does.
2. **AlemLLM (Astana Hub/Alem.AI, 247 B MoE on Yi-Lightning, Apache-2.0 card, 2025-07/08)** is the
   flagship of the national programme and is callable to us via aigw, but it is the weakest-evidenced
   model in this slice: every Kazakh/Russian number on its card is vendor-authored, it has no KazMMLU
   row, and the licence text on the card (Apache-2.0) contradicts the "research / non-commercial only"
   wording on its own GGUF mirror.
3. **Sherkala-8B (Inception G42 + MBZUAI, COLM 2025) is the best-documented national model**: 19.45 B
   Kazakh tokens of 45.3 B total, expanded tokenizer, an explicit safety stage, and independent KazMMLU
   confirmation (45.6, ahead of KazLLM-8B's 41.7 and of stock Llama-3.1-8B's 39.7). Dead end, though —
   no Sherkala 2 in 2026, and the licence is CC-BY-NC-SA-4.0.
4. **KazLLM 1.0 (ISSAI, 2024-12) is infrastructure with no owner now**: >150 B tokens of curated
   kk/ru/en/tr data, CC-BY-NC-4.0, licence handed to Astana Hub in Dec 2024, and ISSAI has said openly
   it was never asked to continue. Its independent KazMMLU score (41.7 at 8B) is below stock frontier
   models and it is not competitive with the 2026 Qwen-based line.
5. **The government programme is a platform, not a model**: AlemGPT (NITEC, live, public-services pilot
   2026-07-07 → 2027-05-01) runs agents on the two TOP500 machines (Alem.Cloud 20.48 PFlop/s #86,
   AI-Farabium 17.93 PFlop/s #103), while `ai.gov.kz` still counts the *national* model set as KazLLM +
   AlemLLM + Sherkala. The only state-funded from-scratch Kazakh model we can point at in weights is
   `nur-dev/llama-1.9B-kaz` (1.94 B, KazNU BR24993001, gated, no evals), and the KazNU programme closed
   in Aug 2026 with "tool calling" as the headline result and no public benchmark.
