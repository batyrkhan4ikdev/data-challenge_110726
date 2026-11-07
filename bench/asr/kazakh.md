# Kazakh call: ASR providers compared (2026-11-08)

One 180 s mono 16 kHz call, record `1234`, which **the dataset labels `language: RU` while the speech is Kazakh**. It is the only Kazakh audio we hold: the 5 DEV calls are Russian and the PART2 records are chats with no audio.

There is no reference transcript. The **kk** column is a **proxy, not accuracy**: the share of words carrying a Kazakh-only letter (`ә ғ қ ң ө ұ ү һ і`). It only shows whether the model produced Kazakh script at all. A model can score high on invented words, and a lower score can simply mean the speaker really used Russian ones, which this call mixes in. **Which transcript is right is Batyrkhantzy111's listening review** (`manual_score` in `data/asr/quality.json`); treat every ranking below as provisional until it lands. Audio and raw output stay in `data/audio/` and `data/asr/raw/` (gitignored).

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

- **No clear Kazakh winner by this proxy.** Once the loop is removed, the Kazakh-script providers sit within 0.53–0.59. The differences are smaller than what the proxy can tell apart.
- **FreedomSpeech and WhisperX are the two candidates with speaker labels.** FreedomSpeech gives the most words (272) and has no loop. WhisperX runs on our GPU, but it looped on this call: without the new loop guard the judge would have read a turn of 109 «өте».
- **Plain Whisper large-v3 (cloud) has the highest share, but about half the words** (138–146 against 232–272) and no speakers: it drops speech rather than mistranscribing it [INFERENCE from the word counts].
- **The automatic kk re-run works on real audio.** With no hint, the hub first answers `language: auto` at kk 0.32. `transcribe()` sees Kazakh letters above the 0.15 threshold and re-runs with `kk`, landing on the same output as the forced provider. The cost is the wasted first pass: 80.2 s against 22.1 s.
- **GigaAM-v3 and T-one are Russian-only** (0.000): they transliterate Kazakh into Russian words. They stay the right choice for Russian calls, where they led the earlier benchmark (`summary.md`), and the wrong one here.
- **Gemini 3.5 Transcribe returned 28 words for 180 s.** It gave up on Kazakh rather than transcribing it.
- **The dataset's language label cannot be trusted:** `1234` is tagged RU. The server therefore forces a language only for a `KZ` label and otherwise auto-detects, so the Kazakh check can fire (`server/routes/transcripts.py`).

Reproduce: `data/asr/raw/` holds each provider's raw result as `1234.<provider>.json`; the collapsed numbers come from running `collapse_repeats` and `kazakh_share` over their `text`.
