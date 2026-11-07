# Kazakh call: ASR providers compared (2026-11-08)

One 180 s mono 16 kHz call, record `1234`, which **the dataset labels `language: RU` while the speech is Kazakh**. It is the only Kazakh audio we hold: the 5 DEV calls are Russian and the PART2 records are chats with no audio.

There is no reference transcript. The **kk** column is a **proxy, not accuracy**: the share of words carrying a Kazakh-only letter (`ә ғ қ ң ө ұ ү һ і`). It only shows whether the model produced Kazakh script at all. A model can score high on invented words, and a lower score can simply mean the speaker really used Russian ones, which this call mixes in. **Which transcript is right is Batyrkhantzy111's listening review** (`manual_score` in `data/asr/quality.json`); treat every ranking below as provisional until it lands. Audio and raw output stay in `data/audio/` and `data/asr/raw/` (gitignored).

| provider | where | detected | words | **kk** | segments | speakers | s |
|---|---|---|---|---|---|---|---|
| **WhisperX + pyannote** (auto → kk re-run) | H200 | kk | 340 | **0.712** | 22 | yes | 80.2 |
| **WhisperX + pyannote** (`language=kk`) | H200 | kk | 340 | **0.712** | 22 | yes | **22.1** |
| Whisper large-v3 (Alem.Cloud) | cloud | kk | 144 | 0.594 | 22 | no | 12.0 |
| Whisper large-v3 (aigw) | cloud | kk | 152 | 0.575 | 24 | no | 3.1 |
| KuSpeech multilingual | cloud | — | 249 | 0.540 | 17 | no | 1.7 |
| FreedomSpeech | cloud | kk | 352 | 0.533 | 27 | yes | 36.0 |
| Whisper large-v3 turbo (Alem.Cloud) | cloud | — | 136 | 0.526 | 20 | no | 16.3 |
| GigaAM-v3 + pyannote | H200 | ru | 58 | 0.000 | 21 | yes | 3.8 |
| T-one + pyannote | H200 | ru | 129 | 0.000 | 28 | yes | 8.2 |
| Gemini 3.5 Transcribe | OpenRouter | — | 33 | 0.000 | 12 | yes | 13.7 |

## What it says

- **WhisperX produces the most Kazakh script** (0.71) and is the only provider that also labels speakers. FreedomSpeech transcribes the most words (352) at a lower Kazakh share (0.53); whether that is Russian creeping in or genuine code-switching by the speakers is exactly what the manual review has to settle.
- **The automatic re-run works on real audio.** With no hint the hub first answers `language: auto` at kk 0.32; `transcribe()` sees Kazakh letters above the 0.15 threshold and re-runs with `kk`, landing on the same 340 words / 0.712 as the forced provider. The cost is the wasted first pass: 80.2 s against 22.1 s. So prefer `h200-whisperx-kk` when the audio is known to be Kazakh, and leave `h200-whisperx` for unknown audio.
- **GigaAM-v3 and T-one are Russian-only** (0.000): they transliterate Kazakh into Russian words. They stay the right choice for Russian calls, where they led the earlier benchmark (`summary.md`), and the wrong one here.
- **Gemini 3.5 Transcribe returned 33 words for 180 s** — it gave up on Kazakh rather than transcribing it.
- The dataset's language label cannot be trusted: `1234` is tagged RU. The server therefore forces a language only for a `KZ` label and otherwise auto-detects, so the Kazakh check can fire (`server/routes/transcripts.py`).

Reproduce: `data/asr/raw/` holds each provider's raw result as `1234.<provider>.json`.
