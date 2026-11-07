# CQA API

Port 8787, all routes under `/api`. Errors are `ApiError` (`contracts/examples/ApiError.dataset.json`). Models: `server/models.py`; TS types: `web/src/types.gen.ts`.

Run the mock: `uvicorn server.mock_app:app --port 8787`

| Method | Path | Request (body / query) | Response |
|---|---|---|---|
| GET | `/datasets/{group_id}/conversations` | `refresh:bool=false` | `ConversationSummary[]` — `ConversationSummary.list.json`; 502 `ApiError.dataset.json` (mock: `group_id=FAIL`) |
| GET | `/datasets/{group_id}/conversations/{cid}` | | `Record` — `Record.chat.json`, `Record.call.json` |
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

Example files live in `contracts/examples/`.
