# Хостед-ASR: что доступно прямо сейчас и почём

Проверено 2026-11-07 на 10-секундном клипе `data/audio/p4-ru-003.mp3` (`ffmpeg -ss 30 -t 10`, 10.0 с, mono 16 кГц).
Сырые транскрипты в отчёте не приводятся (в них ПДн) — только длина текста в символах.
Все запросы — с заголовком `User-Agent: Mozilla/5.0 (cqa)` (Cloudflare требует браузерный UA; без него FreedomSpeech отдаёт 1010).

Тестовый клип содержит в основном один голос (IVR-приветствие + речь оператора), поэтому «реплик двух
говорящих» на нём мало — диаризацию судим по наличию меток в ответе, а не по их чередованию.

## 1. Наш H200-эндпоинт ASR (`AIGW_BASE_URL`, `AIGW_API_KEY`)

`GET {base}/models` → 200, 59 моделей. Аудио-модели в списке: ASR — `whisper-large-v3`,
`alemai/openai/whisper-large-v3`, `alemai/openai/whisper-large-v3-turbo`,
`alemai/ai-sage/GigaAM-Multilingual`, `kuspeech:multilingual`; TTS — `alemai/k2-fsa/OmniVoice`
(`glide-v1.2` в списке есть, но на обеих аудио-дорожках 404 «No matching route found» — не аудио-эндпоинт).
Метаданных о модальностях `/models` не отдаёт (`/models/<id>` → 404).

`POST {base}/audio/transcriptions`, multipart `file` + `model` + `response_format=verbose_json` — все пять ASR: **200, русский текст, кириллица ≥0,70, мусор не замечен**:

| Модель | Работает? | segments | words | Диаризация | Latency (10 с клип) | Цена |
|---|---|---|---|---|---|---|
| `whisper-large-v3` | ✅ 200 | ✅ 3 сегм., `start`/`end` есть | ❌ `words: null`; параметры `word_timestamps=true` и `timestamp_granularities[]=word` принимаются, но игнорируются | ❌ (поля `speaker`/`diarization` в ответе нет; `diarize=true` игнорируется) | 0,42–0,47 с | внутренняя (H200), тарифа нет — `usage: null`, биллинг-эндпоинтов нет (см. ниже) |
| `alemai/openai/whisper-large-v3` | ✅ 200 | ✅ 1 сегм. (5,74–9,98 с) | ✅ на верхнем уровне: `words[]` со `start`/`end` | ❌ | 0,75–1,33 с | "" |
| `alemai/openai/whisper-large-v3-turbo` | ✅ 200 | ❌ `segments: null` | ❌ `words: null` | ❌ | 0,79–0,82 с | "" |
| `alemai/ai-sage/GigaAM-Multilingual` | ✅ 200 | ✅ 1 сегм. (0–10,01 с), но `avg_logprob`/`tokens` = null | ❌ | ❌ (`diarize=true` игнорируется) | 0,33–0,74 с | "" |
| `kuspeech:multilingual` | ✅ 200 | ❌ пустой массив | ✅ `words[]`: `{word, start, end, confidence}` (25 слов на 10 с) | ❌ (`diarize`/`num_speakers` игнорируются) | 0,34–0,42 с | "" |

Дополнительно замерено:

- Текст клипа, длина: `whisper-large-v3` 178 симв.; `alemai/…-v3` 82 симв. (проглотил первые ~5,7 с
  речи на этом клипе — единственный минус); `turbo` 175; `GigaAM` 167; `kuspeech` 167.
- `kuspeech:multilingual` вернул **побайтово тот же текст**, что `alemai/ai-sage/GigaAM-Multilingual`,
  и такой же `duration` — это, судя по всему, тот же движок GigaAM под алиасом KUSpeech (`owned_by: KUSpeech`,
  официально не документировано; ответ идентичен на клипе, в `model` эхо алиаса).
- `turbo` в `verbose_json` не отдаёт ни сегментов, ни `language`, ни `duration` — только `text`.
- `POST {base}/audio/translations` (multipart `file`+`model`): для `whisper-large-v3` 200 (английский перевод),
  для `kuspeech:multilingual` 404 «No matching route found: model».
- `POST {base}/audio/speech` — работает **только с JSON-телом** `{"model":"alemai/k2-fsa/OmniVoice","input":"…"}`
  → 200, WAV (RIFF), ~0,35 с на короткую фразу; multipart → 404. TTS-поставщик для фичи «Озвучить» найден.
- Цена: у эндпоинта нет биллинг-эндпоинтов (`/usage`, `/billing/usage`, `/subscription`, `/organization` → 404),
  в ответах ASR `usage: null`. Это наша/партнёрская инфраструктура — outer-тарифа нет, считаем бесплатной для бенчмарка.

## 2. OpenRouter (`openrouter.ai/api/v1`, ключ `OPENROUTER_API_KEY`)

`GET /models` → 424 модели, из них `architecture.input_modalities` содержит `audio` — 46.
Отдельной модели вида `gpt-4o-transcribe`/whisper в роутере **нет**; `gpt-4o*` не принимают аудио.
Цены $/1M токенов (`audio` — входной аудио-токен, `prompt` — прочий вход, `completion` — выход; `—` = поле null):

| Модель | audio | prompt | completion |
|---|---|---|---|
| google/gemini-2.5-flash | 1,00 | 0,30 | 2,50 |
| google/gemini-2.5-flash-lite | 0,30 | 0,10 | 0,40 |
| google/gemini-2.5-pro / -preview | 1,25 | 1,25 | 10,00 |
| google/gemini-3-flash-preview (:batch) | 1,00 (0,50) | 0,50 (0,25) | 3,00 (1,50) |
| google/gemini-3.1-flash-lite (:batch, -preview) | 0,50 (0,25) | 0,25 (0,125) | 1,50 (0,75) |
| google/gemini-3.1-pro-preview (:batch, -customtools) | 2,00 (1,00) | 2,00 (1,00) | 12,00 (6,00) |
| google/gemini-3.5-flash (:batch) | 3,00 (1,50) | 1,50 (0,75) | 9,00 (4,50) |
| google/gemini-3.5-flash-lite (:batch) | 0,30 (0,15) | 0,30 (0,15) | 2,50 (1,25) |
| google/gemini-3.6-flash (:batch) | 0,75 (0,375) | 0,75 (0,375) | 3,75 (1,875) |
| google/gemini-3.7-flash (:batch) | 0,75 (0,375) | 0,75 (0,375) | 3,75 (1,875) |
| google/gemini-3.8-flash (:batch) | 0,75 (0,375) | 0,75 (0,375) | 3,75 (1,875) |
| google/gemini-4-argon (:batch) | 2,00 (1,00) | 2,00 (1,00) | 10,00 (5,00) |
| ~google/gemini-flash-latest | 0,75 | 0,75 | 3,75 |
| ~google/gemini-pro-latest | 2,00 | 2,00 | 10,00 |
| openai/gpt-audio | 32,00 | 2,50 | 10,00 |
| openai/gpt-audio-mini | 0,60 | 0,60 | 2,40 |
| mistralai/voxtral-small-24b-2507 | 100,00 | 0,10 | 0,30 |
| xiaomi/mimo-v2.5 | — | 0,40 | 2,00 |
| xiaomi/mimo-v2.6-flash / -pro / -pro-ultraspeed | — | 0,14 / 0,435 / 4,35 | 0,28 / 0,87 / 8,70 |
| qwen/qwen3.8-omni-flash | — | 0,15 | 0,47 |
| meta/muse-spark-open | — | 1,25 | 4,25 |
| meta/muse-wonder | — | 4,00 | 20,00 |
| thinkingmachines/inkling | — | 1,00 | 4,05 |
| thinkingmachines/inkling-small (:batch) | — | 0,45 (0,36) | 1,20 (0,96) |
| perceptron/perceptron-mk1.5 | — | 0,15 | 1,50 |
| nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free | 0 | 0 | 0 |
| stealth/crouton-alpha | — | 0 | 0 |
| openrouter/auto, auto-beta, auto-code, typesafe/jev-router | — | −1 (динам.) | −1 |

Варианты `:batch` — тот же провайдер за половину цены (подтверждается листингом: у всех пар batch = 50 %).

Тест чат-комплетиона с `input_audio` (base64 mp3, `format: "mp3"`), промпт «Дословно транскрибируй аудио,
разметь говорящих как [Оператор]/[Клиент]», `usage.include=true`. Потрачено суммарно **≈ $0,0013** (4 успешных
вызова; бюджет $0,10 не выбран и не выбирался):

| Модель | Работает? | timestamps / segments / диаризация | Latency | Стоимость вызова |
|---|---|---|---|---|
| `google/gemini-2.5-flash` | ✅ 200 (1 из 3 запросов упал по сети через 42 с; повторный 200 за 1,3 с) | выдача — один текстовый блок (184 и 204 симв. в двух прогонах); метка `[Оператор]` есть всегда, `[Клиент]` появилась в одном из прогонов; тайм-коды вида `0:00` — только во втором прогоне: **стиль выдачи нестабилен**, структурированных полей нет | 23,2 с холодный / 1,3 с тёплый | $0,00044–0,00049; `audio_tokens: 323` на 10 с (≈ 32 ток/с) |
| `openai/gpt-audio-mini` | ✅ 200 (2/2) | 182 симв., одна строка, есть `[Оператор]`, `Клиент` не появился (говорил один), тайм-кодов в тексте нет; структурированных полей нет | 0,95–1,7 с | $0,00019; `audio_tokens: 100` (10 ток/с) |

Общее: OpenRouter отдаёт **только текст** — тайм-штампы/спикеры возможны лишь в формате, который выдумает
LLM (парсить регэкспом, ненадёжно). `POST /api/v1/audio/transcriptions` как у OpenAI роутер не подтвердил
(пустой POST → 400 «JSON parsing failed», документированного audio-эндпоинта в моделях нет). Провайдер в ответах —
`Google AI Studio` / `OpenAI`. `/credits` → 404, остаток по API не виден.

## 3. FreedomSpeech (`api.freedomspeech.kz`)

- **Хост доступен**: `GET /`, `/v1/models`, `/health`, `/v1/health` отвечают за 0,1–0,3 с корректным
  JSON-404 `{"error":{"message":"unknown route",…}}` (то есть за Cloudflare жив бэкенд, ошибки 1010 нет).
  Таких роутов у него действительно нет — рабочий путь только `POST /v1/audio/transcriptions` (см. `docs/research/freedomspeech.md`).
- `FREEDOMSPEECH_API_KEY`: на момент начала проверки был **не задан**; теперь задан в `.env`, STT-вызовы
  на нём работают (проверено главным агентом; лишних платных вызовов не тратил).
- Ориентир по latency/диаризации из `docs/research/freedomspeech.md`: 5 DEV-звонков (312–620 с) за 7–13 с,
  `diarized_json` даёт говорящих, но тайминги только в `text` как `[speaker-N | s-e]`.
- Периодические таймауты TCP к `freedomspeech.kz/docs` (20–45 с без ответа) — известная сетевая яма на этом канале,
  к API относится так же: ретраи обязательны.

## Итог: что берём в бенчмарк

| Провайдер | Точные параметры вызова | Что даёт |
|---|---|---|
| `aigw-whisper` (`whisper-large-v3`) | `POST {AIGW_BASE_URL}/audio/transcriptions`, UA `Mozilla/5.0 (cqa)`, Bearer `AIGW_API_KEY`, multipart: `file=<mp3>`, `model=whisper-large-v3`, `response_format=verbose_json` | сегменты `start`/`end`, язык, длительность; ~0,5 с / 10 с аудио. Лучший по сегментации из бесплатных |
| `aigw-kuspeech` (`kuspeech:multilingual`) | те же + `model=kuspeech:multilingual` | **пословные** тайм-штампы + `confidence` в `words[]`; сегментов нет — строить из слов; ~0,4 с / 10 с |
| `aigw-whisper-alemai` | те же + `model=alemai/openai/whisper-large-v3` | сегменты + `words[]`; на клипе пропустил начало речи — риск |
| `aigw-gigaam` | те же + `model=alemai/ai-sage/GigaAM-Multilingual` | один сегмент на весь файл, слов нет; текст = kuspeech. В бенчмарк — как дубль kuspeech, не приоритет |
| `aigw-whisper-turbo` | те же + `model=alemai/openai/whisper-large-v3-turbo` | только `text` (без таймингов) — годится лишь для CER-сравнения |
| `openrouter-gemini` | `POST https://openrouter.ai/api/v1/chat/completions`, Bearer `OPENROUTER_API_KEY`, JSON: `model=google/gemini-2.5-flash`, `usage:{include:true}`, user content `[{type:text,text:<промпт>},{type:input_audio,input_audio:{data:<b64>,format:mp3}}]` | текст с метками, иногда тайм-коды; по измеренной цене $0,00045/10 с ≈ $0,03 за 10-мин звонок (все 5 DEV ≈ $0,11); формат выдачи нестабилен, аудио длиннее ~20 с лучше чанковать |
| `openrouter-gptam` | то же, `model=openai/gpt-audio-mini` | текст с метками; $0,00019/10 с ≈ $0,012 за 10-мин звонок; быстрый |
| `freedomspeech` | `POST https://api.freedomspeech.kz/v1/audio/transcriptions`, `X-API-Key`, браузерный UA, `response_format=diarized_json`, `prettify=false` | единственная рабочая **диаризация** из всех проверенных; уже есть результаты в `data/calls/freedomspeech.dev.json` |

- Ни один хостед-эндпоинт, кроме FreedomSpeech, **не делает диаризацию** — роли во всех остальных придётся
  назначать LLM-судье (как и предусмотрено контрактом `asr_to_record`).
- Тайм-штампы сегментов надёжны только у `whisper-large-v3` (H200); пословные — только у `kuspeech:multilingual`.
- Диаризация «из коробки» у hosted-LLM — фикция: метки говорящего приходят текстом и на реальном диалоге
  потребуют парсинга и валидации.
- TTS-замена/второй провайдер для «Озвучить»: `alemai/k2-fsa/OmniVoice`, `POST {AIGW_BASE_URL}/audio/speech`
  c JSON `{model, input}` → WAV, ~0,35 с, бесплатно.
- Бюджет OpenRouter почти не тронут (≈$0,0013 из $0,10 лимита задания).
