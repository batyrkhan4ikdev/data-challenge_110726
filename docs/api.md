# CQA API

Port 8787, all routes under `/api`. Errors are `ApiError` (`contracts/examples/ApiError.dataset.json`). Models: `server/models.py`; TS types: `web/src/types.gen.ts`.

Run the server: `uvicorn server.app:app --port 8787`. It serves `web/` in HTML mode at `/` and `web/dist` at `/static`. Set `LLM_PROFILE=fake` for an offline, deterministic model. Example response bodies for the main models are in `contracts/examples/` (not every model has one, for example the facts, analytics, confirmation, recourse and upload models do not), and `tests/test_contracts.py` validates the ones that exist.

| Method | Path | Request (body / query) | Response |
|---|---|---|---|
| GET | `/datasets/{group_id}/conversations` | `refresh:bool=false` | `ConversationSummary[]` — `ConversationSummary.list.json`; 502 `ApiError.dataset.json` (mock: `group_id=FAIL`) |
| GET | `/datasets/{group_id}/conversations/{cid}` | | `Record` — `Record.chat.json`, `Record.call.json` |
| GET | `/datasets/{group_id}/conversations/{cid}/facts` | | `DialogFacts` — детерминированные факты диалога без LLM (длительность, первая реакция оператора и SLA 180 с, макс. ожидание клиента, реплики, маски, события); только для показа, в промпт не попадает. 404 как у записи |
| GET | `/datasets/{group_id}/analytics` | `baseline:str?` | `GroupAnalytics`: counts, mean total, gross-error ids, `by_channel` / `by_language`, per-criterion yes/no/N/A and mean % of points, and the total histogram. It uses the latest evaluation per dialog, with its total after appeals. `baseline` is another group id: the drift block compares this group against it (without it, the first half of this group's evaluations against the second): PSI for the total and each criterion, KS for the total only |
| GET | `/checklists` | | `ChecklistSummary[]` — `ChecklistSummary.list.json` |
| POST | `/checklists` | `Checklist` (version ignored) — `Checklist.json` | `Checklist` v1 · 400 `ApiError.details` |
| GET | `/checklists/{id}` | `version:int?` | `Checklist` — `Checklist.json` |
| PUT | `/checklists/{id}` | `Checklist` | `Checklist` version+1 · 400 |
| POST | `/evaluations/batch` | `BatchRequest {group_id, conversation_ids, checklist_id:str\|null, profile?, mode?, k?, transcript_source?:str\|null}` | `Job` — `Job.running.json` |
| GET | `/jobs/{id}` | | `Job` — `Job.finished.json` |
| GET | `/conversations/{cid}/evaluations` | | `EvaluationSummary[]` newest first — `EvaluationSummary.list.json` |
| GET | `/evaluations/{id}` | | `EvaluationView` — `EvaluationView.json` (embeds `Evaluation.json`) |
| GET | `/evaluations/{id}/raw` | | `RawCall[]` — `RawCall.list.json` |
| POST | `/appeals` | `AppealCreate {evaluation_id, criterion_id, comment}` | `Appeal` — `Appeal.json` · 400 |
| GET | `/appeals` | `status=open\|resolved?` | `AppealQueueItem[]` — `AppealQueueItem.list.json` |
| POST | `/appeals/{id}/decision` | `DecisionCreate {action, new_verdict?, reason}` | `DecisionResult` — `DecisionResult.json` · 400 |
| GET | `/profiles` | | `[{name, model, provider}]` — model profiles from `config/profiles.toml`; the env default (`LLM_PROFILE`, else `fake`) comes first. |
| GET | `/asr/providers` | | `AsrProviderInfo[]` — speech-to-text providers offered in the call card, in `config/asr.toml` order (disabled ones omitted): `{id, label, hosting, available, note, quality}`. `available=false` with `note` «не настроен: задайте <ENV>» when its env vars are unset; `quality` is the benchmark row from `data/asr/quality.json` |
| GET | `/conversations/{cid}/transcripts` | | `TranscriptSourceInfo[]` — the transcript sources of a conversation: `api` (organizer's, always available), one `asr` entry per enabled provider in `config/asr.toml` (`available` once a transcript exists), `custom`. `quality` comes from `data/asr/quality.json` (may be null) |
| POST | `/conversations/{cid}/transcribe` | `TranscribeRequest {group_id, provider}` | `Record` — audio → ASR → speaker roles + PII masking (judge model = env `LLM_PROFILE`) → stored as source `<provider>`. Calls only. 400 `ApiError` if the provider is unknown or not configured («… не настроен»), 502 if the audio or the ASR fails. Slow (minutes) |
| PUT | `/conversations/{cid}/transcripts/custom` | `CustomTranscriptRequest {group_id, text}` | `Record` — one turn per line with `оператор:` / `клиент:` / `бот:` (`operator:` / `client:` / `bot:`, `О:` / `К:`) prefixes; an unprefixed line continues the previous turn; no timestamps (`offset_s` null). Calls only. 400 on empty text or text before the first prefix |
| POST | `/uploads/call` | multipart `file`, `language=auto\|RU\|KZ\|EN`, `provider` | `Record` — a recording goes through ASR, roles and masking and becomes a new call in the group `UPLOADS`. 413 over 50 MB, 503 without ASR |
| POST | `/uploads/chat` | `UploadChatRequest {text, language}` | `Record` — a pasted chat (`оператор:` / `клиент:` / `бот:` lines) becomes a new chat in `UPLOADS`; 400 on bad text |
| GET | `/uploads/{cid}/audio` | | the stored audio of an uploaded call |
| DELETE | `/uploads/{cid}` | | 204 — removes the uploaded record and its audio |
| GET | `/conversations/{cid}/regpack` | `group_id:str`, `evaluation_id:str?` | ZIP «дело»: transcript, evaluation, checklist version, appeals, final result, raw calls, SHA-256 hashes. Header `X-Regpack-Selfcheck: ok\|fail` is the result of recomputing the total; `scripts/verify_regpack.py` repeats it offline |
| GET | `/criterion-reliability` | | the measured judge agreement with the DEV labels per criterion (`data/criterion_reliability.json`); `{source: null, criteria: {}}` if the file is not generated |
| POST | `/evaluations/{id}/confirmations` | `ConfirmationCreate {criterion_ids, mode: batch\|single, reviewer, note?}` | `Confirmation` — the reviewer accepts criteria; stored apart from appeals, never changes a total. 400 if `reviewer` is empty |
| GET | `/evaluations/{id}/confirmations` | | `Confirmation[]` of that evaluation |
| GET | `/confirmations/stats` | | `ConfirmationStats {batch, single, overridden}`: criteria accepted in a batch, one by one, and changed through appeals |
| GET | `/evaluations/{id}/attention` | | `Attention {score, reasons, criterion_ids}` — review priority (not a probability of error), see `server/triage.py`; the same value is in `ConversationSummary.attention` |
| POST | `/evaluations/{id}/recourse` | `RecourseRequest {criterion_id}` | `Recourse {edits, rationale, before, after, verified, …}` — «как было бы правильно»: the judge proposes at most 2 operator-turn edits for one lost criterion, and the edited dialog is judged again on that criterion alone. Coaching only: never stored as an evaluation, totals and appeals are untouched |

Transcript sources: sources other than `api` are `Record` files in `data/store/transcripts/<cid>/<source>.json`; records in `data/calls/<source>.dev.json` (organizer API format, e.g. `freedomspeech.dev.json`) are seeded as source `<source>` for their conversations. `GET /datasets/{group_id}/conversations/{cid}` and `…/facts` take `source=<id>` (default `api`; 404 if that source has no transcript for the dialog). `BatchRequest.transcript_source` (`null` = `api`) evaluates that source's `Record`; a dialog without it fails with a Russian reason in `Job.failed`, and `Evaluation.transcript_source` (default `api`) records which one was used. Chats always use `api`.

Error statuses: 400 for validation errors (`ApiError.details` lists them; checklist validation uses `error: "Чек-лист невалиден"`), 404 `ApiError` for unknown ids, 502 `ApiError` when the dataset API fails.

Example files live in `contracts/examples/`.
