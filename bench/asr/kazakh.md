# Kazakh call: ASR providers compared (2026-11-08)

One 180 s mono 16 kHz call, record `1234`, which **the dataset labels `language: RU` while the speech is Kazakh**. It is the only Kazakh audio we hold: the 5 DEV calls are Russian and the PART2 records are chats with no audio.

The listening review is done, 2026-11-08. Batyrkhantzy111 chose **Whisper large-v3 (Alem.Cloud)** as the reference base and corrected it from his notes. `bench/asr/kazakh-1234.reference.json` has 32 turns and 218 words: 22 Alem rows, 11 word fixes, and 10 listener-quoted turns Alem dropped. Roles are bot/operator/client; names and the city are masked. The **kk** letter share remains a secondary column only, a script proxy, not accuracy. Audio and raw output stay in `data/audio/` and `data/asr/raw/` (gitignored).

## CER against the reference

| provider | CER covered | WER covered | CER full | words | loop |
|---|---|---|---|---|---|
| KuSpeech multilingual | 0.167 | 0.358 | 0.265 | 249 | 0 |
| FreedomSpeech | 0.199 | 0.394 | 0.343 | 272 | 0 |
| Whisper large-v3 (Alem.Cloud) | 0.312 | 0.390 | 0.312 | 146 | 0 |
| WhisperX + pyannote (`language=kk`) | 0.313 | 0.569 | 0.454 | 236 | 108 |
| WhisperX + pyannote (auto → kk re-run) | 0.313 | 0.569 | 0.454 | 236 | 108 |
| Whisper large-v3 (aigw) | 0.432 | 0.564 | 0.401 | 153 | 0 |
| Whisper large-v3 turbo (Alem.Cloud) | 0.509 | 0.674 | 0.509 | 136 | 0 |
| T-one + pyannote | 0.638 | 0.904 | 0.642 | 129 | 0 |
| GigaAM-v3 + pyannote | 0.804 | 0.922 | 0.790 | 59 | 0 |
| Gemini 3.5 Transcribe | 0.871 | 0.927 | 0.861 | 33 | 0 |

- **covered** drops a provider's segments that lie mostly inside the reference's `gaps`: 10 spans where other providers hear speech the reference does not contain, including a second request for the operator, the rest of the client's credit question, the name exchange around 01:43–01:49, and short replies. **full** scores everything. Hypotheses pass through `collapse_repeats` first, like every server result, so the WhisperX loop of 108 words is removed.
- The reference is biased toward Alem Whisper plus inserted turns. Two inserted turns were quoted from KuSpeech, the operator greeting and the client's first question; one came from FreedomSpeech, `Операторға қосыңыз`. That favours those three. Alem itself is penalised only for the speech it dropped, 146 words against 218, not for wording, because the listener rated 20 of its 22 rows green.
- KuSpeech at 0.167 and FreedomSpeech at 0.199 are closest on the covered text; FreedomSpeech is the closest with speaker labels. WhisperX matches Alem's error rate on covered text, 0.313 vs 0.312, once the loop is collapsed. Whisper (aigw) and turbo are worse; T-one, GigaAM-v3 and Gemini are not usable on Kazakh, at 0.64–0.87.
- One call, 180 s: treat as a direction, not a ranking with error bars.

**Correction (03:55).** The first version of this table ranked WhisperX first with 340 words and 0.712. 108 of those words were one token, «өте», repeated in a single run: a Whisper decoding loop, not speech. The columns below count words after collapsing any run of 5+ identical words (`collapse_repeats` in `server/asr/providers.py`, now applied to every ASR result), and **loop** is how many words that removed.

| provider | where | words | loop | **kk** (raw → collapsed) | speakers | s |
|---|---|---|---|---|---|---|
| Whisper large-v3 (Alem.Cloud) | cloud | 138 | 0 | 0.594 | no | 12.0 |
| Whisper large-v3 (aigw) | cloud | 146 | 0 | 0.575 | no | 3.1 |
| **WhisperX + pyannote** (`language=kk`) | H200 | 232 | **108** | 0.712 → **0.569** | yes | 22.1 |
| WhisperX + pyannote (auto → kk re-run) | H200 | 232 | **108** | 0.712 → 0.569 | yes | 80.2 |
| KuSpeech multilingual | cloud | 250 | 0 | 0.540 | no | 1.7 |
| **FreedomSpeech** | cloud | **272** | 0 | 0.533 | yes | 36.0 |
| Whisper large-v3 turbo (Alem.Cloud) | cloud | 133 | 0 | 0.526 | no | 16.3 |
| GigaAM-v3 + pyannote | H200 | 55 | 0 | 0.000 | yes | 3.8 |
| T-one + pyannote | H200 | 129 | 0 | 0.000 | yes | 8.2 |
| Gemini 3.5 Transcribe | OpenRouter | 28 | 0 | 0.000 | yes | 13.7 |

## What it says

- **No clear Kazakh winner by this proxy.** Once the loop is removed, the Kazakh-script providers sit within 0.53–0.59. The differences are smaller than what the proxy can tell apart. See [CER against the reference](#cer-against-the-reference) for the measured comparison.
- **FreedomSpeech and WhisperX are the two candidates with speaker labels.** FreedomSpeech gives the most words (272) and has no loop. WhisperX runs on our GPU, but it looped on this call: without the new loop guard the judge would have read a turn of 109 «өте».
- **Plain Whisper large-v3 (cloud) has the highest share, but about half the words** (138–146 against 232–272) and no speakers: it drops speech rather than mistranscribing it [INFERENCE from the word counts].
- **The automatic kk re-run works on real audio.** With no hint, the hub first answers `language: auto` at kk 0.32. `transcribe()` sees Kazakh letters above the 0.15 threshold and re-runs with `kk`, landing on the same output as the forced provider. The cost is the wasted first pass: 80.2 s against 22.1 s.
- **GigaAM-v3 and T-one are Russian-only** (0.000): they transliterate Kazakh into Russian words. They stay the right choice for Russian calls, where they led the earlier benchmark (`summary.md`), and the wrong one here.
- **Gemini 3.5 Transcribe returned 28 words for 180 s.** It gave up on Kazakh rather than transcribing it.
- **The dataset's language label cannot be trusted:** `1234` is tagged RU. The server therefore forces a language only for a `KZ` label and otherwise auto-detects, so the Kazakh check can fire (`server/routes/transcripts.py`).

Reproduce: `data/asr/raw/` holds each provider's raw result as `1234.<provider>.json`; the collapsed numbers come from running `collapse_repeats` and `kazakh_share` over their `text`. CER/WER come from `bench.asr.cer`/`wer` against the turns of the reference after `collapse_repeats`; the numbers were computed on the unmasked local copy (masks would count as errors on the real names), so rerunning on the committed masked file gives slightly different values.
