# ASR models for RU/KZ telephone calls (as of 2026-11-07)

Candidates for a one-night benchmark on our 5 DEV calls (mono 16 kHz MP3, 312–620 s, broker contact centre, RU/KZ
code-switch, names/numbers). Every number links to a page we opened; `n/p` = not published; *(inf)* = our inference.
**WER/CER are not comparable across rows** (normalisation and test sets differ) and **no model publishes results on real
8 kHz Kazakh calls** *(inf)*. Sber/T-Bank/NVIDIA/Google tables are vendor-authored.

## 1. Open-weight ASR

### 1.1 The only near-apples-to-apples ru+kk table
Sber's card scores five families under one protocol (lowercase, no punctuation, digits→words, greedy, ≤30 s; WER %).
"Internal" = Sber's own in-the-wild set → vendor benchmark. [ai-sage/GigaAM-Multilingual](https://huggingface.co/ai-sage/GigaAM-Multilingual), [arXiv 2607.10371](https://arxiv.org/abs/2607.10371).

| WER % | GigaAM-ML 220M | **GigaAM-ML large 600M** | Omnilingual-1B LLM | SeamlessM4T v2 | Whisper large-v3 |
|---|---:|---:|---:|---:|---:|
| ru CV / FLEURS / internal | 7.1 / 4.4 / 7.6 | **5.1 / 3.0 / 6.0** | 13.6 / 6.4 / 14.6 | 9.2 / 4.6 / 16.1 | 9.1 / 3.1 / 10.1 |
| kk CV / FLEURS / internal | 17.2 / 5.2 / 18.8 | **13.8 / 4.4 / 15.8** | 23.7 / 6.6 / 32.2 | 23.8 / 6.8 / 62.9 | 57.8 / 32.4 / 65.2 |

Takeaway *(inf)*: vanilla **Whisper is not viable for Kazakh**; `GigaAM-Multilingual` `large_ctc` is the best open
ru+kk single model; Omnilingual/Seamless are weak on spontaneous kk.

### 1.2 Inventory (languages verified on HF cards / API metadata)

| Model | HF id | ru | kk | size / license | published RU | published KK | serving |
|---|---|:-:|:-:|---|---|---|---|
| Whisper large-v3 | `openai/whisper-large-v3` | ✔ | ✔ | 1.55B / Apache-2.0 | §1.1; Sber Callcenter 23.1, OpenSTT phone 27.4 ([GigaAM evaluation.md](https://github.com/salute-developers/GigaAM/blob/main/evaluation.md)); T-Bank call-centre 19.39 ([T-one card](https://huggingface.co/t-tech/T-one)) | §1.1; FLEURS 31.10 self-rep. ([FT card](https://huggingface.co/shyngys879/kazakh-whisper-large-v3-turbo)) | transformers, [faster-whisper](https://huggingface.co/Systran/faster-whisper-large-v3) (MIT), vLLM, WhisperX |
| Whisper large-v3-turbo | `openai/whisper-large-v3-turbo` | ✔ | ✔ | 809M / MIT | n/p (independent) | FLEURS kk 19.75 self-rep.; KSC2 zero-shot 81.2 normalised ([arXiv 2603.00961](https://arxiv.org/abs/2603.00961)) | as above |
| Whisper kk fine-tunes | `shyngys879/kazakh-whisper-large-v3-turbo`, `InflexionLab/sybyrla` (80% KSC2+20% CV-ru), `olzhasAl/whisper-large-v3-tulpar` | partial (tulpar "may hallucinate on pure Russian", per card) | ✔ | 0.8–1.6B / Apache-2.0 | n/p | FLEURS kk 11.80 (CER 4.98); KSC2 test 17.7; ISSAI KSC 10.62 — all self-rep. ([card](https://huggingface.co/InflexionLab/sybyrla)) | transformers / CT2 (`shaipro/sybyrla-ct2`) |
| **GigaAM-Multilingual** | `ai-sage/GigaAM-Multilingual` rev. `ctc`/`large_ctc` | ✔ | ✔ (+ky,uz,en) | 220M/600M / MIT | §1.1 | §1.1 | `trust_remote_code`, ONNX `istupakov/gigaam-multilingual-large-ctc-onnx`; **already on aigw** |
| GigaAM-v3 | `ai-sage/GigaAM-v3` rev. `rnnt`/`ctc`/`e2e_*` | ✔ | ✘ | 220–240M / MIT | **Callcenter 9.5**, Golos farfield 3.9, RuLS 4.4, CV19 0.9, **OpenSTT phone 17.4** ([card](https://huggingface.co/ai-sage/GigaAM-v3), [paper](https://arxiv.org/abs/2506.01192)) | – | transformers/ONNX/GGUF |
| **T-one** (T-Bank) | `t-tech/T-one` | ✔ | ✘ | 71M streaming Conformer-CTC / Apache-2.0 | **call-centre 8.63**, telephony 6.20, **named entities 5.83**, CV19 5.32, OpenSTT 20.27/7.94 — vendor; Sber's re-run gives T-one+LM 13.5 vs GigaAM-v3 9.5 ([card](https://huggingface.co/t-tech/T-one)) | – | `tone` pkg, ONNX, Docker, Triton; "telephone-channel audio" |
| NVIDIA Canary / Parakeet | `nvidia/canary-1b-v2`, `nvidia/parakeet-tdt-0.6b-v3` | ✔ | **✘** | 1B/0.6B / CC-BY-4.0 | FLEURS ru 6.90 ([card](https://huggingface.co/nvidia/canary-1b-v2)) / 5.51 ([card](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3)) | none | NeMo/transformers/GGUF |
| NVIDIA kk+ru | `nvidia/stt_kk_ru_fastconformer_hybrid_large` | ✔ | ✔ | 115M / CC-BY-4.0 | Golos crowd 2.46, farfield 5.98, MCV12 6.29 | **KSC2 read 4.43 / spontaneous 15.25**, MCV17 15.48, KSD 7.08 ([card](https://huggingface.co/nvidia/stt_kk_ru_fastconformer_hybrid_large)) | NeMo, non-streaming, no punctuation |
| NVIDIA Nemotron-3.5 | `nvidia/NVIDIA-Nemotron-3.5-Transcribe-30B-A4B`, `nemotron-3.5-asr-streaming-0.6b` | ✔ | **✘** | 34B MoE (4.3B act.) / 0.6B; OpenMDW-1.1 | FLEURS ru 3.80, CoVoST2 2.47; speaker-attributed transcription + timestamps ([card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Transcribe-30B-A4B)) | none | NeMo Speech, vLLM/SGLang |
| Qwen3-ASR / Qwen3-Omni | `Qwen/Qwen3-ASR-1.7B`, `-0.6B`, `Qwen3-Omni-30B-A3B-Instruct` | ✔ | **✘** (30 langs + 22 zh dialects; kk absent) | 1.7B/0.6B / Apache-2.0 | FLEURS ru 5.99, CV ru 8.28 ([report](https://arxiv.org/html/2601.21337v1)) | n/p (unsupported) | `qwen-asr`, `qwen-asr-serve` (vLLM), streaming; hosted Flash: ru 4.81 ([card](https://huggingface.co/Qwen/Qwen3-ASR-1.7B)) |
| Vosk (Kaldi, CPU) | `vosk-model-kz-0.42` (1.3G), `vosk-model-small-kz-0.42` (58M), `vosk-model-ru-0.42` (1.8G) | ru model | kz model | Apache-2.0 | ru: **OpenSTT calls 36.0**, Golos crowd 4.4 | kz: FLEURS 13.09, CV17 12.50, KSC 4.49, KSC-Other 18.51 ([model list](https://alphacephei.com/vosk/models)) | CPU streaming, word timestamps |
| Meta MMS | `facebook/mms-1b-all` (adapter `kaz`) | ✔ | ✔ | 1B / **CC-BY-NC-4.0** | n/p | FLEURS kk 63.8 (no LM) / 19.5 (with CC n-gram LM); column mapping *(inf)* ([arXiv 2305.13516](https://arxiv.org/pdf/2305.13516)) | `load_adapter("kaz")` |
| Meta Omnilingual ASR | `facebook/omniASR-CTC-{300M,1B}`, `omniASR-LLM-{1B..7B}` | ✔ | ✔ (`kaz_Cyrl`, 1600+ langs) | 300M–7.8B / **Apache-2.0** | CTC-1B-v2 FLEURS ru 11.99 | CTC-1B-v2 FLEURS kk 13.34, KSC2-mixed 40.98 ([k5 card](https://huggingface.co/alibiserikbay/k5-kazakh-russian-stt)); kk fine-tune `tasmulaev/omniasr-ctc-300m-kk`: KSC2 18.64/CER 4.84 but ru regresses to 33.52 ([card](https://huggingface.co/tasmulaev/omniasr-ctc-300m-kk)) | `omnilingual-asr` (fairseq2), sherpa-onnx; [paper](https://arxiv.org/abs/2511.09690) |
| SeamlessM4T v2 | `facebook/seamless-m4t-v2-large` | ✔ | ✔ (101 speech-input langs) | 2.3B / **CC-BY-NC-4.0** | §1.1 | §1.1 | transformers / seamless_communication |
| k5 (GigaAM-ML derivative) | `alibiserikbay/k5-kazakh-russian-stt` | ✔ | ✔ | 600M CTC / **CC-BY-SA-4.0** | FLEURS ru 6.06 | FLEURS kk 9.14 (+KenLM), **kk↔ru mixed KSC2 11.19**; telephony only *simulated* ([card](https://huggingface.co/alibiserikbay/k5-kazakh-russian-stt)) | streaming 2-pass + KenLM + ITN + hotwords |
| Kazakh Nemotron LoRA | `Sherkhan243/Nemotron-3.5-Transcribe-kk-v2` | base only | ✔ | 30B-A4B / OpenMDW-1.1 | (base ru 3.80) | FLEURS kk 8.51/CER 2.22, KSC2 14.34/CER 4.60 ([card](https://huggingface.co/Sherkhan243/Nemotron-3.5-Transcribe-kk-v2)) | NeMo SpeechLM / vLLM |

**No kk (verified via HF language lists):** `ibm-granite/*-speech`, `mistralai/Voxtral-*`,
`CohereLabs/cohere-transcribe-03-2026` (14 langs), `moonshotai/Kimi-Audio-7B`, `nvidia/canary-qwen-2.5b` (en),
`microsoft/VibeVoice-ASR` (ru yes, kk no).

**ISSAI / AlemAI.** The `issai` org publishes **no ru/kk Whisper checkpoint** — only `issai/Persona-ASR` (kk+en
target-speaker, kk WER 43.49 on 3-speaker mixtures; [card](https://huggingface.co/issai/Persona-ASR)). "Kazrhut",
"SGLID", `AlemAI/KazNNM-*` return no HF repos ([search](https://huggingface.co/api/models?search=kazrhut)); ISSAI's open
ASR is ESPnet recipes ([IS2AI/Kazakh_ASR](https://github.com/IS2AI/Kazakh_ASR)); Alem's ASR is hosted-only (§3).
**The HF Open ASR Leaderboard has no ru or kk track** (multilingual = de/fr/it/es/pt) —
[leaderboard](https://huggingface.co/spaces/hf-audio/open_asr_leaderboard), [arXiv 2510.06961](https://arxiv.org/abs/2510.06961).

## 2. Diarization (2-speaker mono)

DER uses **different collars** per toolkit → not comparable across rows; score all candidates on our own labelled
calls with one collar *(inf)*. No published DER on Russian/Kazakh phone audio (n/p).

| Toolkit | id | published DER | mode | license |
|---|---|---|---|---|
| pyannote community-1 | `pyannote/speaker-diarization-community-1` | CALLHOME part2 **26.7** (collar 0), RAMC 20.8, DIHARD3 20.2 ([README](https://github.com/pyannote/pyannote-audio)) | offline, `num_speakers=2` | CC-BY-4.0, **gated** (HF token) |
| pyannote 3.1 | `pyannote/speaker-diarization-3.1` | CALLHOME part2 28.5 (collar 0) (same README) | offline | MIT code + gated weights |
| NeMo Sortformer v1 | `nvidia/diar_sortformer_4spk-v1` | CALLHOME 2-spk **6.49** (collar 0.25) ([card](https://huggingface.co/nvidia/diar_sortformer_4spk-v1)) | offline, ≤4 spk | **CC-BY-NC-4.0**; English-heavy training → ru/kk risk |
| NeMo Streaming Sortformer v2 | `nvidia/diar_streaming_sortformer_4spk-v2` | CALLHOME 2-spk **6.57** (0.25), CH109 4.88, DIHARD3 13.24 (0) ([card](https://huggingface.co/nvidia/diar_streaming_sortformer_4spk-v2)) | streaming+offline, ≤4 spk | **CC-BY-4.0** |
| DiariZen | `BUT-FIT/diarizen-wavlm-large-s80-md-v2` | DIHARD3 14.5 (vs 3.1: 21.7), RAMC 11.0 (vs 22.2); **no CALLHOME** ([card](https://huggingface.co/BUT-FIT/diarizen-wavlm-large-s80-md-v2), [repo](https://github.com/BUTSpeechFIT/DiariZen)) | offline | code MIT, **weights CC-BY-NC-4.0** |
| WhisperX | [m-bain/whisperX](https://github.com/m-bain/whisperX) | no DER published | offline | BSD (code); diarization **is** pyannote community-1 (needs HF token); kk aligner support unverified *(inf)*; [paper](https://arxiv.org/abs/2303.00747) |

**Operator/client roles.** Diarization yields only `speaker-0/1`; roles come from one LLM classifier over the diarized
turns (greeting, «Freedom Broker», verification questions, scripted offers ⇒ operator; IVR ⇒ bot; else client) — this is
our contract in `server/asr/to_record.py`. Hosted precedent: AssemblyAI Speaker Identification (`speaker_type: "role"`)
"infer[s] roles from context clues" and is documented for customer-service calls ([doc](https://www.assemblyai.com/docs/speech-understanding/speaker-identification.md));
the same docs advise ≥30 s of speech per speaker for stable labels ([doc](https://www.assemblyai.com/docs/pre-recorded-audio/label-speakers.md)).
No toolkit assigns roles itself *(inf)*.

## 3. Hosted APIs (official pages; $ per audio minute)

No vendor publishes ru/kk WER on telephone audio; the accuracy buckets below are vendor-claimed.

| Provider | ru | kk | diarization | price/min | 8 kHz |
|---|:-:|:-:|---|---|---|
| OpenAI `whisper-1` | ✔ | ✔ (Whisper 99-lang [tokenizer](https://raw.githubusercontent.com/openai/whisper/main/whisper/tokenizer.py)) | ✘ | $0.006; **deprecated → 2027-02-26** ([pricing](https://developers.openai.com/api/docs/pricing), [deprecations](https://developers.openai.com/api/docs/deprecations)) | n/p |
| OpenAI `gpt-4o-transcribe` / `-mini` / `gpt-transcribe` | n/p (no list published) | n/p | only `gpt-4o-transcribe-diarize` (`diarized_json`, [guide](https://developers.openai.com/api/docs/guides/speech-to-text)) | $0.006 / $0.003 / $0.0045 (same; `gpt-transcribe` [page](https://developers.openai.com/api/docs/models/gpt-transcribe)) — gpt-4o family deprecated | n/p |
| Google STT v2 `chirp_3` | ✔ GA | ✔ **Preview** `kk-KZ` | **not for ru or kk** (14 langs, Batch/Recognize only) | $0.016, dynamic batch $0.003 ([pricing](https://cloud.google.com/speech-to-text/pricing), [doc](https://docs.cloud.google.com/speech-to-text/docs/models/chirp-3)) | no `telephony` model for ru/kk ([langs](https://docs.cloud.google.com/speech-to-text/docs/speech-to-text-supported-languages)) |
| **Gemini `gemini-3.5-transcribe`** | ✔ | ✔ | **✔ ≤8 spk** | ≈$0.005 (32 tok/s) ([doc](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-transcribe), [pricing](https://ai.google.dev/gemini-api/docs/pricing)) | n/p (resampled to 16 kHz) |
| **Yandex SpeechKit v3** | ✔ | ✔ `kk-KZ` + per-sentence `auto` (code-switch) | ✔ `speaker_labeling`: **mono, max 2 speakers** | KZ region incl. VAT: async 4.04 KZT, deferred 1.03, streaming 4.31 ([pricing](https://yandex.cloud/ru-kz/docs/speechkit/pricing)) ≈ $0.008 async *(our conversion)* | **LPCM 8 kHz listed** ([formats](https://yandex.cloud/ru-kz/docs/speechkit/formats); [langs](https://yandex.cloud/ru-kz/docs/speechkit/stt/models), [roles](https://yandex.cloud/ru-kz/docs/speechkit/stt/speaker-labeling)) |
| Deepgram `nova-3` | ✔ | ✔ **monolingual `kk` only** (absent from the code-switch `multi` list) | ✔ included on pre-recorded | $0.0043 mono / $0.0052 multi batch ([pricing](https://deepgram.com/pricing), [langs](https://developers.deepgram.com/docs/models-languages-overview.md)) | phonecall models English-only |
| AssemblyAI `universal-2` | ✔ (bucket ≤10% WER) | ✔ (bucket 25–50%) | `speaker_labels` +$0.02/hr | $0.15/hr = $0.0025 ([pricing](https://www.assemblyai.com/pricing), [langs](https://www.assemblyai.com/docs/pre-recorded-audio/supported-languages)) | n/p; flagship `universal-3.5-pro` supports **neither** ([doc](https://assemblyai.com/docs/pre-recorded-audio/universal-3-5-pro.md)) |
| ElevenLabs `scribe_v2` | ✔ (bucket ≤5%) | ✔ (bucket >5–10%) | ✔ ≤32 spk | $0.22/hr = $0.0037 ([pricing](https://elevenlabs.io/pricing/api), [doc](https://elevenlabs.io/docs/overview/capabilities/speech-to-text)) | n/p |
| Soniox | ✔ | ✔ in-stream switching | bundled | ≈$0.0017 async ([pricing](https://soniox.com/pricing), [langs](https://docs.soniox.com/stt/concepts/supported-languages)) | n/p |
| **FreedomSpeech** (integrated) | ✔ | ✔ auto | ✔ `diarized_json`, ≤4 spk mono | n/p (no public price) | HTTP 8 kHz n/p; WS needs 16 kHz PCM ([docs](https://freedomspeech.kz/docs/)) |
| NCSpeech Studio (KZ) | ✔ | ✔ per-word ru/kz labels | ✔ on by default, unbilled | 0.75–1.00 KZT/min/ch, 25 000-credit trial ([plans](https://api-studio.ncspeech.ai/api/billing/plans), [docs](https://studio.ncspeech.ai/llms-full.txt)) | **"8 kHz supported as is"** |
| Alem Plus "STT Kazakh" | n/p | **kk only** — a KSC2 fine-tune of Whisper-large-v3-turbo (`abilmansplus/whisper-turbo-ksc2`), WER 9.16 in-domain KSC2 | n/p | n/p (key on request) ([service](https://doc.alem.ai/services/speechkaz.html), [card](https://huggingface.co/abilmansplus/whisper-turbo-ksc2)) | n/p |
| Azure Speech | ✔ | ✔ `kk-KZ` | n/p | n/p ([table](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=stt)) | n/p |

**ISSAI** has no ASR API we could verify (issai.kz fails TLS here) — models only. **Tilmash is machine translation,
not ASR** ([page](https://issai.nu.edu.kz/tilmash/)).

**OpenRouter** exposes `/api/v1/audio/transcriptions` (OpenAI-compatible multipart; 25 MB cap, 60 s upstream timeout —
[docs](https://openrouter.ai/docs/guides/overview/multimodal/stt)) with `openai/whisper-large-v3(-turbo)`,
`google/chirp-3`, `google/gemini-3.5-transcribe`, `deepgram/nova-3`, `elevenlabs/scribe-v2`, `qwen/qwen3-asr-1.7b`,
`nvidia/nemotron-3.5-transcribe`. Prices from the [models API](https://openrouter.ai/api/v1/models?output_modalities=transcription)
are per audio **second** *(inf — cross-checked: scribe-v2 0.0000611×3600 = $0.22/hr and chirp-3 0.000267×60 = $0.016/min,
both matching the vendor pages)*: turbo ≈$0.0002, qwen3-asr ≈$0.00045, scribe-v2 ≈$0.0037, nova-3 ≈$0.0043,
gemini-3.5-transcribe ≈$0.005, chirp-3 ≈$0.016 per minute.

## 4. Ranked shortlist to benchmark

5 DEV calls ≈ 40 min of audio total → hosted cost is trivial and each open model can run once per call.

| # | Candidate | exact id | how we run it | why |
|---|---|---|---|---|
| 1 | **GigaAM-Multilingual `large_ctc`** | aigw `alemai/ai-sage/GigaAM-Multilingual` (alias `kuspeech:multilingual`) | **aigw `POST /audio/transcriptions`** — already live (0.3–0.8 s per 10 s clip) | best open ru+kk model in the only cross-family table (§1.1), MIT, built for KZ/KY/UZ |
| 2 | **GigaAM-v3** (`rnnt` / `e2e_rnnt`) | `ai-sage/GigaAM-v3` | GPU agent (H200) or ONNX → `H200_ASR_GIGAAM_V3` | best published RU call-centre WER of anything open: 9.5 (Sber internal), OpenSTT phone 17.4 |
| 3 | **T-one** | `t-tech/T-one` | GPU agent, `tone` package offline mode → `H200_ASR_TONE` | RU telephony specialist, 71M/Apache-2.0, 8.63 call-centre, 5.83 named entities |
| 4 | **Whisper large-v3 / turbo** | `openai/whisper-large-v3`, `-turbo` | aigw `whisper-large-v3`, `alemai/openai/*` — zero setup | the known reference; the numbers show exactly where it fails (kk 32–65) |
| 5 | **NVIDIA kk+ru Conformer** | `nvidia/stt_kk_ru_fastconformer_hybrid_large` | GPU agent, NeMo Speech → `H200_ASR_KKRU` | independent (non-Sber) kk evidence: KSC2 spontaneous 15.25, Golos crowd 2.46, CC-BY-4.0, 115M |
| 6 | **Kazakh Whisper fine-tune** | `shyngys879/kazakh-whisper-large-v3-turbo` (alt. `InflexionLab/sybyrla`) | GPU agent, faster-whisper/CT2 → `H200_ASR_KZWHISPER` | best published kk Whisper FT: FLEURS kk 11.80/CER 4.98 |
| 7 | **Hosted arm** | `google/gemini-3.5-transcribe` via OpenRouter (≈$0.20 for all calls, fits the ~$2.6 credit); alt `elevenlabs/scribe-v2` | multipart + `provider.options` diarization | the cheapest hosted pair with ru **and** kk **and** native diarization; **Yandex SpeechKit** is the best regional API if a key is obtainable (8 kHz, ru+kk, 2-speaker labeling, KZ region) |

Diarization to run alongside: `pyannote/speaker-diarization-community-1` (`num_speakers=2`, HF token) and
`nvidia/diar_streaming_sortformer_4spk-v2` (CC-BY-4.0), then one LLM role call per the contract.
Already covered, not to re-benchmark: **FreedomSpeech** (`data/calls/freedomspeech.dev.json`).
Skip for kk: Canary/Parakeet/Nemotron-3.5/Qwen3-ASR (kk unsupported), MMS + SeamlessM4T v2 (CC-BY-NC-4.0 and weak on
spontaneous kk), AssemblyAI universal-3.5-pro (no ru/kk), OpenAI gpt-4o-transcribe family (deprecated, ru/kk coverage
unpublished).

### Caveats
- aigw ASR endpoints return no speaker labels, and `kuspeech:multilingual` echoes the alias with no backing-model
  metadata; on a 10 s DEV clip it produced byte-identical text to `alemai/ai-sage/GigaAM-Multilingual`, so we treat it as a
  second deployment of the same engine — **not officially documented** *(inf)*. Which revision (220M vs 600M) the gateway
  serves is unknown *(inf)*.
- `alemai/openai/whisper-large-v3-turbo` returns no segments/words in `verbose_json` (measured) → timestamps for that
  provider must come from the diarization pass, not from ASR.
- Every published number above comes from a vendor or self-reported community card. Our CER-vs-FreedomSpeech table
  (`data/asr/quality.json`, written by the benchmark) is the only decision-grade signal, and Batyrkhan's manual
  comparison stays final.
