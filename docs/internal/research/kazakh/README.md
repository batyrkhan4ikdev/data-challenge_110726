# Kazakh-language models: research index (2026-11-08)

The m3 research agents (Qwen 3.8 Flash) wrote these files from primary sources: HF model cards and the HF API, papers, official sites, LinkedIn and news. Every number is linked inside the file. The integrator checked a sample of the HF ids by hand against `huggingface.co/api/models/<id>`.

| File | Scope |
|---|---|
| [llm-foundation.md](llm-foundation.md) | national / from-scratch LLMs and encoders, state programmes and compute, a version chronology |
| [llm-finetunes.md](llm-finetunes.md) | Kazakh fine-tunes, LoRAs and merges of open LLMs; the SFT datasets behind them |
| [speech.md](speech.md) | Kazakh ASR and TTS, RU↔KZ code-switching |
| [industry.md](industry.md) | who builds and deploys Kazakh AI in Kazakhstan; contact-centre speech analytics |
| [benchmarks.md](benchmarks.md) | KazMMLU, Belebele-kk, Kazakh arenas and leaderboards: top scores by model |

Related: `../dsml-models.md` (the DSML.KZ arena view), `../asr-models.md`, `../freedomspeech.md`.

## What it means for our judge

**Kazakh is not where our judge loses points.** The current control setting (`h200-gemma · per_criterion`, final notes) scored against the 65-dialog gold, split by chat language:

| language | chats | matching verdicts |
|---|---|---|
| EN | 15 | 116 / 120 (0.967) |
| **KZ** | 15 | **115 / 120 (0.958)** |
| RU | 30 | 224 / 240 (0.933) |

The best-documented Kazakh LLM is `issai/Qwen3.5-35B-A3B-Kazakh`, with KazMMLU 84.0 and Belebele-kk 88.9 (llm-foundation.md §1.1). We self-host it as `h200-kz`. Head-to-head on the same gold (2026-11-08, `bench/results/20261108-005401`, `-005403`):

| judge | all 60 chats | **KZ chats (15)** | total MAE |
|---|---|---|---|
| gemma-4 31B · per_criterion (control) | **0.939** | **0.957** | 4.51 |
| issai Qwen3.5-35B-A3B-Kazakh · single | 0.842 | 0.858 | 11.90 |
| issai Qwen3.5-35B-A3B-Kazakh · per_criterion | 0.767 | 0.710 | 14.29 |

A high Kazakh knowledge score did not translate into rubric-judging accuracy, not even on the Kazakh chats. No published Kazakh benchmark measures judging (benchmarks.md §7).

So swapping the judge for a Kazakh-specific LLM is not justified. The remaining judge errors are RU-heavy and sit on c04 and c06, and they are mostly ties within the gold itself.

## Where Kazakh models could matter: speech

All 5 DEV calls are Russian, so the ASR benchmark (`../../bench/asr/summary.md`) had no Kazakh audio to test on. Real Freedom calls mix RU and KZ. The verified open candidates for Kazakh ASR (HF ids checked on 2026-11-08):

| HF id | what | size | note |
|---|---|---|---|
| `baisalovar/Tynda-ASR-kk-ru` | Nemotron-3.5-Transcribe-30B-A4B, LoRA fine-tune for kk+ru | 33.7 B params, BF16 | published 2026-11-06; punctuation, timestamps, diarization; NeMo/vLLM plugin; OpenMDW-1.1 |
| `alibiserikbay/k5-kazakh-russian-stt` | GigaAM-Multilingual fine-tune, CTC + KenLM, streaming | 585 M params | built for mixed kk↔ru speech (KSC2 mixed WER 11.19 per speech.md); CC-BY-SA-4.0; lowercase |
| `shyngys879/kazakh-whisper-large-v3-turbo` | Whisper large-v3-turbo fine-tune | 809 M params | 5.2k downloads, Apache-2.0; kk only; drops into the existing faster-whisper / WhisperX hub |

If Kazakh call audio becomes available, the cheapest test is `shyngys879/kazakh-whisper-large-v3-turbo` behind the existing `hk-asr` hub as one more `config/asr.toml` entry. The strongest is Tynda-ASR on its own H200. Neither is part of the submission.
