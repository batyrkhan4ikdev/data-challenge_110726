# CQA API

Порт 8787, все маршруты под `/api`. Ошибки имеют вид `ApiError` (`contracts/examples/ApiError.dataset.json`). Модели: `server/models.py`; типы TS: `web/src/types.gen.ts`.

Запуск сервера: `uvicorn server.app:app --port 8787`. Он отдаёт `web/` в HTML-режиме по `/` и `web/dist` по `/static`. `LLM_PROFILE=fake` включает офлайн-модель с детерминированным ответом. Примеры тел ответов для основных моделей лежат в `contracts/examples/` (есть не у каждой модели: например, нет у моделей фактов, аналитики, подтверждений, регресса и загрузок), а `tests/test_contracts.py` проверяет существующие.

| Метод | Путь | Запрос (тело / query) | Ответ |
|---|---|---|---|
| GET | `/datasets/{group_id}/conversations` | `refresh:bool=false` | `ConversationSummary[]` — `ConversationSummary.list.json`; 502 `ApiError.dataset.json` (mock: `group_id=FAIL`) |
| GET | `/datasets/{group_id}/conversations/{cid}` | | `Record` — `Record.chat.json`, `Record.call.json` |
| GET | `/datasets/{group_id}/conversations/{cid}/facts` | | `DialogFacts` — детерминированные факты диалога без LLM (длительность, первая реакция оператора и SLA 180 с, макс. ожидание клиента, реплики, маски, события); только для показа, в промпт не попадает. 404 как у записи |
| GET | `/datasets/{group_id}/analytics` | `baseline:str?` | `GroupAnalytics`: количества, средний итог, id грубых ошибок, `by_channel` / `by_language`, по каждому критерию yes/no/N/A и средний % баллов, гистограмма итога. Берётся последняя оценка по каждому диалогу, итог — после апелляций. `baseline` — id другой группы: блок дрейфа сравнивает с ней эту группу (без него — первую половину оценок этой группы со второй): PSI для итога и каждого критерия, KS только для итога |
| GET | `/checklists` | | `ChecklistSummary[]` — `ChecklistSummary.list.json` |
| POST | `/checklists` | `Checklist` (version игнорируется) — `Checklist.json` | `Checklist` v1 · 400 `ApiError.details` |
| GET | `/checklists/{id}` | `version:int?` | `Checklist` — `Checklist.json` |
| PUT | `/checklists/{id}` | `Checklist` | `Checklist` с version+1 · 400 |
| POST | `/evaluations/batch` | `BatchRequest {group_id, conversation_ids, checklist_id:str\|null, profile?, mode?, k?, transcript_source?:str\|null}` | `Job` — `Job.running.json` |
| GET | `/jobs/{id}` | | `Job` — `Job.finished.json` |
| GET | `/conversations/{cid}/evaluations` | | `EvaluationSummary[]` сначала новые — `EvaluationSummary.list.json` |
| GET | `/evaluations/{id}` | | `EvaluationView` — `EvaluationView.json` (включает `Evaluation.json`) |
| GET | `/evaluations/{id}/raw` | | `RawCall[]` — `RawCall.list.json` |
| POST | `/appeals` | `AppealCreate {evaluation_id, criterion_id, comment}` | `Appeal` — `Appeal.json` · 400 |
| GET | `/appeals` | `status=open\|resolved?` | `AppealQueueItem[]` — `AppealQueueItem.list.json` |
| POST | `/appeals/{id}/decision` | `DecisionCreate {action, new_verdict?, reason}` | `DecisionResult` — `DecisionResult.json` · 400 |
| GET | `/profiles` | | `[{name, model, provider}]` — профили моделей из `config/profiles.toml`; первым идёт профиль по умолчанию из окружения (`LLM_PROFILE`, иначе `fake`). |
| GET | `/asr/providers` | | `AsrProviderInfo[]` — провайдеры распознавания речи, предлагаемые в карточке звонка, в порядке `config/asr.toml` (отключённые опущены): `{id, label, hosting, available, note, quality}`. `available=false` с `note` «не настроен: задайте <ENV>», если переменные окружения не заданы; `quality` — строка бенчмарка из `data/asr/quality.json` |
| GET | `/conversations/{cid}/transcripts` | | `TranscriptSourceInfo[]` — источники транскрипта диалога: `api` (организаторов, всегда доступен), по одной записи `asr` на каждого включённого провайдера из `config/asr.toml` (`available`, когда транскрипт уже есть), `custom`. `quality` берётся из `data/asr/quality.json` (может быть null) |
| POST | `/conversations/{cid}/transcribe` | `TranscribeRequest {group_id, provider}` | `Record` — аудио → ASR → роли говорящих + маскирование PII (модель-судья = env `LLM_PROFILE`) → сохраняется как источник `<provider>`. Только звонки. 400 `ApiError`, если провайдер неизвестен или не настроен («… не настроен»), 502, если сбой аудио или ASR. Медленно (минуты) |
| PUT | `/conversations/{cid}/transcripts/custom` | `CustomTranscriptRequest {group_id, text}` | `Record` — одна реплика на строку с префиксами `оператор:` / `клиент:` / `бот:` (`operator:` / `client:` / `bot:`, `О:` / `К:`); строка без префикса продолжает предыдущую реплику; меток времени нет (`offset_s` null). Только звонки. 400 при пустом тексте или тексте до первого префикса |
| POST | `/uploads/call` | multipart `file`, `language=auto\|RU\|KZ\|EN`, `provider` | `Record` — запись проходит ASR, роли и маскирование и становится новым звонком в группе `UPLOADS`. 413 при размере более 50 MB, 503 без ASR |
| POST | `/uploads/chat` | `UploadChatRequest {text, language}` | `Record` — вставленный чат (строки `оператор:` / `клиент:` / `бот:`) становится новым чатом в `UPLOADS`; 400 при некорректном тексте |
| GET | `/uploads/{cid}/audio` | | сохранённое аудио загруженного звонка |
| DELETE | `/uploads/{cid}` | | 204 — удаляет загруженную запись и её аудио |
| GET | `/conversations/{cid}/regpack` | `group_id:str`, `evaluation_id:str?` | ZIP «дело»: транскрипт, оценка, версия чек-листа, апелляции, итоговый результат, сырые вызовы, хеши SHA-256. Заголовок `X-Regpack-Selfcheck: ok\|fail` — результат пересчёта итога; `scripts/verify_regpack.py` повторяет его офлайн |
| GET | `/criterion-reliability` | | измеренное по каждому критерию совпадение судьи с разметкой DEV (`data/criterion_reliability.json`); `{source: null, criteria: {}}`, если файл не сгенерирован |
| POST | `/evaluations/{id}/confirmations` | `ConfirmationCreate {criterion_ids, mode: batch\|single, reviewer, note?}` | `Confirmation` — ревьюер принимает критерии; хранится отдельно от апелляций, итог не меняет. 400, если `reviewer` пуст |
| GET | `/evaluations/{id}/confirmations` | | `Confirmation[]` этой оценки |
| GET | `/confirmations/stats` | | `ConfirmationStats {batch, single, overridden}`: критерии, принятые пакетом, по одному и изменённые через апелляции |
| GET | `/evaluations/{id}/attention` | | `Attention {score, reasons, criterion_ids}` — приоритет проверки (не вероятность ошибки), см. `server/triage.py`; то же значение лежит в `ConversationSummary.attention` |
| POST | `/evaluations/{id}/recourse` | `RecourseRequest {criterion_id}` | `Recourse {edits, rationale, before, after, verified, …}` — «как было бы правильно»: судья предлагает не более 2 правок реплик оператора для одного потерянного критерия, после чего исправленный диалог оценивается заново только по этому критерию. Только для обучения: как оценка не сохраняется, итоги и апелляции не затрагиваются |

Источники транскрипта: источники, кроме `api`, — файлы `Record` в `data/store/transcripts/<cid>/<source>.json`; записи из `data/calls/<source>.dev.json` (формат API организаторов, например `freedomspeech.dev.json`) подгружаются как источник `<source>` для своих диалогов. `GET /datasets/{group_id}/conversations/{cid}` и `…/facts` принимают `source=<id>` (по умолчанию `api`; 404, если у этого источника нет транскрипта для диалога). `BatchRequest.transcript_source` (`null` = `api`) оценивает `Record` этого источника; диалог без него завершается ошибкой с причиной на русском в `Job.failed`, а `Evaluation.transcript_source` (по умолчанию `api`) фиксирует, какой источник использован. Чаты всегда используют `api`.

Статусы ошибок: 400 — ошибки валидации (`ApiError.details` перечисляет их; валидация чек-листа использует `error: "Чек-лист невалиден"`), 404 `ApiError` — неизвестные id, 502 `ApiError` — сбой API датасета.

Файлы примеров лежат в `contracts/examples/`.
