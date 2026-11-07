# CQA Prototype Implementation Plan (v2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Every task is mirrored by a GitHub issue; work on a branch named `<issue>-<slug>` and open a PR into `main`.

**Goal:** A Conversation Quality Analytics prototype with these parts:
- Named, versioned checklists.
- LLM scoring of operator dialogs (RU/KZ/EN, chats and calls), with evidence turns.
- Appeals, and reviewer decisions that recompute the total.
- A benchmark that picks the model and mode that best match the organizers' Ground Truth.

**Architecture:**
- **Backend:** Python Litestar, async end to end. Scoring is a pure synchronous module driven entirely by checklist config. The evaluator calls any OpenAI-compatible endpoint through named model profiles. The main candidates are self-hosted vLLM models on an H200; paid APIs are the alternative and fallback.
- **Storage:** JSON files under `data/store/`.
- **Frontend:** TypeScript compiled by plain `tsc` to ES modules. No framework, no bundler, styles scoped under `.cqa`, mounted through a single `mountCqa(root, opts)` entry so it can be wrapped as a Dynamics 365 HTML web resource.
- **Shared types:** generated from the pydantic models, so the two sides cannot drift.

**Tech Stack:**
- **Backend:** Python 3.14, Litestar + uvicorn, pydantic v2, niquests (`AsyncSession`), `tomllib`.
- **Tests:** pytest + pytest-asyncio (`asyncio_mode = "auto"`), `litestar.testing.AsyncTestClient`.
- **Frontend:** TypeScript 5 (`strict`), `json-schema-to-typescript`.
- **Serving:** vLLM (OpenAI-compatible, structured outputs) on an H200 behind its own Cloudflare named tunnel with `--api-key`.
- **App exposure:** `cloudflared` named tunnel.
- **CI:** GitHub Actions.

**Spec:**
- `docs/CQA_Hackathon_Student_Guide.md`: the task guide.
- `docs/CQA_Chat_Quality_Checklist.md`: the organizer checklist (PDF beside it).
- `docs/organizer-answers.md`: organizer clarifications from Telegram, quoted with message ids.

## Clock (UTC+5)

T0 = 12:00 Nov 7.

| Mark | Time | Event |
|---|---|---|
| H+1.5 | 13:30–14:30 | Contract phase merged; tracks start |
| H+4 | 16:00 | H200 endpoint up; benchmark phase 1 |
| H+7 | 19:00 | Track A core green; kakhotitee moves to accuracy work |
| H+7–H+10 | 19:00–22:00 | Gold labeling, 8 dialogs each |
| H+10–H+12 | 22:00–00:00 | Benchmark phase 2; default profile/mode/k chosen |
| H+12–H+21 | until 09:00 Nov 8 | Prompt iteration on disagreements |
| H+21 | 09:00 | Feature freeze, demo rehearsal |
| H+23 | 11:00 | Control set opens; run immediately |
| H+24 | 12:00 | Stop-code; tag `stop-code` |

## Team and Agent Tiers

| Track | Owner | Scope |
|---|---|---|
| Integration | arynyklas | contracts, default checklists, CI, merges, organizer watch, tunnel, README, control run |
| A: core | kakhotitee | dataset, checklists, scoring, store, API, batch CLI; then accuracy work |
| B: evaluator | arynyklas | LLM client, profiles, evaluator, H200 coordination, benchmark, gold set, prompt iteration |
| C: frontend | Batyrkhantzy111 | scaffold, 4 views, appeals, CSS, demo script |

Agent tiers, carried on each issue as a `tier:*` label:
- **`tier:m1`** (Opus): contracts, scoring, the evaluator, and review of research conclusions.
- **`tier:m2`** (Sonnet): implementation inside a track, and research.
- **`tier:m3`** (Qwen 3.8 Flash): only single-file tasks whose issue body fully specifies the output format. Never give it a task that needs cross-file context.

## Global Constraints

- No login/registration. UI language Russian. Explanations always in Russian; evidence is quoted in the dialog's original language (it is rendered from the transcript, never copied by the LLM).
- Speakers `client`, `operator`, `bot`, `system`. Only operator behaviour is scored; bot and system turns are context. Evidence may cite any turn ("Укажите конкретную реплику или системное сообщение").
- Timestamps are shown verbatim: chats use `MM:SS`, calls use ISO 8601 with offset. Evidence anchors by turn index (`idx` = array position), never by timestamp.
- Dataset API: GET with `group_id`. Response is `{error, isSuccess, data:{dataset_group_id,total_records,records[]}}`, and each record is `{conversation_id, channel ("agent chat"|"voice call"), language ("RU"|"KZ"|"EN"), transcript[{timestamp,speaker,text}], audio_url|null}`.
- The base URL is in env `DATASET_URL`, which contains a signed `sig=`. It is never committed, and the dataset is fetched only by the server (CORS).
- Checklist rules, verbatim from the PDF:
  - "«Да» даёт полный вес, «Нет» — ноль."
  - Scale criteria use only the listed steps, and the "верхняя ступень шкалы должна давать полный вес".
  - "Исключите критерии с N/A и пропорционально перераспределите их веса … Максимум должен остаться 100 баллов."
  - "Округлите итог до двух знаков" (round the total to 2 decimals). Rounding mode is `ROUND_HALF_UP` and applies to the total and section totals only.
  - "Если применимых критериев с весом нет, итог не рассчитывается" (no applicable weighted criteria means no total).
  - "Грубые ошибки отметьте отдельно" (gross errors are flagged separately and never change the total).
- Calls use a separate default checklist derived from the chat one. The only changes allowed are the ones organizer message #2343 states.
- Several named checklists can exist. Each has its own version history and a default channel. Every evaluation records `checklist_id` and `checklist_version`. Saving a checklist never mutates stored evaluations, and re-applying it means a full re-evaluation.
- Every evaluation keeps its raw LLM calls (messages, response text, model, timings) as an audit record. Organizers check that the system "действительно анализирует новые диалоги".
- Control set: the submitted results are raw system output. No manual edits or appeals happen before submission; appeals are demoed on DEV.
- Secrets live only in `.env` (gitignored); `.env.example` lists the variable names. The repo is public.
- Demo (5 min): dialog list → evaluation + evidence jump + N/A + total → appeal + decision + new total → edit criterion + re-apply.

## Review Focus

- **Empty transcript:** `evaluate` raises `EvaluationError("пустой транскрипт")`. The batch job records it per dialog and continues. (B2, A4)
- **LLM cites a turn idx ≥ len(transcript), or omits evidence for a non-N/A verdict:** only that criterion is retried once with the validation error. A second failure fails the dialog, which is recorded in the job; nothing invalid is ever stored. (B2)
- **Reviewer sets `na` on a criterion with `na_allowed=false`, or a step not in `steps`:** 400 with the reason, and the appeal stays open. (A4)
- **Checklist saved while a batch job runs:** the job keeps the version it started with. Each evaluation records that version, and the result card renders the criteria of the recorded version, not the latest. (A2, A4, C4)
- **Control `group_id` returns `isSuccess:false`, non-JSON or a timeout:** the API answers 502 `{error}`, the UI shows the message, and the cached group stays untouched. (A1, C3)

---

## File Structure

```
server/
  __init__.py
  config.py            # env + config/profiles.toml loading            [Contract]
  models.py            # ALL pydantic contracts                          [Contract; changes need regenerated types]
  mock_app.py          # serves contracts/examples for Track C; DELETED in A4
  dataset.py           # A1
  checklists.py        # A2
  scoring.py           # A3
  store.py             # A4 evaluations, appeals, raw audit (one JSON file per object)
  jobs.py              # A4 in-memory batch jobs
  routes/{datasets,checklists,evaluations,appeals}.py   # A4
  app.py               # A4 Litestar app + static web/
  llm/{client,fake}.py # B1
  evaluator/{schema,prompt,parse,vote,run}.py           # B2
config/profiles.toml   # model profiles; env-var NAMES only, no secrets
data/checklists/{chat,call}.default.json                # Contract (integrator)
data/cache/            # gitignored dataset cache
data/store/            # gitignored runtime store
contracts/schema.json  # generated from server/models.py
contracts/examples/*.json                               # one per API response type
bench/{select_gold,prefill,render_transcripts,run,metrics}.py   # B4, B5
bench/gold/            # assignments.json, transcripts/*.md, labels.<login>.csv
bench/results/         # gitignored except summary.md files
scripts/{gen_types,run_batch}.py
web/{index.html,cqa.css,tsconfig.json,package.json}
web/src/{main,api,router,types.gen}.ts
web/src/views/{checklists,dialogs,result,review}.ts
web/src/ui/{transcript,criteria-table,appeal-modal}.ts
tests/fixtures/dev.json  # DEV snapshot with sig values replaced by REDACTED
tests/test_*.py
docs/{api,demo,organizer-answers,mentor-questions}.md
docs/research/*.md
.github/workflows/ci.yml
.env.example
README.md
GLOSSARY.md
```

---

## Contracts (Contract phase output; every track consumes these names)

`server/models.py`. Field types are pydantic v2. API JSON uses `float` for points and totals; scoring computes with `Decimal` internally.

- `Turn(idx:int, timestamp:str, offset_s:float|None, speaker:Literal['client','operator','bot','system'], text:str)`
  - `offset_s` is the seconds since the first turn, for ISO timestamps (calls), and `None` for `MM:SS` chats. Call timestamps carry 7 fractional digits, so they are parsed in Python, not in the browser.
- `Record(conversation_id:str, channel:Literal['agent chat','voice call'], language:Literal['RU','KZ','EN'], transcript:list[Turn], audio_url:str|None)`
- `ConversationSummary(conversation_id, channel, language, turns:int, latest:EvaluationSummary|None)`
- `ScaleStep(value:int, description:str)`
- `Section(id:str, title:str)`
- `Criterion(id:str, section_id:str|None, title:str, description:str, answer_type:Literal['yes_no','scale'], weight:float, steps:list[ScaleStep]|None, na_allowed:bool, na_condition:str|None, kind:Literal['scored','gross_error']='scored')`
- `Checklist(id:str, name:str, channel_default:Literal['agent chat','voice call']|None, version:int, sections:list[Section], criteria:list[Criterion], notes:str, source:str)`
- `ChecklistSummary(id, name, channel_default, version)`
- Verdict strings:
  - `yes_no` criteria use `"yes"` or `"no"`.
  - `scale` criteria use `str(step.value)`.
  - `"na"` is allowed only when `na_allowed`.
  - For `gross_error`, `"yes"` means a gross error was found.
- `Item(criterion_id:str, verdict:str, explanation:str, evidence_idx:list[int], expected_range:tuple[int,int]|None, na_reason:str|None, votes:dict[str,int])`
- `ScoreItem(criterion_id, verdict, applicable:bool, points:float|None, max_points:float, effective_points:float|None)`
  - `effective_points` = `points / Σ applicable max_points × 100`.
- `SectionScore(section_id, title, total:float|None)`
- `Score(total:float|None, sections:list[SectionScore], gross_error:bool, applicable_weight:float, items:list[ScoreItem])`
- `Usage(prompt_tokens:int, completion_tokens:int, calls:int, seconds:float)`
- `EvaluationSummary(id, checklist_id, checklist_version, total:float|None, final_total:float|None, gross_error:bool, created_at)`
- `Evaluation(id:str, conversation_id, group_id, checklist_id, checklist_version:int, profile:str, model:str, mode:Literal['single','per_criterion'], k:int, created_at:datetime, items:list[Item], score:Score, usage:Usage)`
- `RawCall(evaluation_id, criterion_ids:list[str], messages:list[dict], response_text:str, model:str, started_at:datetime, seconds:float)`
- `Decision(action:Literal['confirm','change'], new_verdict:str|None, reason:str, decided_at:datetime)`
- `Appeal(id, evaluation_id, criterion_id, comment:str, created_at, status:Literal['open','resolved'], decision:Decision|None)`
- `FinalItem(criterion_id, original_verdict:str, decision:Decision|None, final_verdict:str)`
- `FinalResult(items:list[FinalItem], score:Score)`
- `EvaluationView(evaluation:Evaluation, checklist:Checklist, appeals:list[Appeal], final:FinalResult)` (`checklist` is the recorded version)
- `Job(id, state:Literal['running','finished'], total:int, done:int, failed:dict[str,str], evaluation_ids:list[str])`
- `ApiError(error:str, details:list[str]|None)`

API, also documented in `docs/api.md` with request bodies. The server listens on port 8787 and all routes are under `/api`.

| Method | Path | Body / query | Response |
|---|---|---|---|
| GET | `/datasets/{group_id}/conversations` | `refresh:bool=false` | `list[ConversationSummary]` · 502 on dataset failure |
| GET | `/datasets/{group_id}/conversations/{cid}` | | `Record` |
| GET | `/checklists` | | `list[ChecklistSummary]` |
| POST | `/checklists` | `Checklist` (version ignored) | `Checklist` v1 · 400 `ApiError.details` = validation errors |
| GET | `/checklists/{id}` | `version:int?` | `Checklist` |
| PUT | `/checklists/{id}` | `Checklist` | `Checklist` with version+1 · 400 |
| POST | `/evaluations/batch` | `{group_id, conversation_ids, checklist_id:str|null, profile?, mode?, k?}` | `Job` (`checklist_id=null` → default by channel) |
| GET | `/jobs/{id}` | | `Job` |
| GET | `/conversations/{cid}/evaluations` | | `list[EvaluationSummary]` newest first |
| GET | `/evaluations/{id}` | | `EvaluationView` |
| GET | `/evaluations/{id}/raw` | | `list[RawCall]` |
| POST | `/appeals` | `{evaluation_id, criterion_id, comment}` | `Appeal` · 400 if empty comment / unknown criterion |
| GET | `/appeals` | `status=open|resolved?` | `list[{appeal, evaluation_id, conversation_id, item:Item, criterion:Criterion}]` |
| POST | `/appeals/{id}/decision` | `{action, new_verdict?, reason}` | `{appeal:Appeal, final:FinalResult}` · 400 on empty reason / invalid verdict |

Model profiles live in `config/profiles.toml`, loaded by `server.config.load_profiles() -> dict[str, Profile]`:

```toml
[profiles.fake]
provider = "fake"

[profiles.h200-gemma]
provider = "openai"
base_url_env = "H200_GEMMA_BASE_URL"   # https://hk-gemma.sek.su/v1
api_key_env = "H200_API_KEY"
model = "gemma-4:31b"                  # dense 31B, ctx 65536; KV pool 190k tokens → ≤16 concurrent on long transcripts
supports_n = true                      # send n=k in one request; else k parallel requests
structured = "json_schema"             # response_format type
max_concurrency = 16
max_tokens = 4096
extra_body = {}                        # merged into every request
cost = { kind = "gpu", usd_per_hour = 0.0, concurrency = 16 }   # or { kind = "tokens", usd_per_mtok_in = 0.0, usd_per_mtok_out = 0.0 }

[profiles.h200-gptoss]                 # base H200_GPTOSS_BASE_URL, model "gpt-oss:120b", 120B MoE, ctx 131072, max_concurrency 48
extra_body = { reasoning_effort = "low" }   # reasoning model: its reasoning tokens count toward max_tokens

[profiles.h200-kz]                     # base H200_KZ_BASE_URL, model "qwen3.5-35b-a3b-kazakh", 35B MoE (3B active), ctx 65536, max_concurrency 48
extra_body = {}                        # do NOT send reasoning_effort: it turns thinking on and can spend all of max_tokens with content=null
```

H200 endpoints are served by the GPU agent's own Cloudflare named tunnel `hackathon-h200`. One key for all three lives in `.env`. Only `/v1/*` and `/health` are routed. The namespace is deleted after 12:00 Nov 8.

Client requirements:
- **User-Agent:** the client sends `User-Agent: Mozilla/5.0 (cqa)`, because Cloudflare blocks default library user agents.
- **Invalid replies:** the client treats `finish_reason=="length"` or `content is None` as an invalid reply, and retries it like any other invalid output. Server-side, any-whitespace is now disabled on all three endpoints; before that, strict `json_schema` got stuck in a whitespace loop.
- **Thinking:** gemma and kz have thinking off by default. A thinking variant is a separate profile that sets `extra_body = { chat_template_kwargs = { enable_thinking = true } }`, and the benchmark compares it.
- **Warmup:** the first request to hk-kz takes about 30 s, so the bench runner sends one warmup request per profile before timing.
- **Probe** (13:59, KZ greeting case, strict schema, temperature 0): gemma and gpt-oss (low) gave the valid `yes` with evidence `[1]`; kz without `reasoning_effort` gave a valid `yes`.

Env `LLM_PROFILE` selects the default profile, and `EVAL_MODE` / `EVAL_K` select the default mode and k.

---

## Phase 0: Contract (integrator, H0–H+1.5)

### Task 0.1: Contracts, examples, type generation, CI, mock server

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `.env.example`, `server/__init__.py`, `server/config.py`, `server/models.py`, `server/mock_app.py`, `config/profiles.toml`, `contracts/examples/*.json`, `scripts/gen_types.py`, `docs/api.md`, `tests/test_contracts.py`, `.github/workflows/ci.yml`, `web/package.json`, `web/src/types.gen.ts`, `GLOSSARY.md`

**Interfaces:**
- Produces: everything in **Contracts**.
- `scripts/gen_types.py` writes `contracts/schema.json`, a single JSON Schema with `$defs` for every model, then runs `npx json-schema-to-typescript contracts/schema.json -o web/src/types.gen.ts`.
- `uvicorn server.mock_app:app --port 8787` serves every API route from `contracts/examples/`.

- [ ] **Step 1:** Add `tests/test_contracts.py::test_examples_validate`. Every file `contracts/examples/<Model>[.<variant>].json` must validate against the model of that name. The examples must cover:
  - an evaluation with one N/A item;
  - one `no` item carrying `expected_range`;
  - a call record with ISO timestamps;
  - a resolved appeal whose `final.score.total` differs from `evaluation.score.total`.
- [ ] **Step 2:** `pytest tests/test_contracts.py -q` → FAIL (no models).
- [ ] **Step 3:** Implement `models.py` and the example JSON files.
  - `pyproject.toml`: litestar, uvicorn, pydantic, niquests, pytest, pytest-asyncio; `asyncio_mode="auto"`.
  - `.gitignore`: `.env`, `.venv`, `data/cache`, `data/store`, `web/dist`, `node_modules`, `bench/results/**` except `summary.md`.
  - CI on PRs:
    1. `pip install -e .[dev]`
    2. `pytest -q`
    3. `npm ci --prefix web`
    4. `npx --prefix web tsc --noEmit -p web`
    5. `python scripts/gen_types.py && git diff --exit-code contracts web/src/types.gen.ts`
- [ ] **Step 4:** run → PASS. Then `uvicorn server.mock_app:app --port 8787` and `curl localhost:8787/api/checklists` returns the example list.
- [ ] **Step 5:** commit `feat: contracts, examples, generated types, CI`; push to `main`. This is the only direct push to `main`.

### Task 0.2: Default checklists (chat verbatim, call derived)

**Files:**
- Create: `data/checklists/chat.default.json`, `data/checklists/call.default.json`, `tests/test_default_checklists.py`

**Interfaces:**
- Consumes: `Checklist`.
- `checklists.validate` comes later in A2. This task only asserts the pydantic shape and the values below.

- [ ] **Step 1: Failing tests:**
  - `chat.default.json`: `id=="chat"`, `channel_default=="agent chat"`, and 8 criteria `c01..c08`.
  - Weights are `[10,15,20,20,15,15,5,0]`.
  - `c04.steps` values are `[0,5,10,15,20]`; `c06.steps` values are `[0,4,7,10]`.
  - `na_allowed` is true exactly for `c02,c03,c04,c07`.
  - `c08.kind=="gross_error"`.
  - Sections: `s1` holds c01,c02; `s2` holds c03,c04; `s3` holds c05,c06,c07; `s4` holds c08.
  - `call.default.json`: `id=="call"`, `channel_default=="voice call"`, and the same ids, weights, steps and N/A flags.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3: Write the chat checklist.** Every `description`, `na_condition` and step `description` is copied verbatim from `docs/CQA_Chat_Quality_Checklist.md`, using page 1 rules and page 2 scales. `notes` gets the page-2 calculation rules and the page-3 guidance verbatim: "Нет" vs N/A, what to cite, consultation vs dialog management, the definition of "в обход компании", and the example justification.
- [ ] **Step 4: Write the call checklist.** Copy the chat checklist and change only the following:
  - Replace "чат"/"переписка" with "разговор"/"звонок".
  - Replace `c06.description` with the #2343 wording: "логичность ведения разговора, понятность объяснений, отсутствие неуместных выражений, корректность речевых формулировок и управление паузами".
  - Set `c04.description` to the #2343 wording: "ответил ли оператор на вопросы клиента, не предоставил ли ошибочную информацию, объяснил ли необходимые действия".
  - Set `source` to cite #2343.
- [ ] **Step 5:** run → PASS; commit `feat: default chat and call checklists` via PR.

---

## Track A: Core (kakhotitee)

### Task A1: Dataset loader

**Files:**
- Create: `server/dataset.py`, `tests/test_dataset.py`, `tests/fixtures/dev.json` (already present after the scrub)

**Interfaces:**
- `normalize_response(payload:dict, group_id:str) -> list[Record]` is sync and raises `DatasetError(message)`.
- `async load_dataset(group_id:str, refresh:bool=False, session:niquests.AsyncSession|None=None) -> list[Record]`:
  - The cache is `data/cache/<group_id>.json`, holding the raw payload. A cache hit with `refresh=False` makes no network call.
  - The URL is `DATASET_URL` with its `group_id` query parameter replaced. Timeout 60 s.
  - On a fetch or parse failure it raises `DatasetError` and leaves an existing cache file byte-identical.

- [ ] **Step 1: Failing tests** on `tests/fixtures/dev.json`:
  - 65 records.
  - Each `turn.idx` equals its position.
  - 5 `voice call` records, each with a non-null `audio_url`.
  - Timestamps equal the raw values.
  - Chat turns have `offset_s is None`. For `p4-ru-003`, `offset_s` is `0.0` on turn 0 and `round(offset_s,3)==9.227` on turn 2 (timestamps `…15:49:13.1900670+00:00` → `…15:49:22.4171535+00:00`).
  - `normalize_response({"isSuccess":False,"error":"boom"}, "X")` raises a `DatasetError` matching `boom`.
  - A record missing `transcript` raises `DatasetError` naming its `conversation_id`.
  - Async test: with a stub session returning non-JSON and a cache present, the cache is unchanged and `DatasetError` is raised.
- [ ] **Step 2:** run → FAIL. **Step 3:** implement. **Step 4:** run → PASS. **Step 5:** PR `feat: dataset loader`.

### Task A2: Checklist store with versions

**Files:**
- Create: `server/checklists.py`, `tests/test_checklists.py`

**Interfaces:**
- `validate(c:Checklist) -> list[str]` returns Russian error messages; an empty list means valid.
- `class ChecklistStore(root:Path)`:
  - `async list() -> list[ChecklistSummary]`
  - `async get(id:str, version:int|None=None) -> Checklist`
  - `async create(c) -> Checklist`
  - `async save(c) -> Checklist`
  - `async seed_defaults(dir:Path)`
- Layout: `data/store/checklists/<id>/v<N>.json`. Writes go to a temp file and are renamed, with one `asyncio.Lock` per id. `save` writes v(N+1) and never rewrites vN.
- `seed_defaults` copies `data/checklists/*.default.json` only for ids not yet present.

- [ ] **Step 1: Failing tests.** Both default files validate with `[]`. Each of these produces exactly one error:
  - duplicate criterion id;
  - `scale` with `steps=None` or fewer than 2 steps;
  - duplicate step values;
  - `yes_no` with `steps`;
  - negative weight;
  - `gross_error` with weight ≠ 0 or `answer_type!='yes_no'`;
  - unknown `section_id`;
  - Σ weight over `scored` criteria == 0.

  Then: saving twice yields versions 2 and 3, and `get(id, 2)` returns the v2 content. Finally, `create` with an existing id raises `ChecklistError`.
- [ ] **Step 2–4:** FAIL → implement → PASS. **Step 5:** PR `feat: versioned checklist store`.

### Task A3: Scoring

**Files:**
- Create: `server/scoring.py`, `tests/test_scoring.py`

**Interfaces:**
- `compute_score(checklist:Checklist, verdicts:dict[str,str]) -> Score`:
  - Raises `ValueError` on a missing or unknown criterion id, or on a verdict not allowed for that criterion.
- `final_result(checklist:Checklist, evaluation:Evaluation, appeals:list[Appeal]) -> FinalResult`:
  - A resolved `change` decision overrides the verdict.
  - `confirm` keeps the verdict.
  - Open appeals are ignored.
- Algorithm, in `Decimal`:
  - `points` = weight for `yes`, 0 for `no`, and `step/max_step × weight` for scale.
  - `na` gives `points=None` and `applicable=False`.
  - `gross_error` criteria never contribute; `Score.gross_error = verdict=="yes"`.
  - `total = Σpoints / Σapplicable weights × 100`, rounded to 2 decimals with `ROUND_HALF_UP`. If Σ applicable weights == 0, `total=None`.
  - Sections use the same formula restricted to their criteria.

- [ ] **Step 1: Failing tests** on `chat.default.json`:
  - (a) All `yes`, c04=`20`, c06=`10`, c08=`no` → `total == 100.0`, `gross_error False`.
  - (b) c01 yes, c02 no, c03 na, c04 `15`, c05 yes, c06 `7`, c07 yes, c08 no → `total == 69.38`, `applicable_weight == 80`, and c06 `points == 10.5`.
  - (c) c01 yes, c02 yes, c03 na, c04 `5`, c05 no, c06 `7`, c07 no, c08 no → `total == 50.63` (the half-up case; half-even would give 50.62). Section totals: `s1 == 100.0`, `s2 == 25.0`, `s3 == 30.0`, `s4 is None`.
  - (d) Case (a) with c08=`yes` → `gross_error True`, `total == 100.0`.
  - (e) An inline checklist whose only scored criteria allow N/A, all `na` → `total is None`.
  - (f) c01=`na` → `ValueError`; c04=`12` → `ValueError`.
  - (g) `final_result` with a resolved `change` from c06 `7` to `10` on case (b) → final total `75.0`, while `evaluation.score.total` stays `69.38`.
- [ ] **Step 2–4:** FAIL → implement → PASS. **Step 5:** PR `feat: scoring with N/A redistribution`.

### Task A4: Store, jobs, routes, app

**Files:**
- Create: `server/store.py`, `server/jobs.py`, `server/routes/*.py`, `server/app.py`, `tests/test_api.py`
- Delete: `server/mock_app.py`

**Interfaces:**
- Consumes: A1–A3, and `evaluator.run.evaluate` (B2, see the signature there; use the `fake` profile in tests).
- Produces: every route in the **Contracts** API table.
- Store layout: `data/store/evaluations/<id>.json`, `data/store/raw/<evaluation_id>.jsonl`, `data/store/appeals/<id>.json`.
- `JobRunner.start(...)` runs `asyncio.gather` under `Semaphore(EVAL_CONCURRENCY=4)`. Per-dialog exceptions go into `Job.failed`. The checklist version is resolved once at job start.
- Litestar exception handlers: `DatasetError`→502 and `ValidationError`/`ChecklistError`→400, both as `ApiError`; unknown id → 404. Static `web/` is served at `/`.

- [ ] **Step 1: Failing async tests** using `AsyncTestClient`, the `fake` profile, and the dataset loaded from the fixture via a dependency override:
  - A batch on 2 ids finishes. `GET /evaluations/{id}` returns `score.total` and the `checklist` at the recorded version.
  - PUT checklist bumps the version. The next batch records the new version, and the old evaluation still returns its old checklist.
  - Appeal with an empty comment → 400.
  - Decision `change` → `final.score.total` differs from the original.
  - Decision with `new_verdict:"na"` on c01 → 400.
  - Appeal on an N/A criterion is accepted.
  - A dataset stub that raises → 502 `{error}`.
  - `checklist_id:null` on a call record uses checklist `call`.
  - `GET /evaluations/{id}/raw` is non-empty.
- [ ] **Step 2–4:** FAIL → implement → PASS. Then `uvicorn server.app:app --port 8787`, and `curl "localhost:8787/api/datasets/DEV/conversations"` returns 65 rows.
- [ ] **Step 5:** PR `feat: store, jobs, API`.

### Task A5: Batch runner CLI

**Files:**
- Create: `scripts/run_batch.py`

**Interfaces:**
- `python scripts/run_batch.py <group_id> [--refresh] [--checklist auto|<id>] [--profile P] [--mode M] [--k K]` uses the same store and JobRunner as the app. It prints a table of id, channel, lang, total, gross and error, then the token, time and cost totals per profile cost model. It writes `out/<group_id>.results.json` with the per-criterion verdicts.

- [ ] **Step 1:** Implement.
- [ ] **Step 2: Smoke:** `python scripts/run_batch.py DEV --profile fake` gives 65 rows and 0 errors.
- [ ] **Step 3:** PR `feat: batch runner`.

---

## Track B: Evaluator and accuracy (arynyklas)

### Task B1: LLM client and fake provider

**Files:**
- Create: `server/llm/client.py`, `server/llm/fake.py`, `tests/test_llm_client.py`

**Interfaces:**
- `Completion(text:str, prompt_tokens:int, completion_tokens:int, seconds:float)`
- `class LLMClient(Protocol): async def complete(self, messages:list[dict], schema:dict, temperature:float, n:int) -> list[Completion]`
- `make_client(profile:Profile) -> LLMClient`
  - **`openai` provider:** niquests `AsyncSession`, POST `{base}/chat/completions` with `response_format={"type":"json_schema","json_schema":{"name":"cqa","schema":schema,"strict":true}}`. If the profile has `supports_n`, it sends `n` in one request; otherwise it makes n concurrent requests. Timeout 180 s, one retry on 429/5xx.
  - **`fake` provider:** reads the verdict enums from the `schema` it is given and returns deterministic schema-valid JSON. It picks each verdict by a seeded hash of the messages and the criterion id. Its evidence is the first `[idx] … operator:` line of the user message, or idx 0 if there is none.

- [ ] **Step 1: Failing async tests:**
  - With a stub session returning `n=3` choices, `complete` gives 3 completions with summed usage.
  - With `supports_n=false`, it makes 3 requests.
  - A 500 followed by a 200 gives one retry.
  - The fake output validates (`jsonschema` dev dependency) against a hand-written two-criterion schema: a yes_no criterion with na, and a scale criterion with steps `[0,5]`.
- [ ] **Step 2–4:** FAIL → implement → PASS. **Step 5:** PR `feat: LLM client and fake provider`.

### Task B2: Evaluator

**Files:**
- Create: `server/evaluator/{schema,prompt,parse,vote,run}.py`, `tests/test_evaluator.py`

**Interfaces:**
- `build_schema(checklist, criterion_ids:list[str]) -> dict` produces a JSON Schema object with one property per criterion. Each property is `{verdict: enum(allowed verdicts), explanation, evidence_idx:int[], expected_range:[int,int]|null, na_reason:str|null}`.
- `build_messages(record, checklist, criterion_ids) -> list[dict]`. The system prompt is in Russian and contains:
  - the checklist rules and `notes` verbatim;
  - the instruction that only operator turns are scored;
  - the instruction that explanations are written in Russian;
  - the instruction to cite turns by `[idx]`.

  The user message holds the transcript as `[idx] (timestamp) speaker: text` lines, plus channel and language.
- `parse_items(text, record, checklist, criterion_ids) -> tuple[list[Item], dict[str,str]]` returns the valid items and the errors per criterion id. Validation rules:
  - Each evidence idx satisfies `0 ≤ idx < len(transcript)`.
  - `yes` or a scale step requires non-empty evidence.
  - `no` requires evidence or `expected_range`.
  - `na` requires `na_reason`.
  - Markdown fences are tolerated.
- `aggregate(samples:list[list[Item]], checklist) -> list[Item]`:
  - The majority verdict wins, and ties go to the verdict that appears first in sample order.
  - For a scale criterion where all samples are applicable, the median step wins, taking the lower middle when k is even.
  - Explanation and evidence come from the first sample with the chosen verdict.
  - `votes` holds the counts.
- `async evaluate(record, checklist, *, profile:Profile, mode:Literal['single','per_criterion']='single', k:int=1, llm:LLMClient|None=None, group_id:str) -> tuple[Evaluation, list[RawCall]]`:
  - The default path uses temperature 0 when k=1 and 0.7 when k>1.
  - **`single` mode:** one request covers all criteria.
  - **`per_criterion` mode:** one request per criterion, all run concurrently.
  - Criteria that fail validation are retried once with the error text appended. A second failure raises `EvaluationError`.
  - An empty transcript raises `EvaluationError("пустой транскрипт")` without calling the model.

- [ ] **Step 1: Failing async tests** with a scripted fake client:
  - A valid single-mode run gives an Evaluation whose `score` equals `compute_score` on its verdicts.
  - Per-criterion mode makes 8 calls.
  - idx 999 triggers a retry of only that criterion, and the second call's messages contain the error text.
  - Two invalid replies raise `EvaluationError`.
  - `na` on c01 is rejected as invalid.
  - k=3 with verdicts `[yes,no,yes]` gives `yes` and `votes=={"yes":2,"no":1}`.
  - c06 steps `[4,10,7]` give `7`.
  - An empty transcript makes no client calls.
  - The `RawCall` count equals the number of client calls.
  - The `fake` provider's output for `p1-ru-001` validates against `build_schema(chat.default.json, all ids)` and passes `parse_items` with no errors.
- [ ] **Step 2–4:** FAIL → implement → PASS. **Step 5:** PR `feat: evaluator with schema output, retry, voting`.

### Task B3: H200 endpoints (human + GPU agent)

- [ ] Have the GPU agent bring up OpenAI-compatible vLLM endpoints with structured outputs behind a Cloudflare named tunnel with `--api-key`. One endpoint per candidate class:
  - a large open MoE (~100–120B) that fits one H200;
  - a mid-size model (~30B);
  - a Kazakh-tuned open model.
- [ ] Record the base URLs in `.env` (gitignored) and the profiles in `config/profiles.toml`. Put `usd_per_hour` from `docs/research/llm-candidates.md`.
- [ ] **Smoke:** `python -m bench.run --profiles <each> --set smoke --n 3` gives valid JSON for all 3.

### Task B4: Benchmark harness and phase 1

**Files:**
- Create: `bench/run.py`, `bench/metrics.py`, `tests/test_bench_metrics.py`

**Interfaces:**
- `python -m bench.run --profiles a,b --mode single|per_criterion --k 1|5 --set smoke|gold|all [--n N]` writes `bench/results/<ts>/<profile>-<mode>-k<k>.jsonl` and `bench/results/<ts>/summary.md`.
- `metrics.py` provides:
  - `weighted_agreement(pred:dict[str,str], gold:dict[str,str], checklist) -> float`. Each criterion's checklist weight counts toward the agreement when its verdicts are equal; `gross_error` criteria use weight 1. The sum is divided by the total of those weights.
  - `total_mae(...)`
  - `gross_accuracy(...)`
  - Phase-1 metrics: share of valid JSON on the first try, share needing a retry, failure share, seconds per evaluation, tokens per evaluation, and cost per evaluation.

- [ ] **Step 1: Failing tests** for `weighted_agreement`:
  - Identical verdicts → 1.0.
  - Only c03 differs (weight 20) → `(100-20+1)/(100+1)`.
- [ ] **Step 2–4:** FAIL → implement → PASS.
- [ ] **Step 5: Phase 1.** Run every profile with modes single and per_criterion and k=1 on a stratified 12-dialog smoke set. Then hand-read the KZ explanations (Russian text, KZ quotes). Drop the profiles that fail. Commit `summary.md`.

### Task B5: Gold set

**Files:**
- Create: `bench/select_gold.py`, `bench/prefill.py`, `bench/render_transcripts.py` (tier m3, spec below), `bench/gold/assignments.json`, `bench/gold/transcripts/*.md`, `bench/gold/labels.<login>.csv`

**Interfaces:**
- `select_gold.py --seed 7` picks 24 DEV ids: 12 RU (including 3 calls), 6 KZ and 6 EN. It assigns 8 ids to each of `arynyklas`, `kakhotitee` and `Batyrkhantzy111`. It rotates the prefill profile across the 3 candidate classes and records `{id, labeler, prefill_profile}`.
- `render_transcripts.py [--ids a,b,…]` (all fixture records when `--ids` is omitted) writes `bench/gold/transcripts/<id>.md` from `tests/fixtures/dev.json`:
  - The header is `# <id> · <channel> · <language>`.
  - For calls, a line `audio: <audio_url>` follows the header.
  - After one blank line, each turn becomes one line `[idx] timestamp · speaker: text`.
  - There is no other content.
- `prefill.py` evaluates each id with its assigned profile and writes `labels.<login>.csv`. The columns are `conversation_id,criterion_id,prefill_verdict,prefill_evidence,prefill_explanation,gold_verdict,gold_evidence,note`, with `gold_*` left empty. Prefill columns are never edited, which lets us measure prefill bias.
- Humans fill `gold_verdict` and `gold_evidence` in their own CSV only.

- [ ] **Step 1:** Implement the three scripts and generate the files. **Step 2:** PR. **Step 3:** label (ready-for-human, 8 dialogs each, H+7–H+10).

### Task B6: Phase 2 and default choice

- [ ] Run `bench.run --set gold` for the surviving profiles × modes {single, per_criterion} × k {1,5}.
- [ ] Rank by `weighted_agreement`, then `total_mae`, then `gross_accuracy`.
- [ ] Pick the default profile, mode and k. A paid profile wins only if it beats the best self-hosted profile by more than 5 percentage points of agreement.
- [ ] Set `LLM_PROFILE`, `EVAL_MODE` and `EVAL_K` in `.env.example`. Commit `summary.md` and the README cost line.

### Task B7: Prompt iteration (ongoing until H+21)

- [ ] For each criterion with agreement below 0.8, read the disagreements, adjust the guidance in `prompt.py` without changing the checklist text, and rerun `--set gold`. Keep a change only if `weighted_agreement` does not drop. Log each run in `bench/results/<ts>/summary.md`.
- [ ] Watch for overfitting: the 24 gold ids are the only signal, so changes go into the general guidance, never into rules aimed at a specific dialog.

---

## Track C: Frontend (Batyrkhantzy111)

Shared rules for all of Track C:
- All CSS lives under `.cqa`.
- No inline scripts, and no global state outside `mountCqa`.
- Every view exports `render(root:HTMLElement, ctx:Ctx): Promise<void>`, where `Ctx = {api:Api, params:Record<string,string>}`.
- Types come only from `types.gen.ts`.
- RU strings are kept in one object in `web/src/i18n.ts`.

### Task C1: Scaffold

**Files:**
- Create: `web/index.html`, `web/tsconfig.json`, `web/src/main.ts`, `web/src/api.ts`, `web/src/router.ts`, `web/src/i18n.ts`, `web/cqa.css` (tokens only)

**Interfaces:**
- `mountCqa(root:HTMLElement, opts:{apiBase:string})`
- `class Api` has one method per API route and throws `Error(ApiError.error)` on non-2xx.
- Hash routes: `#/checklists`, `#/checklists/<id>`, `#/dialogs/<group>`, `#/evaluation/<id>`, `#/review`.
- `npm run build` runs `tsc` → `web/dist`.

- [ ] **Step 1:** Implement. **Step 2: Smoke** against `server.mock_app`: every route renders a heading without console errors; take a screenshot. **Step 3:** PR.

### Task C2: Checklist editor

- [ ] **List view:** the checklists with name, channel and version, plus "Создать" (create).
- [ ] **Editor:**
  - Edit name and channel_default.
  - Add, remove and reorder criteria.
  - Per criterion: title, description, section, answer_type, weight, steps (value plus description), N/A allowed plus condition, and kind.
  - Show the live Σ of scored weights.
  - Save sends PUT. A 400 shows `details` next to the form, and success shows the new version.
  - Show the version history and a read-only view of each version.
- [ ] **Smoke:** change c06's weight, save, reload; the version is +1 and the value persists. Take a screenshot. Then PR.

### Task C3: Dialogs list and batch evaluate

- [ ] Group input (default `DEV`) and a "Обновить" button (refresh=true).
- [ ] Filters for channel and language.
- [ ] Table columns: id, channel, lang, turns, latest total / final total, gross badge.
- [ ] Multi-select, a checklist select ("по каналу" by default), then "Оценить". The UI polls `/jobs/{id}` every 1 s and shows progress plus per-id errors.
- [ ] A 502 shows the dataset error, and the table keeps its previous rows.
- [ ] **Smoke** with the fake profile: evaluate 5 dialogs and see the totals. Take a screenshot. Then PR.

### Task C4: Result card

- [ ] **Transcript pane.** Speaker-coloured turns with `id="turn-<idx>"` and the timestamp shown verbatim. Calls get an `<audio controls src=audio_url>`. Each evidence link on a call sets `audio.currentTime = turn.offset_s`.
- [ ] **Criteria table.** One row per criterion of the *recorded* checklist version, showing:
  - title and section;
  - verdict (Да / Нет / N/A / step);
  - points / max_points and effective_points;
  - explanation;
  - evidence links, which scroll to the turn and highlight it;
  - for `no`, an "ожидалось здесь" (expected here) link that highlights `expected_range`;
  - for N/A, `na_reason`;
  - a votes badge when k>1.
- [ ] **Header.** Total (or "Итог не рассчитывается" when no total can be computed), section totals, a gross-error badge, the checklist name and version, the model and mode, and a "Вызовы модели" link (model calls) to `/raw`.
- [ ] **History.** The list of evaluations for this conversation, each with its checklist version.
- [ ] **Smoke** on `p1-ru-001` and `p4-ru-003` with a real profile: evidence highlights the right turns and audio seeks. Take screenshots. Then PR.

### Task C5: Appeals and review

- [ ] An "Оспорить" (appeal) button per row opens a modal with the criterion and a comment (required). It POSTs `/appeals`.
- [ ] `#/review` shows the open appeals. Each card shows the criterion, the original verdict and explanation, the comment, and the fragment `transcript[evidence_idx[0]-3 .. +3]` (or the `expected_range` ±1), clamped.
- [ ] The decision form has confirm / change. Change offers a new verdict from the allowed values, and the reason is required.
- [ ] On the result card, an appealed row shows original → decision (reason) → final, and the header shows original total → final total.
- [ ] **Smoke:** appeal c06 on an evaluated dialog, change it, and check that the final total differs and persists after reload. Take a screenshot. Then PR.

### Task C6: Visual pass (tier m3, single file `web/cqa.css`)

- [ ] Input: the token list in `cqa.css` and the class names used by C1–C5, listed in the issue body.
- [ ] Output: rules for those classes only, with no new classes. Use system font, 14px base, speaker colours from the tokens, sticky table header, and a focus-visible ring.
- [ ] **Smoke:** screenshot of each view.

### Task C7: Demo script

- [ ] Write `docs/demo.md`: a 5-minute click path following the guide timings, using specific DEV ids for N/A, gross error and a call. Rehearse at H+21.

---

## Integration and Release (arynyklas)

- [ ] **I1: Organizer watch, every 2 h until the stop-code.** Read the Telegram topics Announcements (5), Freedom Broker (732) and Q&A Organizers (4) in chat `Data Challenge'26`. Append each case-relevant answer to `docs/organizer-answers.md`, quoted with its message id. Open an issue for any answer that changes a contract.
- [ ] **I2: Mentor questions.** `docs/mentor-questions.md`. The user posts them in the Freedom Broker topic; the agent never posts.
- [ ] **I3: Named Cloudflare tunnel.** Expose the app on this PC (RTX 5080): `cloudflared tunnel run cqa`, mapping `<host>` to `localhost:8787`. Put the URL in the README.
- [ ] **I4: README.** Cover:
  - setup (Python, `pip install -e .[dev]`, `npm ci --prefix web && npm run build --prefix web`);
  - `.env` variables and `uvicorn server.app:app --port 8787`;
  - profiles and the self-hosted vs paid story;
  - the control-set procedure;
  - checklist editing;
  - model name and cost per evaluation: GPU price per hour × measured GPU-seconds ÷ concurrency for self-hosted, tokens × price for paid, with the source cited;
  - the architecture diagram.
- [ ] **I5: Control run** at 11:00 Nov 8: `python scripts/run_batch.py <CONTROL_GROUP> --refresh`. Check the results in the UI. Do not edit anything.
- [ ] **I6: Stop-code** at 12:00 Nov 8: `git tag stop-code && git push --tags`. The criterion swap at the check is done in the UI on this commit.

## Research (tier m2, conclusions reviewed by m1; output `docs/research/<topic>.md`, ≤1 page each)

- **R1, Litestar** (Track A):
  - dependency override in `AsyncTestClient`;
  - static files serving `web/` at `/`;
  - exception handlers mapping domain errors to 400/502 with a JSON body;
  - background tasks vs `asyncio.create_task` for jobs.
- **R2, niquests `AsyncSession`** (Tracks A, B): timeouts, retry configuration, JSON, connection reuse, Windows quirks.
- **R3, LLM candidates** (Track B):
  - the current best open model per class (MoE ~100–120B, ~30B, Kazakh-tuned) that fits one H200 in vLLM with structured outputs;
  - published RU/KZ quality evidence;
  - cheap paid and frontier paid API prices per Mtok;
  - the public on-demand H200 price per hour with its source.
- **R4, Dynamics 365 HTML web resources** (Track C): file and size limits, CSP, how scripts load, `Xrm` context, relative paths; what our `mountCqa` must avoid.
- **R5, contact-center QA and LLM-as-judge practice** (Track B): how human graders apply yes/no vs N/A and gross-error flags; known LLM-judge failure modes (position bias, leniency, evidence hallucination) and prompt mitigations.

## Self-Review

- **Coverage of guide and checklist requirements:**
  - Checklist CRUD with versions and channel defaults: A2, C2.
  - RU/KZ/EN evaluation with bot/system as context only: B2.
  - Per-criterion answer, points, weight, explanation, evidence, skipped-action location, N/A reason: B2 + C4.
  - Weights, N/A redistribution, rounding, gross error: A3.
  - Card link to the message and the call fragment, plus the player: C4.
  - Appeal and decision with recompute, keeping original, decision and final: A3, A4, C5.
  - Dataset, CORS and the control set: A1, I5.
  - README and cost: I4, B6.
  - Ground-Truth accuracy: B3–B7.
  - Process integrity (raw audit): A4, B2, C4.
  - Calls: 0.2.
- **Types:** `Item.verdict` strings are shared by `compute_score`, `parse_items`, `Decision.new_verdict` and the UI. `Turn.idx` is the only evidence anchor.
- **Gaps:** the tunnel hostname is not chosen yet (I3).
