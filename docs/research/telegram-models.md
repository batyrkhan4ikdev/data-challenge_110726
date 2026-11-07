# Models and Kazakh data seen in our Telegram feeds (as of 2026-11-07)

Sources: the user's Telegram folder «Новости» (AI channels: Machinelearning, Data Secrets, эйай ньюз, Анализ данных, NN, AI Radar (DSML.KZ), DSML.KZ Новости, Devs.kz) and the DSML.KZ Public chat. Searched 435 queries and got 734 unique messages since 2025-01 (Kazakh queries) or 2026-09 (model queries). Hugging Face ids were checked against the HF API on 2026-11-07.

## Kazakh dataset link (DSML.KZ)

- **Awesome Kazakh Datasets** by Асель Ермекова: <https://github.com/Allessyer/awesome-kaz-datasets>.
  - Posted in DSML.KZ Новости #1258 (2026-08-18) and Devs.kz #7229.
  - Contents: 113 datasets in total. 70 are text/NLP/LLM, 25 speech and 18 vision. The catalog was last verified 2026-08-21.
- **Companion catalog: awesome-kaz-models**: <https://github.com/alenisaw/awesome-kaz-models>, linked from the README above.

None of the datasets is contact-center or QA-grading data, so neither catalog gives us training or gold data for this task. These are the parts we can use:

| Dataset | Use for us |
|---|---|
| [issai/IFBench_Kazakh](https://huggingface.co/datasets/issai/IFBench_Kazakh) (444) | Fast screen of Kazakh instruction-following per candidate model |
| [MBZUAI/KazMMLU](https://huggingface.co/datasets/MBZUAI/KazMMLU) (10,969 KZ) | Kazakh knowledge sanity check; not judge accuracy |
| [nurkhan5l/kazakh-ift](https://huggingface.co/datasets/nurkhan5l/kazakh-ift) (gated) | Kazakhstani public-service instructions; only if we fine-tune, which is out of scope |

Benchmark decision unchanged: the 24-dialog gold set (B5) stays the only accuracy signal. IFBench_Kazakh is optional for B4 phase 1, only to break ties on Kazakh quality.

## Candidate open models that fit one H200 (141 GB)

| Model (HF id) | Size | License | Why it is relevant | Source |
|---|---|---|---|---|
| `meta-models/Muse-Glimmer-30B` | 30B (29.8B safetensors) | Apache-2.0 | DSML.KZ Новости #1256: «модель хорошо работает на казахском языке». Agentic, runs locally | DSML.KZ Новости #1256 (2026-08-13), Machinelearning #10679 |
| `nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-BF16` | 74B MoE, 9B active | NVIDIA open | Compressed Nemotron 3.5 Super VL; 74B total fits in bf16 | Machinelearning #11264 (2026-11-02) |
| `issai/Qwen3.5-35B-A3B-Kazakh` | 35B MoE, 3B active | per card | Already served as `h200-kz` | awesome-kaz-models #7 |
| `ricursiveAI/Ripple-65B-Preview` | 65B dense | per card | Coding and agents focus; preview | Анализ данных #6080 (2026-11-05) |
| `Darmm/darmm-chat-kazakh-8b` | 8B (Qwen3-8B QLoRA) | per card | Kazakh chat, small | awesome-kaz-models #5 |
| `Tohirju/qwen38-27b-kazakh-tool` | ~27B | gated | Kazakh SFT plus tool-calling (GRPO variant) | awesome-kaz-models #8 |
| `inceptionai/Llama-3.1-Sherkala-8B-Chat` | 8B | gated | Second place in the DSML Kazakh LLM arena (2025); older | DSML.KZ Новости #1120, #1121 |

DSML Kazakh LLM arena (#1121, 2025-05): «Модели Gemma … стабильно сильные; Sherkala-8B второе место; ISSAI … одни из самых слабых по генерации». That supports keeping `gemma-4:31b` as a primary candidate. It also means `h200-kz` must prove itself on gold, not on its "Kazakh-tuned" label.

## Seen but not usable on one H200, or not an instruct model

| Model | Reason |
|---|---|
| Muse Spark Open (816B / 42B active) | Too large; license has commercial restrictions |
| Kimi K3.1 Pro (2.8T), MiMo-2.6 (1.02T), Mistral Large 4 (1T), Step 5 Preview (600B) | Too large |
| Reflection Beam (501B / 23B active) | Weights "скоро", not out yet |
| ERNIE 5.5 Flash Base (280B), AliceAI-Foundation-80B-A3B-Base | Base checkpoints with no instruct alignment |
| Index-Translate 35B-A3B | Translation model; weights later |
| Til-Core-0.5B, SozKZ, EkiTil | Sub-1B Kazakh base models |

## Proposed change (needs the user's approval: adds a 4th H200)

Add `meta-models/Muse-Glimmer-30B` as profile `h200-glimmer` in benchmark phase 1. It is the only new candidate with a direct claim of good Kazakh quality, and it is Apache-2.0 and small. `Nemotron-3.5-Bolt-74B-A9B` is the second choice if a card is free. If no card is free, swap Glimmer in place of the weakest model after phase 1.
