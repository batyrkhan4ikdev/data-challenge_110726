# CQA API

Port 8787, all routes under `/api`. Errors are `ApiError` (`contracts/examples/ApiError.dataset.json`). Models: `server/models.py`; TS types: `web/src/types.gen.ts`.

Run the server: `uvicorn server.app:app --port 8787`. It serves `web/` in HTML mode at `/` and `web/dist` at `/static`. Set `LLM_PROFILE=fake` for an offline, deterministic model. Example response bodies for every model are in `contracts/examples/`, and `tests/test_contracts.py` validates them.

| Method | Path | Request (body / query) | Response |
|---|---|---|---|
| GET | `/datasets/{group_id}/conversations` | `refresh:bool=false` | `ConversationSummary[]` — `ConversationSummary.list.json`; 502 `ApiError.dataset.json` (mock: `group_id=FAIL`) |
| GET | `/datasets/{group_id}/conversations/{cid}` | | `Record` — `Record.chat.json`, `Record.call.json` |
| GET | `/datasets/{group_id}/analytics` | | `GroupAnalytics`: counts, mean total, gross-error ids, `by_channel` / `by_language`, per-criterion yes/no/N/A and mean % of points, and the total histogram. It uses the latest evaluation per dialog, with its total after appeals |
| GET | `/checklists` | | `ChecklistSummary[]` — `ChecklistSummary.list.json` |
| POST | `/checklists` | `Checklist` (version ignored) — `Checklist.json` | `Checklist` v1 · 400 `ApiError.details` |
| GET | `/checklists/{id}` | `version:int?` | `Checklist` — `Checklist.json` |
| PUT | `/checklists/{id}` | `Checklist` | `Checklist` version+1 · 400 |
| POST | `/evaluations/batch` | `BatchRequest {group_id, conversation_ids, checklist_id:str\|null, profile?, mode?, k?}` | `Job` — `Job.running.json` |
| GET | `/jobs/{id}` | | `Job` — `Job.finished.json` |
| GET | `/conversations/{cid}/evaluations` | | `EvaluationSummary[]` newest first — `EvaluationSummary.list.json` |
| GET | `/evaluations/{id}` | | `EvaluationView` — `EvaluationView.json` (embeds `Evaluation.json`) |
| GET | `/evaluations/{id}/raw` | | `RawCall[]` — `RawCall.list.json` |
| POST | `/appeals` | `AppealCreate {evaluation_id, criterion_id, comment}` | `Appeal` — `Appeal.json` · 400 |
| GET | `/appeals` | `status=open\|resolved?` | `AppealQueueItem[]` — `AppealQueueItem.list.json` |
| POST | `/appeals/{id}/decision` | `DecisionCreate {action, new_verdict?, reason}` | `DecisionResult` — `DecisionResult.json` · 400 |
| GET | `/profiles` | | `[{name, model, provider}]` — model profiles from `config/profiles.toml`; the env default (`LLM_PROFILE`, else `fake`) comes first. |

Error statuses: 400 for validation errors (`ApiError.details` lists them; checklist validation uses `error: "Чек-лист невалиден"`), 404 `ApiError` for unknown ids, 502 `ApiError` when the dataset API fails.

Example files live in `contracts/examples/`.
