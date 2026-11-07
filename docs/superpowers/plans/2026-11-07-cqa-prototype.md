# CQA Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Conversation Quality Analytics prototype: configurable checklist, LLM scoring of operator dialogs with evidence, appeal and reviewer-decision flow with recomputed totals.

**Architecture:** Python Litestar backend, async end to end (dataset fetch, checklist storage, LLM evaluation, appeals) and a TypeScript frontend compiled with plain `tsc` to ES modules (no framework, no bundler; one self-contained module per screen so it can be wrapped later as a Dynamics 365 HTML web resource). Scoring math is a pure synchronous Python module with no I/O, driven entirely by checklist config. Storage is JSON files under `data/store/`. The backend serves the compiled `web/dist/` statically.

**Tech Stack:** Python 3.14, Litestar + uvicorn, pydantic v2, niquests (`niquests.AsyncSession`) for all outbound HTTP, pytest + `pytest-asyncio` (`asyncio_mode = "auto"`, tests are `async def`, API tests use `litestar.testing.AsyncTestClient`); TypeScript 5 (`tsc` only, `strict: true`), vitest for pure frontend logic only; OpenAI-compatible chat-completions API configured by env (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`).

**Spec:** `docs/CQA_Hackathon_Student_Guide.md` (task guide). The eight-criteria checklist PDF is a separate organizer file that is **not in the repo yet** (see Task 2 blocker).

## Global Constraints

- Backend Python, frontend TypeScript (`strict`), HTML and CSS; no UI framework; styles scoped under a root `.cqa` class (adaptable to a Dynamics 365 HTML component).
- No login/registration.
- Languages RU, KZ, EN must be supported by evaluation; bot and system turns are context only (never scored as operator behaviour).
- Speakers: `client`, `operator`, `bot`, `system`. Preserve original timestamps verbatim (chat `MM:SS`; call ISO 8601 with offset).
- Dataset API: GET with `group_id`; response `{error, isSuccess, data:{dataset_group_id,total_records,records[]}}`; record `{conversation_id, channel ("agent chat"|"voice call"), language ("RU"|"KZ"|"EN"), transcript[{timestamp,speaker,text}], audio_url|null}`. DEV = 65 records (60 chats, 5 RU calls; observed: 35 RU incl. calls, 15 KZ, 15 EN).
- Per criterion output: answer, points, weight, explanation, evidence turn. Skipped action: state the checked transcript range. N/A: state the reason.
- Weighted scale scores; N/A redistributes weight over applicable criteria; gross error flagged separately; rounding rules taken from the checklist PDF.
- Appeal: pick criterion + comment; reviewer sees disputed score, comment, dialog fragment; confirms or changes with a reason; total recomputed; card keeps original, decision, final.
- Checklist edits (add/change criterion text, weight, answer type, N/A flag, numeric scale) saved via UI and applied at evaluation time. Organizers will swap one criterion at the check.
- Control set opens at +23h; stop-code commit at +24h; README with run steps; send repo link early. Paid model: record model name and approx cost per evaluation in README.
- CORS: dataset is fetched by the server, never the browser.
- 5-minute demo path: dialog list -> evaluation + evidence jump + N/A + total -> appeal + decision + new total -> edit criterion + re-apply.

## Review Focus

- Transcript empty or operator never speaks → all operator criteria N/A with reason; total never NaN/ZeroDivisionError.
- LLM returns evidence index outside the transcript → rejected/retried, never rendered as a link.
- All criteria N/A or applicable weights sum to 0 → total `None` ("not scorable"), UI shows that state.
- Criterion removed/replaced after evaluation exists → old results stay viewable with their `checklist_version`; re-evaluation uses the new one.
- Appeal on an N/A criterion or on the gross-error flag → allowed; reviewer change recomputes correctly.
- KZ text, mixed-language turns, voice-call ISO timestamps → shown unmodified; evidence anchors by turn index, not timestamp.
- Control-set `group_id` returns `isSuccess:false` or non-JSON → clear UI error, previous data intact.

---

## File Structure

```
server/
  __init__.py
  app.py            # Litestar app, static files router, route handler wiring
  models.py         # pydantic: Record, Turn, Checklist, Criterion, Item, Evaluation, Appeal
  dataset.py        # fetch/cache/normalize
  checklist.py      # validate, load/save, versioning
  scoring.py        # pure compute_score
  evaluator.py      # prompt, LLM call, validation
  store.py          # JSON-file persistence
  routes.py         # API handlers
web/
  index.html
  cqa.css
  tsconfig.json
  src/api.ts        # typed fetch client + shared types mirroring models.py
  src/app.ts        # hash router
  src/views/{checklist,dialogs,result,review}.ts
  src/logic/evidence.ts   # pure helpers (fragment slicing, anchor ids)
  dist/             # tsc output (gitignored)
data/dev.json       # present
data/checklist.default.json
tests/              # pytest (async)
web/tests/          # vitest
pyproject.toml
README.md
```

---

### Task 1: Project scaffold and dataset module

**Files:**
- Create: `pyproject.toml`, `server/__init__.py`, `server/models.py`, `server/dataset.py`, `tests/test_dataset.py`, `.gitignore` (`.venv`, `web/dist`, `node_modules`, `data/store`)

**Interfaces:**
- Produces: `models.Turn(idx:int, timestamp:str, speaker:Literal['client','operator','bot','system'], text:str)`; `models.Record(conversation_id, channel, language, transcript:list[Turn], audio_url:str|None)`; `dataset.normalize_response(payload:dict) -> list[Record]` (sync; raises `DatasetError` on `isSuccess:false` or bad shape; `idx` = array position); `async dataset.load_dataset(group_id:str, refresh:bool=False) -> list[Record]` (cache `data/<group_id>.json`; base URL from env `DATASET_URL`, `group_id` appended as query param; fetched with `niquests.AsyncSession`; on fetch failure with cache present raise `DatasetError` leaving cache intact).

- [ ] **Step 1: Failing tests** (`tests/test_dataset.py`, using `data/dev.json`): 65 records; each turn `idx` equals position; 5 records `channel=='voice call'` with non-null `audio_url`; timestamps equal raw; `normalize_response({"isSuccess":False,"error":"boom"})` raises `DatasetError` matching `boom`.
- [ ] **Step 2:** `pytest tests/test_dataset.py -q` → FAIL (import error).
- [ ] **Step 3:** Implement as above; `pyproject.toml` pins deps (litestar, uvicorn, pydantic, niquests, pytest, pytest-asyncio) and sets `[tool.pytest.ini_options] asyncio_mode = "auto"`. Add one async test: `load_dataset` with a stubbed session returning a bad payload raises `DatasetError` and leaves an existing cache file byte-identical.
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** `git add -A && git commit -m "feat: scaffold and dataset loader"`

### Task 2: Checklist schema and default config

**Blocker:** needs the organizer checklist PDF (eight criteria, weights, scales, N/A rules, rounding). Transcribe it verbatim into `data/checklist.default.json`; do not invent criteria. (`Data 2 (1) 1.pdf` in Downloads is a company brochure, not the checklist.)

**Files:**
- Create: `server/checklist.py`, `data/checklist.default.json`, `tests/test_checklist.py`

**Interfaces:**
- Produces: `models.Criterion(id:str, section:str|None, text:str, weight:float, type:Literal['scale','yesno'], scale:tuple[float,float]|None, na_allowed:bool, na_rule:str|None, gross_error:bool=False)`; `models.Checklist(version:int, rounding_digits:int, rounding_mode:Literal['half_up','half_even'], sections:list[Section], criteria:list[Criterion])`; `checklist.validate(c:Checklist) -> list[str]` (errors; empty = ok); `load() -> Checklist`; `save(c:Checklist) -> Checklist` (bumps version, archives old at `data/store/checklists/v<N>.json`); `get_version(n:int) -> Checklist`.

- [ ] **Step 1: Failing tests:** default file validates with no errors and has 8 criteria; duplicate `id` → error; `type='scale'` with `scale=None` or `min>=max` → error; negative weight → error; two `save` calls give versions N, N+1 and `get_version(N)` returns old content.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** Implement. Gross-error criteria excluded from the weighted sum (flagged separately) unless the PDF says otherwise.
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** commit `feat: checklist schema and default config`.

### Task 3: Scoring math

**Files:**
- Create: `server/scoring.py`, `tests/test_scoring.py`

**Interfaces:**
- Consumes: `Checklist` (Task 2).
- Produces: `models.Answer(criterion_id:str, applicable:bool, points:float|None, gross_error:bool=False)`; `scoring.compute_score(checklist:Checklist, answers:list[Answer]) -> Score` with `Score(total:float|None, sections:dict[str,float|None], gross_error:bool, items:list[ScoreItem(criterion_id, normalized:float|None, effective_weight:float)])`.

- [ ] **Step 1: Failing tests** (hand-computed): (a) weights 60/40, scale 0-2, points 2/1 → total 80.0; (b) criterion 2 N/A → weight moves to criterion 1, total 100.0; (c) all N/A → `total is None`; (d) rounding digits/mode per checklist with an `x.5` case separating half_up vs half_even; (e) gross-error answer → `gross_error True`, total still computed; (f) section score uses only that section's applicable criteria; (g) points outside scale → `ValueError`.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** Implement `compute_score`: `normalized=(p-min)/(max-min)` (yesno → 0/1); `effective_weight=weight/Σ applicable weights`; total = Σ normalized×effective_weight×100, rounded per checklist (use `decimal`, not float `round`).
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** commit `feat: weighted scoring with N/A redistribution`.

### Task 4: LLM evaluator

**Files:**
- Create: `server/evaluator.py`, `tests/test_evaluator.py`

**Interfaces:**
- Consumes: `Record`, `Checklist`, `compute_score`.
- Produces: `models.Item(criterion_id, applicable, na_reason:str|None, answer:str, points:float|None, explanation:str, evidence_idx:list[int], checked_range:tuple[int,int]|None, gross_error:bool=False)`; `models.Evaluation(conversation_id, checklist_version:int, items:list[Item], score:Score, model:str, usage:Usage(prompt_tokens:int, completion_tokens:int))`; `evaluator.build_prompt(record, checklist) -> tuple[str,str]` (system, user; sync); `evaluator.parse_output(raw:str, record, checklist) -> list[Item]` (sync; raises `EvaluationError`); `async evaluator.evaluate(record, checklist, llm:LLM|None=None) -> Evaluation` where `LLM = Callable[[list[dict]], Awaitable[tuple[str, Usage]]]` (default: niquests `AsyncSession` call to OpenAI-compatible endpoint; injectable for tests).

- [ ] **Step 1: Failing async tests** with an async fake `llm`: valid JSON → Evaluation with score; prompt contains every criterion id and every turn as `[idx] speaker: text`; `evidence_idx` ≥ len(transcript) → `parse_output` raises; applicable item with empty `evidence_idx` and no `checked_range` → raises; `applicable=False` without `na_reason` → raises; invalid then valid → `evaluate` retries once and succeeds; two invalid → raises `EvaluationError`; markdown-fenced JSON accepted; empty transcript → no LLM call, all items N/A with reason, `score.total is None`.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** Implement. Prompt: score only `operator` turns; `bot`/`system` context only; explanation in the dialog's language; cite by `idx`; return strict JSON. Record `usage`.
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** commit `feat: LLM evaluator with evidence validation`.

### Task 5: Store and HTTP API

**Files:**
- Create: `server/store.py`, `server/routes.py`, `server/app.py`, `tests/test_api.py`

**Interfaces:**
- Consumes: Tasks 1-4.
- Produces (`uvicorn server.app:app --port 8787`; `app` is a `litestar.Litestar`; serves `web/dist` and `web/index.html` at `/`):
  - `GET /api/conversations?group_id=DEV` → `[{conversation_id, channel, language, turns, has_evaluation, final_total}]`
  - `GET /api/conversations/{id}` → Record
  - `GET|PUT /api/checklist`
  - `POST /api/evaluate {conversation_ids:[str], group_id}` → `{started:int}`; `GET /api/evaluate/status` → `{done:int, total:int, errors:{id:str}}`
  - `GET /api/evaluations/{conversation_id}` → `{evaluation, appeals:[Appeal], final:{items, score}}`
  - `POST /api/appeals {conversation_id, criterion_id, comment}` → `Appeal(id, conversation_id, criterion_id, comment, status:'open'|'resolved', created_at, decision:Decision|None)`
  - `POST /api/appeals/{id}/decision {action:'confirm'|'change', new_points?:float, new_applicable?:bool, reason:str}` → `{appeal, final}`; `final` = `compute_score` over the evaluation with accepted overrides; the stored evaluation is never mutated.
  - Dataset failure → 502 `{error}`.

- [ ] **Step 1: Failing async tests** (`AsyncTestClient(app)`, fake async `llm` injected via Litestar dependency override, dataset from `data/dev.json`): evaluate one dialog then GET returns score; PUT checklist bumps version and the next evaluation records the new `checklist_version` while the old keeps its version; appeal requires non-empty `comment` and known `criterion_id` (400 otherwise); decision `change` yields `final.score.total != evaluation.score.total`; decision without `reason` → 400; appeal on an N/A criterion accepted; dataset failure → 502.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** Implement. Persist under `data/store/` (`evaluations/<id>.json`, `appeals.json`). Batch evaluation runs as an `asyncio.gather` over dialogs bounded by an `asyncio.Semaphore` (default 4), per-dialog errors captured so one failure doesn't abort the batch; file I/O via `asyncio.to_thread`.
- [ ] **Step 4:** run → PASS; then `uvicorn server.app:app --port 8787` and `curl "localhost:8787/api/conversations?group_id=DEV"` returns 65 rows.
- [ ] **Step 5:** commit `feat: store and API`.

### Task 6: Frontend scaffold and checklist editor

**Files:**
- Create: `web/package.json`, `web/tsconfig.json`, `web/index.html`, `web/cqa.css`, `web/src/api.ts`, `web/src/app.ts`, `web/src/views/checklist.ts`

**Interfaces:**
- Produces: `api.ts` exports interfaces mirroring `server/models.py` (`Record`, `Turn`, `Criterion`, `Checklist`, `Item`, `Evaluation`, `Score`, `Appeal`) and `api<T>(path:string, init?:RequestInit): Promise<T>` (throws `Error` with server `error` text). `app.ts` registers hash routes `#/checklist`, `#/dialogs`, `#/dialog/<id>`, `#/review`. Every view module exports `render(root:HTMLElement): Promise<void>`. `npm run build` = `tsc` → `web/dist`.

- [ ] **Step 1:** Implement criteria list with inline edit of text, weight, type, scale min/max, N/A allowed + rule, add/delete criterion, Save (disabled while client-side validation fails; server errors shown).
- [ ] **Step 2: Smoke:** `npm run build`, open the page in a browser, change a weight, save, reload; value persists and `version` increments; screenshot.
- [ ] **Step 3:** commit `feat: frontend scaffold and checklist editor`.

### Task 7: Dialogs list and result card

**Files:**
- Create: `web/src/views/dialogs.ts`, `web/src/views/result.ts`, `web/src/logic/evidence.ts`, `web/tests/evidence.test.ts`

**Interfaces:**
- Consumes: `/api/conversations`, `/api/evaluate`, `/api/evaluations/{id}`.
- Produces: `evidence.turnAnchor(idx:number): string` → `"turn-<idx>"`; `evidence.fragment(transcript:Turn[], center:number, radius:number): Turn[]` (clamped at both ends); `evidence.rangeIdxs(range:[number,number]): number[]`.

- [ ] **Step 1: Failing vitest** for `fragment`: center 0 radius 3 on 10 turns → idx 0..3; center 9 → idx 6..9; empty transcript → `[]`; `turnAnchor(5)==='turn-5'`.
- [ ] **Step 2:** `npx vitest run` → FAIL; **Step 3:** implement `evidence.ts`; **Step 4:** PASS.
- [ ] **Step 5:** Dialogs view: filter by channel/language, multi-select + Evaluate with progress polling, per-row total. Result view: speaker-coloured transcript (`id=turnAnchor(idx)`), criteria table (answer, points, weight, explanation, evidence link scrolls/highlights turn; skipped action highlights checked range; N/A shows reason; total + section scores + gross-error badge; `null` total shows "not scorable"). Voice calls: `<audio controls>` with `audio_url`; timestamps verbatim.
- [ ] **Step 6: Smoke:** evaluate `p1-ru-001` and call `p4-ru-003` with the real model; evidence links highlight correct turns; screenshots.
- [ ] **Step 7:** commit `feat: dialogs list and result card`.

### Task 8: Appeal and reviewer flow

**Files:**
- Create: `web/src/views/review.ts`; modify `web/src/views/result.ts` (appeal button per criterion)

**Interfaces:**
- Consumes: `/api/appeals`, `/api/appeals/{id}/decision`, `evidence.fragment`.

- [ ] **Step 1:** Appeal dialog (criterion, comment) from the result card. `#/review`: open-appeal queue; each shows disputed criterion with original points, comment, `fragment(...,radius=3)` around evidence; confirm/change form (new points within scale or N/A toggle, required reason). Result card then shows original → decision → final total.
- [ ] **Step 2: Smoke:** appeal one criterion, change score, final total differs from original; reload persists; screenshot.
- [ ] **Step 3:** commit `feat: appeals and reviewer decisions`.

### Task 9: Batch run, README, cost note

**Files:**
- Create: `README.md`, `scripts/run_batch.py`

**Interfaces:**
- `python scripts/run_batch.py <group_id>`: loads group (refresh), evaluates all records, prints failures and token totals.

- [ ] **Step 1:** Implement script (`asyncio.run`) and README (env vars, install, `npm run build`, `uvicorn` command, control-set procedure, checklist editing, model name and approx cost per evaluation computed from recorded `usage`).
- [ ] **Step 2: Smoke:** `python scripts/run_batch.py DEV`; all 65 evaluated or failures listed; fill cost numbers in README.
- [ ] **Step 3:** commit `docs: README, batch runner`; push.

---

## Self-Review

- Coverage: checklist edit (T2, T6), RU/KZ/EN evaluate (T4), result with evidence/N/A/range (T4, T7), weighting/N/A/gross/rounding (T3), card/link/audio (T7), appeal (T8), decision/recompute (T5, T8), dataset + control set (T1, T9), README/cost (T9). Gap: real checklist content (T2 blocker).
- Types: `Item.evidence_idx` / `Turn.idx` consistent across T1/T4/T7; `Evaluation.score` is T3 `Score`; `final` in T5 reuses `compute_score`; TS interfaces in `api.ts` mirror `models.py` names.
- Proportion: bodies omitted deliberately.
