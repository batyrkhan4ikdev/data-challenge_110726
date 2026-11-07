# Demo script (≈7 min + questions, 8–10 min total)

The organizers want the live product to be the presentation, with the full cycle shown in order (#3398): checklist setup → getting dialogs → evaluation → viewing results → appeal → manual re-evaluation. A couple of slides frame it (`docs/pitch.md`, slides 1–3). Everything below is clicked live.

## Before the pitch

1. Start the app: `.venv/Scripts/python.exe -m uvicorn server.app:app --port 8787`, then open `http://localhost:8787/#/dialogs/DEV`.
2. Check that `data/store` holds the DEV results: the list should show totals for all 65 dialogs. If it doesn't, run `python scripts/run_batch.py DEV`, which takes 7–8.5 min on the 4-replica gemma (420 s and 507 s measured).
3. Check the model with `python scripts/preflight.py`. hk-gemma and the ASR hub stay up until 17:00. If gemma goes down, each dialog falls back along `FALLBACK_PROFILE`, and the card shows which model scored it.
4. Open a spare tab on the control group, `#/dialogs/<CONTROL_GROUP>`: «this is our raw control output, with no manual edits».
5. The checklist edit in step 1 creates a new version of `chat`. That is fine after the control run. Before any further `--submit` run, restore the default with `--reset-defaults`.

## 0. Frame (30 s, slide 1)

One sentence: we score every operator chat and call against a versioned checklist, with a reason and the exact turn for each verdict, on our own GPU by default, in about 30 s per dialog (per-criterion mode). Accuracy is about 0.93 against labels that match five other teams' published DEV labels at 94.6–99.3% (the one fully blind manual set, 14 dialogs, is lower at 84%; `bench/gold/README.md`).

## 1. Checklist setup (60 s): «добавить критерий, изменить, поменять вес»

**Чек-листы** → `chat` → edit:
- add «Предупреждение об ожидании», yes/no/N/A, weight 5;
- change the wording of an existing criterion;
- change the weight of c07 «Завершение» from 5 to 10.

Save. A new version is created, and the previous one stays readable. Rules and edge cases live in the checklist notes, not in the code, so QA changes the rules without a developer.

## 2. Getting dialogs (30 s)

**Диалоги** → group DEV, loaded from the organizers' API. Filters: channel, language (RU/KZ/EN) and «Грубые ошибки». Point out the 8 gross-error dialogs, including the KZ chat p1-kz-015, where an account restriction was revealed before identification (#3106).

## 3. Evaluation (45 s)

Select 2–3 dialogs → **Оценить выбранные**: progress is live, about 30 s per chat. This is also the step the jury may ask to see on their own transcripts (#3327).

## 4. Viewing results (90 s): «результаты конкретного диалога, почему ошибка»

1. **p1-ru-022**, gross error: the operator offers to take the money personally, «в обход компании». Open the c08 row and its evidence: the highlighted turn. The flag is reported separately and does not zero the total (31.25).
2. **p1-ru-029**: the score ring, points as `x / weight`, and «Почему снижена оценка» with «Перейти к фрагменту». One N/A: c03 «Идентификация» is N/A when no account data was disclosed, the reason is shown, and the weight is redistributed.
3. «Факты диалога»: first operator response against the 3-minute SLA, the longest client wait, masked data. It is computed from the transcript without an LLM.
4. **Аналитика** (10 s): mean total, pass rate per criterion, by language and channel.

## 5. Appeal and manual re-evaluation (90 s)

1. On p1-ru-029: «Оспорить оценку» on c06, with a comment.
2. **Апелляции** → the appeal is in the queue → «Изменить», a new value and a reason → the final total is recomputed. The raw and the final score are both kept, and history shows who changed what.
3. Manual re-evaluation under the new rules: open any dialog → «Переоценить по текущему чек-листу». The new criterion from step 1 gets a verdict with evidence, and the total is computed under the new version. History shows the old and the new version.

## 6. Calls: our approach (60 s), per #3397 «почему это важно для бизнеса»

Open the call **p4-ru-003**. The organizers' transcript is unusable for QA («идентификацию успешно проеданная»), and a wrong transcript means a wrong score. In the «Транскрипт» switch:
- **FreedomSpeech** (Freedom's own STT) is the default;
- 8 benchmarked models, each with a quality badge;
- «Вставить свой транскрипт».

«Распознать заново» on T-one or GigaAM-v3 runs on our H200 in seconds (about 40 s). Do not re-transcribe live with Gemini or WhisperX: they take 110–163 s per call (`bench/asr/summary.md`). Roles are assigned and personal data masked by our own model by default, so customer data stays on our GPU. Click an evidence turn and the audio seeks to that moment.

## If they ask for laptop access

Hand over the dialogs tab. Everything above is safe to click; live evaluation of any DEV dialog takes about 30 s.
