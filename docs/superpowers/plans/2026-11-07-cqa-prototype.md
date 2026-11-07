# CQA Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Conversation Quality Analytics prototype: configurable checklist, LLM scoring of operator dialogs with evidence, appeal and reviewer-decision flow with recomputed totals.

**Architecture:** Zero-build static frontend (plain HTML/CSS/ES modules, one self-contained component per screen so it can later be wrapped as a Dynamics 365 HTML web resource) talking JSON to a small Node server. Server owns dataset fetch, checklist storage, LLM evaluation and appeals; scoring math is a pure module with no I/O, driven entirely by checklist config. Storage is JSON files under `data/store/`.

**Tech Stack:** Node 24 (ESM, `node:test`, `node:http`, global `fetch`; zero npm deps), vanilla JS frontend, OpenAI-compatible chat-completions API configured by env (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`).

**Spec:** `docs/CQA_Hackathon_Student_Guide.md` (task guide). The eight-criteria checklist PDF is a separate organizer file that is **not in the repo yet** (see Task 2 blocker).

## Global Constraints

- Frontend: HTML, CSS, JavaScript only; structure must be adaptable to a Dynamics 365 HTML component (no framework build, no global CSS leakage: scope styles under a root `.cqa` class).
- No login/registration.
- Languages RU, KZ, EN must be supported by evaluation; bot and system turns are context only (never scored as operator behaviour).
- Speakers: `client`, `operator`, `bot`, `system`. Preserve original timestamps verbatim (chat `MM:SS`; call ISO 8601 with offset).
- Dataset API: GET with `group_id`; response `{error, isSuccess, data:{dataset_group_id,total_records,records[]}}`; record `{conversation_id, channel ("agent chat"|"voice call"), language ("RU"|"KZ"|"EN"), transcript[{timestamp,speaker,text}], audio_url|null}`. DEV = 65 records (60 chat, 5 calls; the guide says 35 RU / 15 KZ / 15 EN, actual data is 35 RU incl. 5 calls).
- Per criterion output: answer, points, weight, explanation, evidence turn. Skipped action: state the checked transcript range. N/A: state the reason.
- Weighted scale scores; N/A redistributes weight over applicable criteria; gross error flagged separately; rounding rules taken from the checklist PDF.
- Appeal: pick criterion + comment; reviewer sees disputed score, comment, dialog fragment; confirms or changes with a reason; total recomputed; card keeps original, decision, final.
- Checklist edits (add/change criterion text, weight, answer type, N/A flag, numeric scale) saved via UI and applied to dialogs at evaluation time. Organizers will swap one criterion at the check.
- Control set: opens at +23h, stop-code commit at +24h; README with run steps; repo is public-by-submission (send link early). Paid-model use requires stating model name and approx cost per evaluation (record in README).
- CORS: dataset is fetched by the server, never the browser.
- 5-minute demo path: list/dialog -> evaluation + evidence jump + N/A + total -> appeal + decision + new total -> edit criterion + re-apply.

## Review Focus

- Transcript empty or operator never speaks → all operator criteria N/A with reason, total not NaN/divide-by-zero.
- LLM returns evidence index outside the transcript or a quote not in that turn → rejected/retried, never rendered as a working link.
- All criteria N/A or applicable weights sum to 0 → total `null` with explicit "not scorable" state.
- Criterion removed/replaced after evaluation exists → old results stay viewable (frozen with their checklist version), re-evaluation uses the new one.
- Appeal on an N/A criterion or on a gross-error flag → allowed, and reviewer change recomputes correctly.
- KZ text or mixed RU/KZ/EN turns, and voice-call ISO timestamps → shown unmodified, evidence anchors still resolve (anchor by turn index, not timestamp).
- Control-set group_id returns `isSuccess:false` or non-JSON → clear UI error, previous data intact.

---

## File Structure

```
server/
  index.js          # http server, routing, static files
  dataset.js        # fetch/cache/normalize dataset
  checklist.js      # schema validation, load/save, versioning
  scoring.js        # pure: total, section scores, N/A redistribution, rounding
  evaluator.js      # prompt build, LLM call, response validation
  store.js          # JSON-file persistence (evaluations, appeals)
  api.js            # route handlers
web/
  index.html
  cqa.css
  app.js            # router + shared state
  views/checklist.js
  views/dialogs.js
  views/result.js
  views/review.js
data/dev.json       # fetched DEV set (already present)
data/checklist.default.json
test/*.test.js
README.md
```

---

### Task 1: Dataset module

**Files:**
- Create: `server/dataset.js`, `test/dataset.test.js`

**Interfaces:**
- Produces: `normalizeResponse(json: object): Record[]` (throws `Error` on `isSuccess:false`/bad shape; each transcript turn gets `idx: number` = array position); `async loadDataset(groupId: string, {refresh?: boolean}): Promise<Record[]>` (caches to `data/<groupId>.json`, env `DATASET_URL` is the base GET URL without `group_id`).

- [ ] **Step 1: Failing tests** in `test/dataset.test.js` using `data/dev.json`: `normalizeResponse` returns 65 records; every turn has `idx` equal to its position; 5 records have `channel==='voice call'` with non-null `audio_url`; `normalizeResponse({isSuccess:false,error:'boom'})` throws `/boom/`; timestamps unchanged vs raw.
- [ ] **Step 2:** `node --test test/dataset.test.js` → FAIL (module missing).
- [ ] **Step 3:** Implement as above. `loadDataset` reads cache unless `refresh`; on fetch failure with cache present, throw but leave cache intact.
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** `git add server/dataset.js test/dataset.test.js && git commit -m "feat: dataset loader"`

### Task 2: Checklist schema and default config

**Blocker:** needs the organizer checklist PDF (eight criteria, weights, scales, N/A rules, rounding). Obtain it before Step 3; the implementer must transcribe it verbatim into `data/checklist.default.json` and must not invent criteria. (`Data 2 (1) 1.pdf` in Downloads was checked: it is a Freedom Holding company brochure, not the checklist.)

**Files:**
- Create: `server/checklist.js`, `data/checklist.default.json`, `test/checklist.test.js`

**Interfaces:**
- Produces: type `Checklist = {version:number, rounding:{digits:number, mode:'half_up'|'half_even'}, sections:[{id,name}], criteria:[Criterion]}`; `Criterion = {id:string, section?:string, text:string, weight:number, type:'scale'|'yesno', scale?:{min:number,max:number}, na_allowed:boolean, na_rule?:string, gross_error?:boolean}`; `validateChecklist(c): {ok:boolean, errors:string[]}`; `loadChecklist(): Checklist`; `saveChecklist(c): Checklist` (bumps `version`, archives previous at `data/store/checklists/v<N>.json`); `getChecklistVersion(n): Checklist`.

- [ ] **Step 1: Failing tests:** default file validates `ok`; has 8 criteria; duplicate `id` → error; `type:'scale'` without `scale` or `min>=max` → error; negative weight → error; `saveChecklist` twice yields versions N, N+1 and `getChecklistVersion(N)` returns the old content.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** Implement. Gross-error criteria carry `gross_error:true` and are excluded from weighted sum (flagged separately), unless the PDF says otherwise.
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** commit `feat: checklist schema and default config`.

### Task 3: Scoring math

**Files:**
- Create: `server/scoring.js`, `test/scoring.test.js`

**Interfaces:**
- Consumes: `Checklist` from Task 2.
- Produces: `type Answer = {criterion_id, applicable:boolean, points:number|null, gross_error?:boolean}`; `computeScore(checklist, answers: Answer[]): {total:number|null, sections:{[id]:number|null}, gross_error:boolean, items:[{criterion_id, normalized:number|null, effective_weight:number}]}`.

- [ ] **Step 1: Failing tests** with hand-computed numbers: (a) 2 criteria weights 60/40, scale 0-2, points 2/1 → total 80 on 0-100; (b) criterion 2 N/A → its weight moves to criterion 1, total 100; (c) all N/A → `total:null`; (d) rounding digits/mode from checklist (case `x.5` distinguishing half_up vs half_even); (e) gross error answer → `gross_error:true`, total still computed; (f) section scores use only that section's applicable criteria; (g) points outside scale → throws.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** Implement `computeScore`: `normalized = (points-min)/(max-min)` (yesno → 0/1); `effective_weight = weight / Σ applicable weights` ; total ×100 rounded per checklist.
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** commit `feat: weighted scoring with N/A redistribution`.

### Task 4: LLM evaluator

**Files:**
- Create: `server/evaluator.js`, `test/evaluator.test.js`

**Interfaces:**
- Consumes: `Record` (Task 1), `Checklist` (Task 2), `computeScore` (Task 3).
- Produces: `buildPrompt(record, checklist): {system:string, user:string}`; `parseModelOutput(raw:string, record, checklist): {items: Item[]}` where `Item = {criterion_id, applicable, na_reason?, answer, points, explanation, evidence_idx:number[], checked_range?:[number,number], gross_error?:boolean}` (throws on invalid); `async evaluate(record, checklist, {llm}={}): Promise<Evaluation>` with `Evaluation = {conversation_id, checklist_version, items:Item[], score:ReturnType<computeScore>, model:string, usage:{prompt_tokens,completion_tokens}}`; `llm(messages): Promise<{text,usage}>` default = OpenAI-compatible fetch, injectable for tests.

- [ ] **Step 1: Failing tests** with a fake `llm`: valid JSON → Evaluation with score; prompt contains every criterion id and each turn labelled `[idx] speaker:`; output with `evidence_idx` ≥ transcript length → parse throws; applicable item with empty `evidence_idx` and no `checked_range` → throws; `applicable:false` without `na_reason` → throws; first call invalid then valid → `evaluate` retries once and succeeds; two invalid → rejects; markdown-fenced JSON accepted.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** Implement. Prompt instructs: score only `operator` turns; `bot`/`system` context only; answer explanation in the dialog's language; cite turns by `idx`. Use JSON-mode if the endpoint supports it, otherwise strip fences. Record `usage` for the cost note.
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** commit `feat: LLM evaluator with evidence validation`.

### Task 5: Store and HTTP API

**Files:**
- Create: `server/store.js`, `server/api.js`, `server/index.js`, `test/api.test.js`

**Interfaces:**
- Consumes: Tasks 1-4.
- Produces (JSON over HTTP, port `PORT||8787`, also serves `web/`):
  - `GET /api/conversations?group_id=DEV` → `[{conversation_id, channel, language, turns, has_evaluation, final_total}]`
  - `GET /api/conversations/:id` → record
  - `GET|PUT /api/checklist`
  - `POST /api/evaluate {conversation_ids:string[], group_id}` → `{started:n}`; progress `GET /api/evaluate/status`
  - `GET /api/evaluations/:conversation_id` → `{evaluation, appeals:[Appeal]}`
  - `POST /api/appeals {conversation_id, criterion_id, comment}` → `Appeal = {id, conversation_id, criterion_id, comment, status:'open'|'resolved', created_at, decision?:{action:'confirm'|'change', new_points?, new_applicable?, reason, decided_at}}`
  - `POST /api/appeals/:id/decision {action, new_points?, new_applicable?, reason}` → `{appeal, final:{items, score}}` where `final` = `computeScore` over the evaluation with accepted overrides applied; the evaluation itself stays unmodified.

- [ ] **Step 1: Failing tests** (start server on ephemeral port, injected fake `llm` and `data/dev.json` cache): evaluate one dialog then GET evaluation returns score; PUT checklist bumps version and next evaluation records new `checklist_version` while old evaluation keeps the old one; appeal creation requires non-empty `comment` and known `criterion_id` (400 otherwise); decision `change` with reason recomputes `final.score.total` differently from original; decision without `reason` → 400; appeal on an N/A criterion accepted; dataset fetch failure → 502 with `{error}`.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** Implement. Persist under `data/store/` (`evaluations/<id>.json`, `appeals.json`). Evaluation concurrency capped (default 4) with per-dialog error capture so one failure doesn't abort the batch.
- [ ] **Step 4:** run → PASS; also `node server/index.js` and `curl localhost:8787/api/conversations?group_id=DEV` returns 65 rows.
- [ ] **Step 5:** commit `feat: store and API`.

### Task 6: Checklist editor UI

**Files:**
- Create: `web/index.html`, `web/cqa.css`, `web/app.js`, `web/views/checklist.js`

**Interfaces:**
- Consumes: `/api/checklist`.
- Produces: `app.js` exports `api(path, opts)` and `mount(viewName)` used by later views; each view module exports `render(root: HTMLElement): Promise<void>`; all markup under `.cqa`.

- [ ] **Step 1:** Implement list of criteria with inline edit of text, weight, type, scale min/max, N/A allowed + rule, add and delete criterion, Save button (disabled while `validateChecklist`-equivalent client check fails; show server errors).
- [ ] **Step 2: Smoke:** open the page via `browser`, change one criterion weight, save, reload; value persists and `version` increments; screenshot.
- [ ] **Step 3:** commit `feat: checklist editor`.

### Task 7: Dialogs list and result card

**Files:**
- Create: `web/views/dialogs.js`, `web/views/result.js`

**Interfaces:**
- Consumes: `/api/conversations`, `/api/evaluate`, `/api/evaluations/:id`.
- Produces: `#/dialog/<id>` route.

- [ ] **Step 1:** Dialogs view: filter by channel/language, multi-select + "Evaluate" with progress, per-row total. Result view: transcript pane (speaker-coloured, `id="turn-<idx>"`) and criteria table (answer, points, weight, explanation, evidence link → scrolls/highlights `turn-<idx>`; skipped action shows checked range highlight; N/A shows reason; totals + section scores + gross-error badge). Voice calls: `<audio controls src=audio_url>`; evidence link also seeks nothing but shows the turn (timestamps shown verbatim).
- [ ] **Step 2: Smoke:** evaluate `p1-ru-001` and `p4-ru-003` (call) with the real model; evidence link highlights correct turn; N/A example visible; screenshot both.
- [ ] **Step 3:** commit `feat: dialogs list and result card`.

### Task 8: Appeal and reviewer flow

**Files:**
- Create: `web/views/review.js`; modify `web/views/result.js` (appeal button per criterion)

**Interfaces:**
- Consumes: `/api/appeals`, `/api/appeals/:id/decision`; route `#/review`.

- [ ] **Step 1:** Appeal dialog (criterion, comment) from result card. Review view: open-appeals queue; each shows disputed criterion with original points, comment, ±3-turn fragment around the evidence; confirm/change form (new points within scale or toggle N/A, required reason). After decision, card shows original → decision → final total.
- [ ] **Step 2: Smoke:** appeal one criterion, change score, see final total differ from original; reload persists.
- [ ] **Step 3:** commit `feat: appeals and reviewer decisions`.

### Task 9: Batch run, README, cost note

**Files:**
- Create: `README.md`, `scripts/run-batch.js`

**Interfaces:**
- Consumes: `/api/evaluate`; `scripts/run-batch.js <group_id>` loads the group (refresh) and evaluates all records, printing failures and token totals.

- [ ] **Step 1:** Implement script and README (env vars, `node server/index.js`, how to run control set, how to edit checklist, model name and approx cost per evaluation computed from recorded `usage`).
- [ ] **Step 2: Smoke:** run `node scripts/run-batch.js DEV`; all 65 evaluated or failures listed; cost numbers filled in README.
- [ ] **Step 3:** commit `docs: README, batch runner`; push.

---

## Self-Review

- Coverage: checklist edit (T2, T6), evaluate RU/KZ/EN (T4), result display with evidence/N/A/range (T4, T7), weighting/N/A/gross/rounding (T3), card/link/audio (T7), appeal (T8), decision/recompute (T5, T8), data API + control set (T1, T9), README/cost (T9). Gap: the real checklist content (T2 blocker).
- Types: `Item.evidence_idx` and `turn.idx` used consistently in T1/T4/T7; `Evaluation.score` is `computeScore` output (T3) and `final` in T5 reuses it.
- Proportion: bodies omitted deliberately; implementer decides internals.
