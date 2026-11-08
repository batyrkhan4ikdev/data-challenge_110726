# LLM candidates for the CQA judge (as of 2026-11-07; GitHub issue #32)

Every number has a source link. "n/p" means nothing published that we could find.

## 1. H200 rental price (on-demand, per GPU-hour)

| Provider | $/GPU-h | Date | Source |
|---|---|---|---|
| Vast.ai (median of 6 hosts, range 3.63–5.54) | 3.85 | 2026-11-03 | [Thunder Compute tracker](https://www.thundercompute.com/blog/nvidia-h200-pricing) |
| RunPod | 5.29 | 2026-11-04 | [runpod.io/pricing](https://www.runpod.io/pricing) |
| Nebius (HGX H200) | 5.40 | 2026-11-07 (page read) | [nebius.com/prices](https://nebius.com/prices) |
| CoreWeave (HGX H200 node $50.44 ÷ 8) | 6.31 | 2026-11-07 (page read) | [coreweave.com/pricing](https://www.coreweave.com/pricing) |

Lambda no longer lists a self-serve H200 ([lambda.com/pricing](https://lambda.com/pricing)). Hyperscalers cost $7.91–$10.85 (AWS to Google) per the Thunder tracker, so they are out of scope.

**Median of the four = $5.35/GPU-h** ((5.29 + 5.40) / 2). That is $0.001486 per GPU-second. README formula: `cost per evaluation = $/h × GPU-seconds per evaluation ÷ concurrency ÷ 3600`.

## 2. Paid API list prices (USD per 1M tokens, input / output)

| Tier | Model | In / Out | Strict JSON-schema output | Source |
|---|---|---|---|---|
| Cheap | Gemini 3.8 Flash | 0.75 / 3.75 until 2026-12-31, then 1.50 / 7.50 | Yes, `response_format` JSON schema | [pricing](https://ai.google.dev/gemini-api/docs/pricing), [structured output](https://ai.google.dev/gemini-api/docs/structured-output) |
| Cheap | GPT-6 Luna (mini-class: GPT-5.4-mini is 0.75 / 4.50) | 0.10 / 0.50 | Yes, `json_schema` with `strict: true` | [pricing](https://developers.openai.com/api/docs/pricing), [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs) |
| Cheap | Claude Haiku 5.5 (prompts ≤100k) | 0.10 / 0.50 | Yes, `output_config.format` | [pricing](https://platform.claude.com/docs/en/about-claude/pricing), [structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) |
| Frontier | Claude Sonnet 5.5 | 2 / 10 | Yes (same docs) | same |
| Frontier | Claude Opus 5.5 | 4 / 20 | Yes | same |
| Frontier | GPT-6.1 Sol / GPT-6 Astra | 2 / 10 / 10 / 50 | Yes | OpenAI links above |
| Frontier | Gemini 4 Argon | 2 / 10 until 2026-11-30, then 4 / 20 | Yes | Google links above |

Batch halves the Claude and OpenAI prices. Per-model structured-output support: only Claude's page lists supported models (Haiku 5.5 and Sonnet 5.5 are included). Google's and OpenAI's pages state the feature generally, not per model.

## 3. Kazakh and Russian quality evidence

| Model | KZ evidence | RU evidence |
|---|---|---|
| `gemma-4:31b` | n/p KZ-specific score. [Card](https://huggingface.co/google/gemma-4-31B-it): pre-trained on 140+ languages, MMMLU 88.4% (multilingual MMLU, not Kazakh). DSML arena note (Telegram, via `telegram-models.md`): Gemma "стабильно сильные" on Kazakh generation. | n/p RU-specific; only the MMMLU figure |
| `gpt-oss:120b` | Community [KazBench real-data run](https://github.com/Yersultan04/kazbench/blob/master/results/real/REAL_DATA_LEADERBOARD.md) (Groq, n=60 per task, unvalidated items): overall 71.7, ЕНТ knowledge 56.7, sentiment 86.7. Same run: gemini-2.5-flash 87.5 overall, gpt-4o-mini 71.7. [Card](https://huggingface.co/openai/gpt-oss-120b) makes no language claims. | n/p |
| `issai/Qwen3.5-35B-A3B-Kazakh` | [Card](https://huggingface.co/issai/Qwen3.5-35B-A3B-Kazakh), thinking on: KazMMLU 84.0 (base Qwen3.5-35B-A3B 82.6), KazCulture 68.7 (60.3), Belebele 88.9 (89.4). English MMLU falls 91.2 → 89.3. The DSML arena note says ISSAI models were weak at generation, but it is an older Telegram claim and not tied to this model. | n/p (the card has no Russian benchmark) |
| `Muse-Glimmer-30B` | n/p numbers. [Card](https://huggingface.co/meta-models/Muse-Glimmer-30B): "trained on more than 100 languages", "not evaluated on all languages". Telegram claim: "хорошо работает на казахском". It appears in the NeurIPS-workshop [Kazakh evaluation audit](https://neurips.cc/virtual/2026/loc/sydney/178282), but I could not read its per-model scores (OpenReview blocked). The card names LLM-as-a-judge as an intended use. | n/p |
| `Nemotron-3.5-Bolt-74B-A9B` | n/p. [Card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-BF16) language list: en, es, fr, de, it, ja (input section adds hi, ko, pt, zh). No Kazakh, no Russian. | none claimed |

Gold set B5 stays the only accuracy signal. KazMMLU, KazBench and the DSML arena measure knowledge or generation, not judging.

## 4. Thinking mode as a judge

**Accuracy.** Published evidence is positive but not on our setting:
- Qwen3 0.6–4B on RewardBench: thinking gives about +10 points for under 2× FLOPs, and the benefit carries to the multilingual extension ([Jayarao et al.](https://arxiv.org/abs/2509.13332)).
- Reasoning models are more accurate judges, especially on reasoning-intensive tasks, but they still show strong biases ([Huang et al., EvalEval 2026](https://aclanthology.org/2026.evaleval-1.13/)).
- n/p for gpt-oss low/medium/high, Gemma 4 or Qwen3.5 as rubric judges, or any of them on Kazakh. We have to measure it.

**Conflict with strict `json_schema` in vLLM.** Mostly no, with caveats.
- vLLM's [reasoning parsers](https://docs.vllm.ai/en/latest/features/reasoning_outputs/) list `json` structured-output support for `gemma4` and `qwen3`. [Structured outputs](https://docs.vllm.ai/en/latest/features/structured_outputs/) states that any structured feature works with reasoning models. The reasoning goes to the `reasoning` field and the schema constrains `content`.
- Gemma 4 thinking is off by default; enable it with `chat_template_kwargs.enable_thinking=true` or by setting `reasoning_effort`. Qwen3 thinking is on by default in vLLM; disable it with `enable_thinking=false`.
- Known failure mode: reasoning tokens share `max_tokens`. A long chain gives `finish_reason=length` and `content=null`. Think profiles need a larger `max_tokens`, and the client already retries invalid replies.
- gpt-oss uses the Harmony channels. vLLM enforces the schema only after the `final` channel starts. The issue [#23120](https://github.com/vllm-project/vllm/issues/23120) was closed "not planned": output on other channels is not enforced. The decode stall at long reasoning ([#37897](https://github.com/vllm-project/vllm/issues/37897)) was fixed 2026-04-21. [#45736](https://github.com/vllm-project/vllm/issues/45736) reports `content: null` with `finish_reason="stop"`. Validate output, and compare low and medium on the invalid-reply rate as well as on accuracy.

## 5. Recommended phase-1 matrix (6 runs)

| # | Profile | Setting | Why |
|---|---|---|---|
| 1 | `h200-gptoss-low` | `reasoning_effort=low` | Cheap MoE baseline and the current default |
| 2 | `h200-gptoss-med` | `reasoning_effort=medium` | Tests whether the extra reasoning pays |
| 3 | `h200-gemma` | thinking off | The Gemma family leads the DSML Kazakh arena; the dense model is the likely accuracy leader |
| 4 | `h200-gemma-think` | `enable_thinking=true` | Thinking on/off for Gemma |
| 5 | `h200-kz` | thinking off | KZ-tuned, and fast |
| 6 | `h200-kz-think` | `enable_thinking=true` | The card's benchmarks use thinking; its authors warn about shorter chains |

Left out: Glimmer and Nemotron. Nemotron lists no Russian or Kazakh. Glimmer has no numbers, and it needs a 4th card (see `telegram-models.md`); add it only if a card is free. A paid reference (Sonnet 5.5, Gemini 3.8 Flash) is optional and wins only by more than 5 points of agreement (plan task B6).

## Recommendations for this repo

Set `usd_per_hour = 5.35` on every `kind = "gpu"` profile. Keep each profile's `concurrency` equal to its `max_concurrency` until phase 1 measures real throughput.

```toml
[profiles.h200-gemma]            # existing; thinking off; change only the price
cost = { kind = "gpu", usd_per_hour = 5.35, concurrency = 16 }

[profiles.h200-gemma-think]
provider = "openai"
base_url_env = "H200_GEMMA_BASE_URL"
api_key_env = "H200_API_KEY"
model = "gemma-4:31b"
supports_n = true
structured = "json_schema"
max_concurrency = 16
max_tokens = 8192
extra_body = { chat_template_kwargs = { enable_thinking = true } }
cost = { kind = "gpu", usd_per_hour = 5.35, concurrency = 16 }

[profiles.h200-gptoss-low]       # rename of the existing h200-gptoss
provider = "openai"
base_url_env = "H200_GPTOSS_BASE_URL"
api_key_env = "H200_API_KEY"
model = "gpt-oss:120b"
supports_n = true
structured = "json_schema"
max_concurrency = 48
max_tokens = 4096
extra_body = { reasoning_effort = "low" }
cost = { kind = "gpu", usd_per_hour = 5.35, concurrency = 48 }

[profiles.h200-gptoss-med]
provider = "openai"
base_url_env = "H200_GPTOSS_BASE_URL"
api_key_env = "H200_API_KEY"
model = "gpt-oss:120b"
supports_n = true
structured = "json_schema"
max_concurrency = 48
max_tokens = 8192
extra_body = { reasoning_effort = "medium" }
cost = { kind = "gpu", usd_per_hour = 5.35, concurrency = 48 }

[profiles.h200-kz]               # existing; thinking off; change only the price
cost = { kind = "gpu", usd_per_hour = 5.35, concurrency = 48 }

[profiles.h200-kz-think]
provider = "openai"
base_url_env = "H200_KZ_BASE_URL"
api_key_env = "H200_API_KEY"
model = "qwen3.5-35b-a3b-kazakh"
supports_n = true
structured = "json_schema"
max_concurrency = 48
max_tokens = 8192
extra_body = { chat_template_kwargs = { enable_thinking = true } }
cost = { kind = "gpu", usd_per_hour = 5.35, concurrency = 48 }
```

README cost line: "H200 at $5.35/GPU-h (median of Vast, RunPod, Nebius, CoreWeave on-demand, 2026-11)". For paid profiles use `cost = { kind = "tokens", usd_per_mtok_in = …, usd_per_mtok_out = … }` with the table in section 2.
