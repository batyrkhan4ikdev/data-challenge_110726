# Казахские речевые модели: ASR + TTS (срез на 2026-11-08)

Карта казахских speech-моделей и сервисов для судьи колл-центра Freedom Broker (RU/KZ/EN).
Уже покрыто в репозитории и здесь **не** повторяется: [asr-models.md](../asr-models.md) (RU/KZ телефония,
диаризация, hosted-прайс), [asr-hosted.md](../asr-hosted.md) (замеры aigw/OpenRouter),
[freedomspeech.md](../freedomspeech.md) (прогон FreedomSpeech на 5 DEV-звонках).

Правила чтения:

- Каждая цифра ведёт на первоисточник (карточка HF, статья, официальный доки вендора). `n/p` = не опубликовано.
  `(инф)` = наш вывод. **Все WER/CER само-отчётные, кроме** колонок, перемеренных сторонним автором
  (отмечено «перемерено у …»).
- Протоколы несравнимы: нормализация, длина сегмента (≤30 с vs длинный аудио), written-vs-spoken числа,
  greedy vs beam+KenLM, наличие/отсутствие KSC2 в обучении. Одна таблица = один протокол, иначе помечено.
- Модели, которые нам уже доступны, помечены **«доступна нам»**: aigw `alemai/astanahub/alemllm`,
  self-hosted `issai/Qwen3.5-35B-A3B-Kazakh`, aigw `kuspeech:multilingual`, aigw TTS `alemai/k2-fsa/OmniVoice`.
- Типы: `with-scratch` = обучена с нуля; `CPT` = продолженное предобучение; `FT` = полный дообуч;
  `LoRA` = адаптер (в т.ч. слитый); `merge` = слияние.
- Идентификаторы HF проверены через `https://huggingface.co/api/models/<id>`; у `unverified` карточка
  открыта, но метаданные API не получены (401 на момент проверки).

## 0. Что такое KSC2 и почему все цифры «из KSC2»

`issai/Kazakh_Speech_Corpus_2` (ISSAI / Nazarbayev University) — ~1,2 тыс. ч, >600 000 фраз, 6 доменов
(crowdsourced/read, parliament, TV news, radio, podcasts, talkshow), лицензия **CC BY 4.0** на корпусе
([DOI 10.48342/m90y-aj02](https://doi.org/10.48342/m90y-aj02),
[дата-карточка](https://huggingface.co/datasets/issai/Kazakh_Speech_Corpus_2),
[Mussakhojayeva et al., Interspeech 2022](https://www.isca-archive.org/interspeech_2022/mussakhojayeva22_interspeech.html)).
В HF-карточке лицензии датасета стоит `mit` ([репо](https://huggingface.co/datasets/issai/Kazakh_Speech_Corpus_2)),
в карточках моделей KSC2 указывается как CC BY 4.0 — расхождение официальное, для коммерческого
дообучения сверяйтесь с DOI-лицензией. KSC2 изначально **код-свитчинговый** kk↔ru корпус, вплоть до
уровня суффиксов (об этом пишет вендор geko, см. §3) — то есть это наш рабочий регистр, а не «чистый казахский».
Размер «официального теста» уже сами авторы называют по-разному: 9 351 фразы
([ai4kazakh](https://huggingface.co/ai4kazakh/qwen3-asr-1.7b-kazakh)), 9 352
([Sherkhan243](https://huggingface.co/Sherkhan243/Nemotron-3.5-Transcribe-kk-v2)), и «6 733 фразы / 12,97 ч»
у geko под тем же названием «KSC2 official test» (причину расхождения geko не объясняет *(инф: вероятно,
после их фильтрации)*). Плюс стратифицированные
2 019 и подмножества по 600. Поэтому 14.34 и 11.04 ниже — не «кто лучше», а разные протоколы.

Родственный корпус TTS: **KazakhTTS2** — 271,7 ч, 5 дикторов (3 Ж/2 М), 136 196 сегментов, 1,7 М токенов,
22,05 кГц ([LREC 2022, PDF](https://aclanthology.org/2022.lrec-1.578.pdf)); v1 KazakhTTS = 93,2 ч / 2 диктора
([Interspeech 2021](https://www.isca-archive.org/interspeech_2021/mussakhojayeva21_interspeech.pdf)).
Зеркала: [issai/KazakhTTS (датасет)](https://huggingface.co/datasets/issai/KazakhTTS),
[issai/KazakhTTS (модель-репо = tar.gz корпуса, 35,7 ГБ, без весов)](https://huggingface.co/api/models/issai/KazakhTTS),
[ai4kazakh/ISSAI_KazakhTTS2 (parquet по дикторам)](https://huggingface.co/datasets/ai4kazakh/ISSAI_KazakhTTS2).

## 1. ASR: открытые веса (казахский и kk+ru)

| id / продукт | орг | релиз | тип | база | размер | kk-данные | лицензия | опубликованные метрики | веса открыты | источник |
|---|---|---|---|---|---|---|---|---|---|---|
| `alibiserikbay/k5-kazakh-russian-stt` | Alibiserik K. (инди/KZ) | 2026-10 | CPT+FT (CTC) | `ai-sage/GigaAM-Multilingual` `large_ctc` | 600M | 2 364 ч открытых (KSC2 30% replay, KSD, Al-Farabi, OpenSLR 140, FLEURS kk/ru, Golos, SOVA) | **CC BY-SA 4.0** | FLEURS kk **9.14** WER (KenLM beam-1000; 5.85 при ITN чисел; CER в этой таблице не приведён); **kk↔ru mixed KSC2 11.19**; KSC2 read 3.18; KSC2 podcasts 13.56; FLEURS ru 6.06; streaming 2-pass финал 9.03 vs offline 8.84; hotwords имена 24%→80% (перемерено автором на одном нормализаторе) | да | [карточка](https://huggingface.co/alibiserikbay/k5-kazakh-russian-stt) |
| `Sherkhan243/Nemotron-3.5-Transcribe-kk-v2` | Sherkhan (инди/KZ) | 2026-11 | LoRA r=64 (слит) + полный энкодер | `nvidia/NVIDIA-Nemotron-3.5-Transcribe-30B-A4B` | 30B MoE, 4.3B актив., 63 ГБ BF16 | 1 193 ч (KSC2-Structured 1 158 ч + FLEURS kk ×3; 633 736 фраз) | OpenMDW-1.1 | FLEURS kk **8.51 / CER 2.22**; KSC2 test (полный) **14.34 / 4.60**; по доменам: TV 8.6, read 9.0, parliament 11.7, radio 20.9, talk 23.5, podcasts 24.4; DER на синтетических kk-диалогах 11.3 (2 спикера, без collar) | да | [карточка](https://huggingface.co/Sherkhan243/Nemotron-3.5-Transcribe-kk-v2) |
| `baisalovar/Tynda-ASR-kk-ru` | R. Baisalova (Univ. of Waterloo) | 2026-11 | LoRA r=64 (слит) + полный энкодер | та же Nemotron-3.5-Transcribe-30B-A4B | 30B-A4B, 63 ГБ | ~1 470 ч: KSC2 1 154 ч + FLEURS kk ×3 (11.7×3) + **Golos ru 249 ч** | OpenMDW-1.1 | **FLEURS kk 12.23 / CER 4.47**; **FLEURS ru 9.21 / 6.37** (greedy, один нормализатор, казахский промпт с пунктуацией) | да | [карточка](https://huggingface.co/baisalovar/Tynda-ASR-kk-ru) |
| `shyngys879/kazakh-whisper-large-v3-turbo` | Shyngys Sovetkhan (инди/KZ) | 2026-06 | FT (merge, полные веса) | `openai/whisper-large-v3-turbo` | 809M (808 878 080 F16) | «841 000+ пар, ~1 500+ ч»: KSC2, `farabi-lab/kazakh-stt`, OpenSLR 140-hq, KSD, ISSAI_KSC_335RS_v1.1, `sarulab-speech/yodas2_sidon` | Apache-2.0 | **FLEURS kk 11.80 / CER 4.98** (база 19.75, large-v3 31.10, medium 48.69, small 70.45); внутр. 5 000-фраз test 8.73 / 2.10; RTF 0,0646 (T4) | да | [карточка](https://huggingface.co/shyngys879/kazakh-whisper-large-v3-turbo) |
| `ai4kazakh/qwen3-asr-1.7b-kazakh` | ai4kazakh | 2026-11-07 | FT | `Qwen/Qwen3-ASR-1.7B` (базовая kk **не** поддерживает) | 1.7B | ~960k фраз: KSC2 627 824 + Alfarabi 173 610 + NCSpeech YO-CPT-kk 156 903 | **CC BY-NC 4.0** | **KSC2 test 11.04 / CER 3.72** по доменам: crowdsourced 7.40, parliament 8.74, tv_news 6.73, radio 17.37, talkshow 17.59, podcasts 19.47; Alfarabi test 10.86 / 2.42 | да | [карточка](https://huggingface.co/ai4kazakh/qwen3-asr-1.7b-kazakh) |
| `nvidia/stt_kk_ru_fastconformer_hybrid_large` | NVIDIA | 2024-09 (правка 2025-02) | with-scratch (FastConformer, гибрид TDT+CTC) | — | ~115M | CV kk 17, KSC2, KSD; ru: CV 12, Golos, SOVA, Dusha | CC BY-4.0 | **KSC2 read 4.43 / spontaneous 15.25**; CV17 kk 15.48; KSD 7.08; Golos crowd 2.46 / farfield 5.98; MCV12 ru 6.29; SOVA 4.41 / 19.83 | да | [карточка](https://huggingface.co/nvidia/stt_kk_ru_fastconformer_hybrid_large) |
| `InflexionLab/sybyrla` | Inflexion Lab (KZ) | 2025-12 | FT | `openai/whisper-large-v3` | 1.55B | 80% KSC2 (~1 200 ч, пунктуация восстановлена Gemma 27B) + 20% Common Voice 23 **ru** (~250 ч) | Apache-2.0 | **KSC2 test 17.7**; у автора k5 перемерено: FLEURS kk 11.64, kk↔ru mixed 20.98; в статье SIST 2026 — CER 14,8 % на held-out (другая система с LID) | да; CT2 [`shaipro/sybyrla-ct2`](https://huggingface.co/shaipro/sybyrla-ct2) | [карточка](https://huggingface.co/InflexionLab/sybyrla), [DOI 10.1109/SIST61674.2026.11596103](https://doi.org/10.1109/sist61674.2026.11596103) |
| `olzhasAl/whisper-large-v3-tulpar` | Olzhas Alseitov (инди) | 2026-03 (v2) | FT, все 1.55B | `openai/whisper-large-v3` | 1.55B | ~957 ч: ISSAI KSC ~335 + farabi-lab ~554 + FLEURS kk ~12 + YouTube ~57 | Apache-2.0 | **ISSAI KSC test 10.62**; FLEURS kk — `n/p` (TBD в карточке); «может галлюцинировать на чистом русском», код-свитч «частично» | да | [карточка](https://huggingface.co/olzhasAl/whisper-large-v3-tulpar) |
| `abilmansplus/whisper-turbo-ksc2` | Abilmansplus (**Alem Plus / doc.alem.ai**) | 2025-05 | FT | `openai/whisper-large-v3-turbo` | 809M | KSC2 ~1 000 ч | MIT | **KSC2 test 9.16** (in-domain, та же партития, что в обучении) | да | [карточка](https://huggingface.co/abilmansplus/whisper-turbo-ksc2) |
| `InflexionLab/VibeVoice-ASR-Kazakh` | Inflexion Lab | 2026-03 | LoRA (слит) | `microsoft/VibeVoice-ASR` (kk не умела) | карточка размера не указывает | `InflexionLab/ISSAI-KSC2-Structured` ~1 200 ч | Apache-2.0 | KSC2 test ~22 / CER ~9.6; farabi-lab test 17.6 / 4.25; выдаёт пунктуацию и регистр | да | [карточка](https://huggingface.co/InflexionLab/VibeVoice-ASR-Kazakh) |
| `aismlv/wav2vec2-large-xlsr-kazakh` | `adilism`/aismlv | 2022-03 | FT | `facebook/wav2vec2-large-xlsr-53` | wav2vec2-large (~315M — типовой размер базы, в карточке не указан) | Kazakh Speech Corpus v1.1 (335RS) | Apache-2.0 | **KSC v1.1 test WER 19.65**; у shyngys879 перемерено на FLEURS kk: 21.75 / CER 6.24 | да | [карточка](https://huggingface.co/aismlv/wav2vec2-large-xlsr-kazakh) |
| `alibiserikbay/kazakh-russian-mixed-stt` | тот же автор, v1 | 2026-09 | FT (wav2vec2+CTC, TorchScript) | — | 94.4M моно / 188.8M mixed (2 башни) | KSC2, `NCSpeech/YO-CPT-ru`, FLEURS kk/ru | Apache-2.0 | FLEURS kk 12.78 / CER 4.88 (KenLM), greedy 16.88; FLEURS ru 10.47; **mixed rukk kk greedy 16.01**; CPU 24–40×RT; KSC2 read +KenLM 4.27, podcasts 20.68 | да (+KenLM, VAD, пунктуатор в том же репо) | [карточка](https://huggingface.co/alibiserikbay/kazakh-russian-mixed-stt) |
| `tasmulaev/omniasr-ctc-300m-kk` | T. Mulaev (инди) | 2026-06 | FT (полный энкодер+CTC) | `omniASR_CTC_300M_v2` (Meta) | ~300M | KSC2 + FLEURS kk | Apache-2.0 | **KSC2 18.64 / CER 4.84** (база 40.19); регресс: FLEURS ru 33.52, FLEURS en 58.67 | да | [карточка](https://huggingface.co/tasmulaev/omniasr-ctc-300m-kk) |
| `KRASR/kazakh-russian-asr-whisper-large-v3-lora` | KRASR (ВКР) | 2026-05 | LoRA r=32 α=64 (не слит) | `openai/whisper-large-v3` | 1.55B + адаптер | `KRASR/kazakh-russian-asr-dataset` (объём не указан) | «other» | Test-MIXED **30.49 / CER 14.96**; Test-KK 17.30 / 3.92; Test-RU 6.82 / 1.44; FLEURS-KK 20.53 / 7.00; FLEURS-RU 7.08 / 4.13 | да | [карточка](https://huggingface.co/KRASR/kazakh-russian-asr-whisper-large-v3-lora) |
| `askhaYerga/whisper-turbo-ksc2-kk-spontaneous-lora` | A. Yergaliyev, IITU | 2026-10 | LoRA r=16 α=32 (13 МБ) | `abilmansplus/whisper-turbo-ksc2` | 809M + 3.28M обуч. | 7 139 фраз (16,39 ч) **спонтанного** среза KSC2-Train | MIT | канонический WER спонтанной речи **13.48 → 10.78** (−20 %, p<0.001), CER 6.63 → 4.89; пропуск слов-паразитов 23.0 % → 4.6 %; на подготовленной речи −0.23 п.п. (н/з) | да | [карточка](https://huggingface.co/askhaYerga/whisper-turbo-ksc2-kk-spontaneous-lora) |
| `DrishtiSharma/whisper-large-v2-kazakh` | Drishti Sharma | 2022-12 | FT | `openai/whisper-large-v2` | 1.55B | Common Voice 11.0 kk | Apache-2.0 | CV 11.0 test **34.70** | да | [карточка](https://huggingface.co/api/models/DrishtiSharma/whisper-large-v2-kazakh) |
| `BauyrjanQ/wav2vec2-large-mms-1b-kazakh-ksc2-*` (2b/4b/8b/32b) | Bauyrjan Q. | 2023-10…12 | FT | `facebook/wav2vec2-large-mms-1b` | 1B | KSC2 | не указана | n/p (в карточке нет ни метрик, ни текста) | да | [пример](https://huggingface.co/BauyrjanQ/wav2vec2-large-mms-1b-kazakh-ksc2-2b-5ep_2nd) |
| `issai/Persona-ASR` | **ISSAI** | 2026-07 | FT (WavLM-Base-Plus + FiLM + CTC, target-speaker) | `microsoft/wavlm-base-plus` | 118.67M backbone + 198k gate (~1,3 ГБ) | kk + en; смеси KazMix-3 / Libri3Mix | CC BY-4.0 | **Kazakh KazMix3-100h (3 спикера): raw WER 43.49, gated 50.77**, BAcc 86.28, F1 88.78 | да | [карточка](https://huggingface.co/issai/Persona-ASR), [статья](https://doi.org/10.3390/make8080246), [код](https://github.com/IS2AI/Persona_ASR) |
| `Shirali/whisper-small-ISSAI_KSC_335RS_v2` (и `..._335RS`) | Shirali (KZ) | 2023-03 | FT | `openai/whisper-small` | 244M | ISSAI KSC 335RS v1/v2 | не указана | n/p (model-index пуст) | да | [карточка](https://huggingface.co/api/models/Shirali/whisper-small-ISSAI_KSC_335RS_v2) |
| Длинный хвост kk-фин-тюнов без метрик | — | 2023–2026 | FT | whisper-small/medium, wav2vec2 | 244M–1B | KSC/KSD/CV | в осн. Apache-2.0 | n/p: [`raxat/whisper-small-kazakh-finetuned`](https://huggingface.co/raxat/whisper-small-kazakh-finetuned), [`Musa505/kazakh-tts`](https://huggingface.co/Musa505/kazakh-tts) (название TTS, внутри **Whisper-small ASR** на farabi-lab, eval loss 0.0776, WER не приведён), [`nileq/kazakh-omni-asr-ctc`](https://huggingface.co/nileq/kazakh-omni-asr-ctc) (omniASR CTC, 20 000 шагов, метрик нет), [`Uali/whisper-turbo-ksc2-kazakh-finetuned`](https://huggingface.co/api/models/Uali/whisper-turbo-ksc2-kazakh-finetuned) (пустая карточка, 809M) | да | ссылки в колонке |
| `stukenov/sozkz-core-omniaudio-{50,70,150,300,600}m-kk-asr-v1/v2` | stukenov | 2026-03…04 | FT | «OmniAudio» (семейство) | 50–600M | kk | MIT (gated) | n/p (карточка закрыта доступом) | gated | [70m-v1](https://huggingface.co/stukenov/sozkz-core-omniaudio-70m-kk-asr-v1) |
| `nur-dev/asr-220m-kk-ru-en`, `nur-dev/realtime-streaming-asr-kk-ru-en`, `nur-dev/kk-ru-asr-tdt-accuracy` | nur-dev (KZ) | 2026-06…10 | FT / NeMo streaming (FastConformer TDT/RNNT) | `ai-sage/GigaAM-Multilingual`; NeMo | 220M+ | kk, ru, en | CC BY-NC 4.0 / «other», все **gated** | n/p; у `Qwen3-ASR-0.6B-kk-ru-en` цифры приводит сторонняя карточка Sherkhan243: FLEURS kk 17.8, KSC2 20.4 | gated | [220m](https://huggingface.co/nur-dev/asr-220m-kk-ru-en), [streaming](https://huggingface.co/nur-dev/realtime-streaming-asr-kk-ru-en) |
| `TilQazyna/asr-kkru-fastconformer-hybrid-large`, `TilQazyna/asr-kkru-qwen3`, `TilQazyna/kazakh-asr-whisper` | TilQazyna | 2026-05…06 | n/p | NVIDIA kk-ru / Qwen3-ASR / Whisper | n/p | kk+ru | n/p | n/p (пустые карточки-зеркала) | да | [пример](https://huggingface.co/TilQazyna/asr-kkru-fastconformer-hybrid-large) |
| `openai/whisper-large-v3`, `-turbo` — нулевой кадр | OpenAI | 2023-11 | with-scratch (мультияз.) | — | 1.55B / 809M | kk входит в 99 языков | Apache-2.0 / MIT | FLEURS kk 31.10 / large-v3, 19.75 / turbo (по карточке shyngys879); KSC2 zero-shot **81.2** нормализованный ([arXiv 2603.00961](https://arxiv.org/abs/2603.00961)) | да | [карточка](https://huggingface.co/openai/whisper-large-v3-turbo) |
| `facebook/mms-1b-all` (адаптер `kaz`) | Meta | 2023-05 | FT-адаптер SSL | wav2vec2 XLS-R 1B | 1B | FLEURS kk | **CC BY-NC 4.0** | FLEURS kk 63.8 без LM / 19.5 с n-gram LM — значения из табл. статьи 2305.13516, сопоставление столбцов с kk *(инф)* | да | [статья](https://arxiv.org/pdf/2305.13516) |
| `facebook/omniASR-CTC-{300M,1B,3B,7B}`, `omniASR-W2V-*`, `omniASR-LLM-{300M,1B,3B,7B,7B-ZS}` | Meta | 2025-11 | with-scratch SSL (1600+ яз.) | — | 300M–7.8B | `kaz_Cyrl` в покрытии | Apache-2.0 | CTC-1B v2 FLEURS kk **13.34**, kk↔ru mixed KSC2 40.98 — перемерено автором k5; ru 11.99 | да | [репо](https://github.com/facebookresearch/omnilingual-asr), [статья 2511.09690](https://arxiv.org/abs/2511.09690); `facebook/omniASR-CTC-1B-v2` — **unverified** (API 401, v2-зеркала есть у `bezzam/omniasr-llm-7b-v2`) |
| `facebook/seamless-m4t-v2-large` | Meta | 2024 | with-scratch (ASR+MT) | — | 2.3B | 101 язык входа, kk есть | **CC BY-NC 4.0** | FLEURS kk 6.8 / CV kk 23.8 (таблица Sber, см. §1.1 asr-models.md); на **KSD** перемерено в [MDPI Information 2026](https://doi.org/10.3390/info17070690): **WER 9.72** — лучше дообученного Whisper (11.88) | да | [карточка](https://huggingface.co/facebook/seamless-m4t-v2-large) |
| Vosk `vosk-model-kz-0.42` (1.3 ГБ), `vosk-model-small-kz-0.42` (58 МБ) | Alpha Cephei | v0.42 (дата n/p) | Kaldi nnet3+HMM (CPU) | — | 1.3G | KSC, CommonVoice | Apache-2.0 | FLEURS kk 13.09, CV17 12.50, **KSC 4.49**, KSC-Other 18.51 | да | [список моделей](https://alphacephei.com/vosk/models) |

**Количественная сводка по единому протоколу.** Единственная таблица, где kk-модели стоят рядом,
**перемеренные одной рукой**, — в карточке `k5` (один нормализатор, одни и те же 600 фраз FLEURS kk,
greedy для внешних моделей; таблица Sherkhan243 тоже сравнительная, но цифры в ней скопированы с карточек):
K5+KenLM **9.14** < shyngys879 11.58 < sybyrla 11.64 < omniASR CTC-1B v2 13.34 < whisper-large-v3-turbo 20.98;
на смешанной kk↔ru речи (175 фраз KSC2): K5 **11.19** < shyngys879 16.81 < sybyrla 20.98 < omniASR 40.98 < turbo 56.47.
Вендор geko независимо даёт KSC2 official test (6 733 фраз, 12,97 ч): **seta-kk-ru-v2 8.71 / CER 2.63**,
Whisper large-v3 **44.95** на 1 200-фразном подмножестве, и **9.41** на симулированной телефонии
([bench](https://docs.geko.sh/stt/accuracy.md)). ISSAI в статье KSC2 (Interspeech 2022, табл. 2) публиковала
стриминговый трансформер **15.6** общего WER на том же сплите — само число мы читали по пересказу geko
(их [сравнение по доменам](https://docs.geko.sh/stt/accuracy.md)), оригинальный PDF
[mussakhojayeva22](https://www.isca-archive.org/interspeech_2022/mussakhojayeva22_interspeech.html)
на момент правки не открывался (таймаут сети), так что 15.6 помечаем как «пересказано третьей стороной».

## 2. ISSAI: корпусы, рецепты, сервисы (и чего у них нет)

| Артефакт | Что это | Ссылка |
|---|---|---|
| `IS2AI/Kazakh_ASR` | ESPnet-рецепт ASR на KSC + `recognize.py`; весов в репо нет, CC BY 4.0 | [GitHub](https://github.com/IS2AI/Kazakh_ASR) |
| `IS2AI/Kazakh_TTS` | ESPnet-TTS рецепт KazakhTTS/TTS2 **+ 5 готовых Tacotron2-моделей и 5 ParallelWaveGAN-вокодеров** (zip с issai.nu.edu.kz, не на HF) | [GitHub](https://github.com/IS2AI/Kazakh_TTS) |
| Söyle | Дообученный Whisper для 11 тюркских + языки ООН; kk учился на CVC 13.0 + **KSC2**; демо до 60 мин, шумоустойчивость, длинный аудио; CC BY 4.0, DOI 10.48342/hkc6-yq77 | [проект](https://issai.nu.edu.kz/soyle-project/), [код](https://github.com/IS2AI/Soyle), [ICAIIC 2024](https://doi.org/10.1109/ICAIIC60209.2024.10463419) |
| Söyle веса | В README указан `dhcppc0/soyle_onnx` (ONNX, пайплайн `optimum`) — **unverified**: HF API отвечает 401; поиск `soyle` на HF даёт только несвязанное | [README](https://github.com/IS2AI/Soyle) |
| MangiSoz / Soyle App | Коммерческий продукт ISSAI: распознавание + синтез + перевод, kk/ru/en/tr(+zh), запуск ноябрь 2024, inference на сервере «Mangitas 01» (4 GPU, 192 ГБ VRAM, air-gapped поставка) | [новость 2025-03-28](https://issai.nu.edu.kz/2025-03-28/mangitas-01-issais-new-inference-server-for-soyle-foundational-speech-model/), [Mangitas](https://issai.nu.edu.kz/mangitas/), [приложение](https://mangisoz.nu.edu.kz/) |
| TilSync | Субтитр-сервис ISSAI (kk/ru/en); веса в HF только как CT2-зеркало `stukenov/issai-faster-whisper-tilsync-beta-30sept2025-fp16` (gated, MIT, метрик нет) | [tilsync.nu.edu.kz](https://tilsync.nu.edu.kz/), [HF](https://huggingface.co/stukenov/issai-faster-whisper-tilsync-beta-30sept2025-fp16) |
| `issai/Persona-ASR` | Единственная ASR-модель ISSAI на HF (target-speaker kk+en, см. §1) | [карточка](https://huggingface.co/issai/Persona-ASR) |
| `issai/KazGenericTTS` | Единственная TTS-модель ISSAI на HF (gated, см. §4) | [карточка](https://huggingface.co/issai/KazGenericTTS) |
| `issai/tilmash` | **машинный перевод**, не ASR/TTS (pipeline kk↔en/ru/tr) | [карточка](https://huggingface.co/issai/tilmash), [проект](https://issai.nu.edu.kz/tilmash/) |
| Multilingual (kk/ru/en) ASR | Первый joint-E2E kk+ru+en: 318 ч kk (KSC) + 327 ч ru + 330 ч en, датасет `issai/Multilingual_Speech_Dataset`, DOI 10.48342/0qzd-fk83 | [проект](https://issai.nu.edu.kz/multilingual-asr/), [SPECOM 2021 / arXiv 2108.01280](https://arxiv.org/abs/2108.01280) |
| `Dauren-Nur/ISSAI_TURKIC_ASR` | Мультиязычный kk/en/ru/tr/ky/uz/ug/tt/az/ba на ISSAI_KSC_335RS_v1.1; карточка без единой метрики | [карточка](https://huggingface.co/Dauren-Nur/ISSAI_TURKIC_ASR), [новость про 10 тюркских](https://issai.nu.edu.kz/2023-01-30/issai-researchers-develop-automatic-speech-recognition-for-ten-turkic-languages-by-leveraging-their-advances-in-kazakh/) |

Итог по ISSAI: у института **нет открытой сильной ASR-модели на HF**; их вклад в kk speech —
корпусы (KSC, KSC2, KazakhTTS/TTS2, KazEmoTTS, KazParaD), ESPnet-рецепты, Söyle/MangiSoz как продукт
и базовые числа KSC2 (их стриминговый трансформер 15.6 общего WER, таблица по доменам — в оригинале
нами не прочитан, см. оговорку в §1), на которых сегодня оценивается всё сообщество.
`issai/Qwen3.5-35B-A3B-Kazakh` (**доступна нам**) — текст, не аудио.

## 3. Код-свитчинг RU↔KZ (наш основной регистр)

| Модель / работа | Как именно решает | Опубликованное число на смешанной речи | Источник |
|---|---|---|---|
| `alibiserikbay/k5-kazakh-russian-stt` | единый 600M CTC-вокабуляр kk+ru, телефонная аугментация и **kk↔ru смеси** в обучении; 2-pass стриминг, KenLM, ITN, hotwords | **kk↔ru KSC2 11.19** (KenLM) vs 12.88 greedy; v1mixed автор же: 18.88 | [карточка](https://huggingface.co/alibiserikbay/k5-kazakh-russian-stt) |
| `alibiserikbay/kazakh-russian-mixed-stt` | отдельная модель с **двумя энкодерными башнями** (`asr/rukk`, 188.8M), один проход без LID | kk greedy 16.01; ru greedy 13.84 (−1.5 п.п. к моно-ru модели — цена покрытия) | [карточка](https://huggingface.co/alibiserikbay/kazakh-russian-mixed-stt) |
| `baisalovar/Tynda-ASR-kk-ru` | kk (KSC2/FLEURS) + ru (Golos) в одном LoRA-фине-тюне; промпты по языкам | **FLEURS kk 12.23 + FLEURS ru 9.21** из одной модели; автор прямо пишет: «intra-utterance code-switching не обучался» | [карточка, Limitations](https://huggingface.co/baisalovar/Tynda-ASR-kk-ru) |
| `ai-sage/GigaAM-Multilingual` `large_ctc` (**доступна нам** через `kuspeech:multilingual`) | общий kk/ru/ky/uz/en конформер | kk CV 13.8 / FLEURS 4.4 / internal 15.8; ru 5.1 / 3.0 / 6.0 (протокол Sber ≤30 с, greedy) | [карточка](https://huggingface.co/ai-sage/GigaAM-Multilingual), [arXiv 2607.10371](https://arxiv.org/abs/2607.10371) |
| geko `seta-kk-ru-v2` | fine-tune GigaAM-ML large_ctc: 56 % разговорной речи, 23 % русского, единый 70-символьный вокабуляр; **позиционирует KSC2 как код-свитч-корпус** и считает долю kk-токенов с `ә ғ қ ң ө ұ ү һ і` | KSC2 8.71 (телефонная симуляция 9.41), FLEURS ru 7.65; асимметрия детекции: кириллица ru ⊂ kk, поэтому «ru» доказывается только орфографически | [accuracy](https://docs.geko.sh/stt/accuracy.md) |
| **Sybyrla (Inflexion Lab)** — система | Whisper-large-v3 FT + **внешний LID на недообученном Whisper**, форсированный язык на сегмент, sub-window LID для intra-segment переключений; один деплой-сервер на базе WhisperX | CER **14.8 %** на held-out по kk/ru/en смеси; IEEE SIST 2026 | [DOI](https://doi.org/10.1109/sist61674.2026.11596103), [DSML-страница](https://dsml.kz/research/works/dias-ilyas-2-sybyrla-end-to-end-low-resource-kazakh-speech-recognitio) |
| `InflexionLab/sybyrla` — веса | 80 % KSC2 + 20 % Common Voice **ru**, чтобы не деградировать на русских вставках и заимствованиях | у k5: mixed KSC2 20.98 | [карточка](https://huggingface.co/InflexionLab/sybyrla) |
| `KRASR/*-kazakh-russian-asr-*` | учебная сравнительная линейка (Whisper-small FT/LoRA, large-v3 LoRA, XLS-R 1B CTC) на датасете `KRASR/kazakh-russian-asr-dataset` | Test-MIXED WER 30.49 / CER 14.96 (large-v3 LoRA) — единственный публичный «mixed-only» скор у Whisper-линейки | [карточка](https://huggingface.co/KRASR/kazakh-russian-asr-whisper-large-v3-lora) |
| Yandex SpeechKit v3 | `language-auto` переключает язык **на уровне предложений** (не внутри) | n/p WER | [модели](https://yandex.cloud/ru-kz/docs/speechkit/stt/models) |
| Soniox | переключение языков внутри потока, kk+ru | n/p | [языки](https://docs.soniox.com/stt/concepts/supported-languages) |
| Deepgram nova-3 | `kk` доступен **только как monolingual**, в `multi`-списке его нет ⇒ kk+ru в одном вызове не покрыт | n/p | [модели](https://developers.deepgram.com/docs/models-languages-overview.md) |
| `askhaYerga/...-spontaneous-lora` | обучен именно на спонтанной kk-речи, где русские служебные слова и морфо-слияния — часть фильтра «спонтанности» | канон. WER 10.78 на спонтанной; на подготовленной −0.23 п.п. (н/з) | [карточка](https://huggingface.co/askhaYerga/whisper-turbo-ksc2-kk-spontaneous-lora) |

Что **не** решает код-свитчинг: NVIDIA FastConformer kk+ru и GigaAM-ML дают оба языка в одном словаре,
но ни та, ни другая не публикует скор на *интра-сегментной* смеси; Vanilla Whisper (любого размера) на kk
теряется уже на §1 (zero-shot KSC2 81.2 %), и дообучение на kk только смещает язык детекции
(`tulpar`: «галлюцинирует на чистом русском»).

## 4. TTS: открытые веса

| id / продукт | орг | релиз | тип | база | размер | kk-данные | лицензия | метрики | веса открыты | источник |
|---|---|---|---|---|---|---|---|---|---|---|
| ISSAI Tacotron2 ×5 дикторов (F1/F2/F3/M1/M2) + ParallelWaveGAN | **ISSAI** | 2022 (LREC) | with-scratch на корпусе | ESPnet-TTS (LJ-рецепт) | Tacotron2 + PWGAN | KazakhTTS2 271,7 ч (каждая модель — один диктор) | CC BY 4.0 | **MOS: F1 4.535, F2 4.061, F3 4.049, M1 Book 4.057, M1 Wiki 3.673, M2 4.200** (ground truth 4.17–4.73; 25 фраз на диктор, ≥24 оценок, Telegram-краудсорсинг) | да (zip на сайте ISSAI) | [статья, табл. 4](https://aclanthology.org/2022.lrec-1.578.pdf), [рецепт+ссылки на веса](https://github.com/IS2AI/Kazakh_TTS) |
| KazakhTTS v1 (Tacotron2) | ISSAI | 2021 (Interspeech) | with-scratch | ESPnet-TTS | — | 93,2 ч, 2 диктора | CC BY 4.0 | «MOS above 4.0» (пересказано в LREC-2022) | да | [статья](https://www.isca-archive.org/interspeech_2021/mussakhojayeva21_interspeech.pdf) |
| KazEmoTTS (эмоц. базовая модель) | ISSAI | 2024 (LREC) | with-scratch baseline | — | — | 74,85 ч, из них 34,23 ч одной женщины, 6 эмоций | не указана в HF-карточке | **MOS 3.51–3.57, MCD 6.02–7.67** | да (zip `EmoKaz.zip`) | [статья](https://aclanthology.org/2024.lrec-main.841.pdf), [датасет](https://huggingface.co/datasets/issai/KazEmoTTS) |
| `stukenov/kazakh-tts-omnivoice-experiment-a` | stukenov | 2026-09 | FT (полный) | `shyngys879/KazakhTTS-OmniVoice` ← `k2-fsa/OmniVoice` | 612,6M (база) | 522 512 реальных фраз (KazakhTTS2 + KSC2 + FLEURS + CV) + 18 000 синт. | Apache-2.0 | **WER 7.48 %** (у базы-референса 15.2), **CER 4.48** (5.87), scorer = `til-asr`; **UTMOS 3.08** vs 3.18 у базы | да | [карточка](https://huggingface.co/stukenov/kazakh-tts-omnivoice-experiment-a) |
| `shyngys879/KazakhTTS-OmniVoice` | Shyngys Sovetkhan | 2026-07 | FT | `k2-fsa/OmniVoice` (612,6M, база `Qwen/Qwen3-0.6B`, релиз 2026-03) | 612.6M | 56 % KazakhTTS2 + 44 % синт. voice-design (10 800 фраз, 18 категорий: пол/возраст/тон) | **в карточке не указана** | n/p (ни WER, ни MOS; только аудиопримеры) | да | [карточка](https://huggingface.co/shyngys879/KazakhTTS-OmniVoice) |
| `TilLabs/kokoro-tts-kazakh` (`km_m1`) | N. Mambetaly / A. Sultanbekov / A. Balakhazy | 2026-07 | FT (StyleTTS2 stage 1+2, `kikiri-tts`) | `hexgrad/Kokoro-82M` | 82M | **102,8 ч / 48 154 клипа** одного мужского диктора из KazakhTTS2 (всего корпус 269,9 ч, 5 дикторов) | Apache-2.0 | **WER 16,4 %** на 20 held-out фразах (scorer — kk-Whisper + jiwer) как отбор чекпойнта; CPU RTF 0,39 (пик 2,6×RT на 6 ядрах), 24 кГц, 1,4 ГБ RAM | да | [карточка](https://huggingface.co/TilLabs/kokoro-tts-kazakh) |
| `issai/KazGenericTTS` | **ISSAI** | 2026-09 | **LoRA-адаптер** | `k2-fsa/OmniVoice` | n/p (gated) | `issai/KazParaD` — kk paralinguistic: пол/возраст/тон/эмоция + 18 категорий невербальных вокализаций | CC BY-NC 4.0 | n/p (gated-карточка без метрик) | gated (ручной доступ) | [карточка](https://huggingface.co/issai/KazGenericTTS), [KazParaD](https://huggingface.co/datasets/issai/KazParaD) |
| `Anadilorg/Anadil_Kazakh_TTS` | Anadil.org (TR) | 2026-10 | LoRA r=32 α=32 (LM + DiT), адаптер ~72 МБ / 18,1M параметров | `openbmb/VoxCPM2` | 48 кГц выход | **1 884 сегмента** Common Voice 26.0 kk, один диктор | MIT | n/p (автор прямо пишет: автоматические метрики не считали, примеры — из обучающих фраз) | да | [карточка](https://huggingface.co/Anadilorg/Anadil_Kazakh_TTS) |
| `ErnarBahat/VoxCPM-KazakhTTS-Lora` | ErnarBahat / allssai | 2026-02 | LoRA r=32 α=16 | `openbmb/VoxCPM1.5` | n/p | **66,1 ч** `issai/KazakhTTS`, 4 160 шагов | Apache-2.0 | только обучающие лоссы (`loss/diff` 0.644, `loss/stop` 0.004); MOS n/p | да | [карточка](https://huggingface.co/ErnarBahat/VoxCPM-KazakhTTS-Lora) |
| `ErnarBahat/Spark-TTS-Kazakh` | allssai | 2026-01 | FT | `SparkAudio/Spark-TTS-0.5B` | 0.5B, 16 кГц | `issai/KazakhTTS` | CC BY-NC-SA 4.0 | n/p; заявлены клонирование по 3–10 с и кириллица + арабская («Тоте Жазу») графика | да | [карточка](https://huggingface.co/ErnarBahat/Spark-TTS-Kazakh), [сервер FastAPI+UI](https://github.com/allssai/Spark-TTS-Kazakh) |
| `futureDoctor/qwen3-tts-kazakh-emotional` | futureDoctor | 2026-03 | FT | `Qwen/Qwen3-TTS-12Hz-1.7B-Base` | 1.7B | KazEmoTTS, 34 ч (жен.), 6 эмоций | CC BY 4.0 (фронтматтер карточки битый — лицензия только в теле README) | n/p | да | [карточка](https://huggingface.co/futureDoctor/qwen3-tts-kazakh-emotional) |
| `facebook/mms-tts-kaz` | Meta | 2023-09 | with-scratch (VITS) | — | **36,3M** | корпус MMS (объём именно на kk в карточке не указан) | CC BY-NC 4.0 | n/p (карточка — только фронтматтер, ни метрик, ни объёма данных) | да | [карточка](https://huggingface.co/api/models/facebook/mms-tts-kaz) |
| piper `kk_KZ-issai-high`, `kk_KZ-iseke-x_low`, `kk_KZ-raya-x_low` | RHVoice → упаковка `speaches-ai` / `csukuangfj` (sherpa-onnx) | 2023-11 / 2025-03 | FT (VITS/piper) | Piper | **127.9 МБ ONNX** (`kk_KZ-issai-high.onnx`, замерено по дереву репо) | голоса RHVoice kk (имена `issai`, `iseke`, `raya`) | свободная (PHI/CC — проверить по репо) | n/p | да | [speaches](https://huggingface.co/speaches-ai/piper-kk_KZ-issai-high), [csukuangfj](https://huggingface.co/csukuangfj/vits-piper-kk_KZ-issai-high) |
| `zizzimars/speecht5_finetuned_kazakh_tts2`, `..._tts2_1` | zizzimars | 2024-04 | FT | `microsoft/speecht5_tts` | 144M | KazakhTTS2 | MIT | n/p (model-index пуст) | да | [карточка](https://huggingface.co/api/models/zizzimars/speecht5_finetuned_kazakh_tts2) |
| XTTS / Coqui / F5 / StyleTTS2 на kk | — | — | — | — | — | — | — | **не найдено ни одного HF-репозитория** (поиск `kazakh xtts`, `f5 tts kazakh` → пусто); StyleTTS2-семейство представлено только kokoro-FT выше | — | [поиск XTTS](https://huggingface.co/api/models?search=kazakh%20xtts), [поиск F5](https://huggingface.co/api/models?search=f5%20tts%20kazakh) |

## 5. TTS: сервисы (hosted)

| Провайдер | kk-голоса | Что публикуется | Цена/доступ | Источник |
|---|---|---|---|---|
| **FreedomSpeech** (уже интегрирован) | `tomiris` (kk+ru, 6 эмоций + инлайн `<laugh> <sigh> <pause> <louder> <slower>`), `taymas` (kk) и **37 каталожных** голосов (всего в `GET /api/voices` — 39; 16 с суффиксом `_kz`, у большинства есть пара `_ru`: `call_center_alua_kz`, `anara_call_center_kz`, `azamat_kz`, `audiobook`, `lecture`, `tales`…) | OpenAI-совместимый `POST /v1/audio/speech`, WAV 16-bit mono **24 кГц**, WS `/ws/tts` (очередь 8, 60 с), voice clone + voice design, движки `freedomspeech` / `freedomspeech-flash` и `omnivoice`/`flash` в `?variants=all` | публичного прайса нет; демо-ключ веб-фронта | [docs](https://freedomspeech.kz/docs/), [голоса (живой JSON)](https://freedomspeech.kz/api/voices) |
| **Yandex SpeechKit** (регион KZ, только v3) | `amira` (Ж), `madi` (М) — v1+v3; `saule` (Ж, роли neutral/strict), `zhanar` (Ж, neutral/friendly) — v3; русские варианты `madi_ru`, `saule_ru`, `zhanar_ru` | реальные дикторы, амплуа, Realtime API для голосовых агентов | KZ-прайс со скидкой; в `asr-models.md` разобран STT-прайс | [список голосов](https://yandex.cloud/ru-kz/docs/speechkit/tts/voices) |
| **Cybernet AI (ADM)** | «natural voices in Kazakh and Uzbek, with Russian and English», голоса на лицензированных данных, REST, WAV | ASR+TTS под одним ключом, биллинг по 10 с; заявляет RTF < 0.3 и код-свитч в ASR | доступ по заявке | [ml.cyber-net.ai](https://ml.cyber-net.ai/en), [статья про тюркскую ASR 2026-01](https://astanatimes.com/2026/01/kazakhstan-develops-central-asias-largest-ai-model-for-turkic-speech-recognition/) |
| **geko** | `tokay-kk-v1`, 6 именованных kk-голосов (Aigerim — default, Arman, Ainur, Aruzhan, Sanzhar, Yerlan), пол/стиль/сценарий в каталоге | WAV 24 кГц 16-bit, поток по предложениям, нормализация чисел/дат/валют в казахскую устную форму, OpenAI-алиас | $0.04/1k символов, $1 стартовый баланс | [TTS](https://docs.geko.sh/tts/index.md), [голоса](https://docs.geko.sh/tts/voices.md) |
| **NCSpeech Studio** (Astana Hub, KZ) | синтез kk+ru, клонирование голоса; с 2026-10 — «смешанная kk/ru речь» в одну модель (записи партнёрства с inDrive) | метрики — собственные спецификации, сторонних бенчмарков нет | 0.75–1.00 KZT/мин/канал (STT) | [astanahub 2026-10-13](https://raem.kz/en/ncspeech-kazakh-russian-speech-models-october-2026-en), [studio](https://studio.ncspeech.ai/llms-full.txt) |
| **ElevenLabs** | Kazakh в списке языков мультиязычной модели (страница kk TTS), 90+ языков | MOS/WER на kk не публикуются | $/символы | [страница kk TTS](https://elevenlabs.io/text-to-speech/kazakh) |
| **Soniox** | «каждая речь говорит по-казахски», language mixing kk+EN в одном предложении, cloning, char-таймстампы, WS/REST | n/p | **$0.70 / час** сгенерированного аудио | [kk TTS](https://soniox.com/text-to-speech/kazakh) |
| **Azure Speech** | `kk-KZ-AigulNeural` (Ж), `kk-KZ-DauletNeural` (М); имена двух голосов взяты из зеркала каталога ([json2video](https://json2video.com/ai-voices/azure/languages/kazakh/), [speakshelf](https://speakshelf.com/azure/voices/kk-KZ) — там же kk-KZ-Neural/DragonHD/Multilingual семейства), официальная страница рендерится JS | SSML, MOS не публикуется | $/1M символов | [языки MS](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=tts) |
| **Google Cloud TTS** | **казахского нет**: ни в `Chirp 3: HD` (52 кода, kk отсутствует), ни в списке голосов (`grep -i kazakh` по скачанной странице = 0 совпадений). Для сравнения: в **STT** v2 `chirp_3` код `kk-KZ` есть, но в Preview ([asr-models.md §3](../asr-models.md)) | — | — | [chirp3-hd](https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd), [voices](https://docs.cloud.google.com/text-to-speech/docs/list-voices-and-types) |
| `alemai/k2-fsa/OmniVoice` (**доступна нам**) | базовая OmniVoice (`k2-fsa/OmniVoice`, 612,6M, 646 языков в cardData, `kk` среди них; **лицензия в cardData не указана**) — не казахский фин-тюн | `POST {AIGW}/audio/speech` **только JSON-телом** → 200 WAV; ~0,35 с на короткую фразу | внутренний aigw | [aigw-замер](../asr-hosted.md), [OmniVoice](https://huggingface.co/k2-fsa/OmniVoice) |

## 6. Пробелы и риски (чтобы не выдать ложную точность)

1. **Ни одна модель не публикует WER на реальных 8-кГц звонках на казахском.** Телефония везде симулирована
   (band-pass → 8 кГц → μ-law): geko даёт +8.0 % относительного роста WER, k5 — отдельную строку «simulated»,
   у FreedomSpeech поддержка 8 кГц в HTTP вообще не документирована, а WS требует 16 кГц PCM
   (замерено нами, [asr-models.md §3](../asr-models.md)). Наш `data/asr/quality.json` остаётся единственным
   decision-grade сигналом.
2. **Спонтанная речь — провал всех kk-моделей**: лучший опубликованный доменный разброс 9 % (read/TV) vs
   20–24 % (talkshow/podcasts) у Nemotron-kk, 17–20 % у Qwen3-ASR-kk, 15.25 (spontaneous) vs 4.43 (read)
   у NVIDIA. Диалог оператора — это правый край.
3. **Лицензионный пол**: CC BY-**NC** — `ai4kazakh/qwen3-asr-1.7b-kazakh`, `facebook/mms-1b-all`,
   `facebook/mms-tts-kaz`, `facebook/seamless-m4t-v2-large`, `issai/KazGenericTTS`, `nur-dev/*`.
   CC BY-SA (share-alike на производные) — `k5-kazakh-russian-stt` и обучающий Golos. Свободно для продукта:
   Apache/MIT/OpenMDW — `shyngys879/*`, `InflexionLab/*`, `TilLabs/kokoro-tts-kazakh`,
   `stukenov/kazakh-tts-omnivoice-experiment-a`, `nvidia/stt_kk_ru_fastconformer_hybrid_large`, Tynda/Nemotron-kk.
4. **Числа TTS почти отсутствуют.** Кроме ISSAI (2021/2022/2024) ни один kk-TTS не опубликовал
   **человеческий** MOS; у новых моделей только автоматические суррогаты: «обходной» WER
   (синтез → распознавание → сравнение с исходным текстом: kokoro 16.4 %, stukenov 7.48 %) и UTMOS 3.08
   у `stukenov/kazakh-tts-omnivoice-experiment-a`. Сравнивать эти WER между карточками нельзя —
   разные ASR-scorer'ы (kk-Whisper+`jiwer` против неуказанного `til-asr`) и разные тексты; обходной WER
   к тому же смешивает качество синтеза с качеством распознавателя.
5. **Нет казахского Open ASR Leaderboard** трека (de/fr/it/es/pt) — [пространство](https://huggingface.co/spaces/hf-audio/open_asr_leaderboard),
   поэтому «общепринятого» ранкинга kk-ASR не существует; всё сводится к KSC2/FLEURS на карточках.
6. **`kuspeech:multilingual`** — алиас в нашем aigw с `owned_by: KUSpeech`; побайтово совпадает с
   `alemai/ai-sage/GigaAM-Multilingual`, то есть это, (инф), то же самое развертывание GigaAM-ML. Публичного
   сайта/документации KUSpeech найти не удалось (`kuspeech.kz`, `.com`, `.ai` не резолвятся; web-поиск по
   «KUSpeech» даёт только несвязанные домены), так что **производитель официально не подтверждён** —
   не считайте это независимым движком.
7. **Söyle ONNX-веса (`dhcppc0/soyle_onnx`) — unverified**: ссылка из README ISSAI, HF API вернул 401
   (нет репозитория или приватный). Числов kk у Söyle в открытом доступе нет, кроме диаграмм в статье.

## 7. Рекомендация

### 7.1 Лучший казахский ASR на self-host одного H200

**Один прогон, один H200 (141 ГБ), RU+KZ колл-центр:**

1. **`baisalovar/Tynda-ASR-kk-ru`** — единственный открытый чекпойнт, у которого **обе** цифры на одном
   протоколе: kk 12.23 / ru 9.21 FLEURS, плюс из базовой Nemotron ветки **пословные тайм-штампы (CTC head)
   и диаризация (Sortformer)** в той же модели, пунктуация и регистр. 63 ГБ BF16 → комфортно в 141 ГБ.
   Развертывание (дословно из [карточки](https://huggingface.co/baisalovar/Tynda-ASR-kk-ru)):
   ```bash
   export VLLM_PLUGINS=nemo_speechlm VLLM_USE_V2_MODEL_RUNNER=0
   vllm serve baisalovar/Tynda-ASR-kk-ru --served-model-name tynda --trust-remote-code --dtype bfloat16 \
     --max-model-len 65536 --enable-chunked-prefill --no-enable-prefix-caching \
     --mamba-cache-mode none --mm-processor-cache-gb 0 --no-async-scheduling \
     --reasoning-parser nemotron_v3 --trust-request-mm-kwargs \
     --middleware nemo.collections.speechlm2.vllm.salm.ctc_serving.ctc_timestamp_middleware
   ```
   Промпт для kk **обязательно с пунктуацией** (совпадает с 95 % обучающих данных):
   `Audio transcription. Language: Kazakh. Wording: verbatim. Formatting: punctuation and capitalization. Output: transcript only.`
   Ограничения: max_tokens ≈ 30×длительность+32; числа пишет словами; intra-utterance код-свитч не обучался.
2. **Если нужен только kk и максимум in-domain** — `Sherkhan243/Nemotron-3.5-Transcribe-kk-v2`
   (KSC2 14.34, FLEURS kk 8.51, тот же командный стек vLLM + `nemo_speechlm`; карточка предупреждает:
   `<spk:k>`-метки в тексте работают плохо, говорящего назначать по тайм-штампам диаризации).
3. **Дешёвый/быстрый arm и запасной путь** — `shyngys879/kazakh-whisper-large-v3-turbo`
   (Apache-2.0, 809M ≈ 1.6 ГБ fp16; transformers / faster-whisper / CT2 `d1nagul00/kazakh-whisper-turbo-ct2`
   / GGUF Q8_0 `Figmapng/bulbul-kazakh-whisper-large-v3-turbo-gguf`), плюс **уже живой** aigw
   `kuspeech:multilingual` = `ai-sage/GigaAM-Multilingual` `large_ctc` (MIT, FLEURS kk 4.4 по протоколу Sber,
   но строчный, без пунктуации, ≤30 с на сегмент).
4. **Стриминг/край CPU** — `alibiserikbay/k5-kazakh-russian-stt`: 600M, двухпроходный
   `deploy/transcribe_stream.py`, KenLM, ITN чисел, hotwords (имена 24 %→80 %), 16 real-time стримов на H100
   при 640 мс чанках; лицензия CC BY-SA 4.0 ⇒ веса-производные надо распространять на тех же условиях.
5. **Надстройка для verbatim-транскрипта звонков** — адаптер `askhaYerga/whisper-turbo-ksc2-kk-spontaneous-lora`
   (13 МБ, MIT, к `abilmansplus/whisper-turbo-ksc2`): перестаёт выбрасывать слова-паразиты (23 %→4.6 %),
   −2.7 п.п. канонического WER на спонтанной речи; для сущностей и интентов он бесполезен (F1 0.725 vs 0.705, н/з).

Не брать для kk: `nvidia/canary-*`, `parakeet-*`, базовые `Qwen3-ASR`, `ibm-granite/*-speech`, `Voxtral`,
`cohere-transcribe`, `microsoft/VibeVoice-ASR` (без kk-фин-тюна), MMS 1B и SeamlessM4T v2 (NC-лицензия +
слабы на спонтанном kk).

### 7.2 Лучший казахский TTS для демо на сайте

- **Дефолт, ноль инфраструктуры:** уже подключённый **FreedomSpeech** `POST https://api.freedomspeech.kz/v1/audio/speech`
  с `{"voice":"tomiris","language":"kk","emotion":"neutral"}` → WAV 24 кГц; у него есть отдельные
  call-centre kk-голоса (`anara_call_center_kz`, `arman_call_center_kz`, `assel_call_center_kz`,
  `call_center_alua_kz`/`alua`) и просодические теги — для «Озвучить» в продукте это самый короткий путь.
  Наш второй живой путь — aigw `alemai/k2-fsa/OmniVoice` (**доступна нам**, JSON-тело обязательно).
- **Self-host, лучшее опубликованное качество на открытых весах:** `stukenov/kazakh-tts-omnivoice-experiment-a`
  (Apache-2.0, 612M, WER-обход 7.48 % / CER 4.48 %, UTMOS 3.08) → тот же вес, что у FreedomSpeech-движка
  `omnivoice`, 2–3 ГБ VRAM в bf16, живёт на том же H200 рядом с ASR:
  ```python
  from omnivoice import OmniVoice
  m = OmniVoice.from_pretrained("stukenov/kazakh-tts-omnivoice-experiment-a",
                                device_map="cuda:0", dtype=torch.float16)
  audio = m.generate(text="Сәлеметсіз бе! Сіздің өтінішіңіз қабылданды.", language="Kazakh")
  ```
  (24 кГц, `pip install omnivoice soundfile torch`.) Если нужны управляемые пол/возраст/тон — берите
  `shyngys879/KazakhTTS-OmniVoice` (18 voice-design категорий, но лицензия в cardData отсутствует ⇒ для
  продакшена запросить у автора).
- **Без GPU вообще (статичный HTML-демо, много параллельных):** `TilLabs/kokoro-tts-kazakh` —
  82M, Apache-2.0, RTF 0.39 на 6 CPU-ядрах, пик ~3×реального времени на 6–8 однопоточных воркерах;
  установка `pip install torch kokoro "misaki[kk]"`. Минус: один мужской диктор `km_m1`, WER 16,4 % на
  held-out — слышно акцент-артефакты; для «женского оператора» лучше piper `kk_KZ-iseke-x_low`
  (несколько МБ ONNX, `sherpa-onnx`/`piper`) или сервисный голос.
- **Клонирование голоса брокера:** FreedomSpeech `/api/voice-clone` (референс ≤20 с) или zero-shot
  OmniVoice (`ref_audio` + `ref_text`), а для RU+KZ одной персоной — каталожные пары `_kz`/`_ru`.

## Вывод — самое значимое в срезе

1. **`baisalovar/Tynda-ASR-kk-ru`** и **`Sherkhan243/Nemotron-3.5-Transcribe-kk-v2`** (2026-11, обе на
   Nemotron-3.5-Transcribe-30B-A4B, OpenMDW-1.1): первый публичный kk-ASR, дающий сразу пунктуированный текст,
   пословные тайм-штампы и диаризацию на одной H200; Tynda единственная честно покрывает kk **и** ru числами
   (12.23 / 9.21) — это ровно наш микс.
2. **`alibiserikbay/k5-kazakh-russian-stt`** — лучший открытый результат на *смешанной* kk↔ru речи
   (KSC2 mixed 11.19) плюс стриминг 2-pass, KenLM, ITN и hotwords из коробки; цена — CC BY-SA 4.0 и
   строчный вывод без пунктуации.
3. **`shyngys879/kazakh-whisper-large-v3-turbo`** — де-факто стандарт kk Whisper (5.2k загрузок, Apache-2.0,
   FLEURS kk 11.80 / CER 4.98, RTF 0.065) с готовыми CT2/GGUF-артефактами; самый дешёвый способ закрыть kk
   в существующем faster-whisper-конвейере.
4. **`ai-sage/GigaAM-Multilingual` `large_ctc` = наш `kuspeech:multilingual`** — это хребет обеих лучших
   community-моделей kk (k5 9.14 FLEURS kk, geko seta 8.71 KSC2 — обе форкнуты с него, обе измеряли
   его производные независимо), тогда как собственные kk-цифры самого GigaAM (FLEURS 4.4, CV 13.8) —
   вендорский самоотчёт Sber; движок под нашим алиасом официально не документирован, совпадение с
   `alemai/ai-sage/GigaAM-Multilingual` побайтовое на наших клипах.
5. **TTS-реальность 2026:** открытые kk-голоса за год переехали на OmniVoice (612M, zero-shot клонирование +
   voice-design) — `stukenov/kazakh-tts-omnivoice-experiment-a` (Apache-2.0, WER 7.48 %, UTMOS 3.08) и
   `TilLabs/kokoro-tts-kazakh` (CPU real-time) — а единственные опубликованные MOS принадлежат ISSAI 2021/2022
   (Tacotron2, 3.67–4.54) и KazEmoTTS 2024 (3.51–3.57); Google Cloud TTS казахского не имеет вообще.
