# Demo script (≈7 min + questions, 8–10 min total)

The organizers want the live product to be the presentation, with the full cycle shown in order (#3398): checklist setup → getting dialogs → evaluation → viewing results → appeal → manual re-evaluation. A couple of slides frame it (`docs/pitch.md`, slides 1–3). Everything below is clicked live.

## Before the pitch

1. Start the app: `.venv/Scripts/python.exe -m uvicorn server.app:app --port 8787`, then open `http://localhost:8787/#/dialogs/DEV`.
2. Check that `data/store` holds the DEV results: the list should show totals for all 65 dialogs. If it doesn't, run `python scripts/run_batch.py DEV`, which takes 7–8.5 min on the 4-replica gemma (420 s and 507 s measured).
3. Check the model with `python scripts/preflight.py`. If gemma goes down, each dialog falls back along `FALLBACK_PROFILE`, and the card shows which model scored it.
4. Open a spare tab on the control group, `#/dialogs/<CONTROL_GROUP>`: «this is our raw control output, with no manual edits».
5. The checklist edit in step 1 creates a new version of `chat`. That is fine after the control run. Before any further `--submit` run, restore the default with `--reset-defaults`.
6. The Kazakh call `1234` is already in the group `UPLOADS` (`up-call-002`, uploaded on this machine; its audio is gitignored). Keep it for step 6 in case live ASR is slow.
7. Type the appeal comment and the reviewer's reason for step 5 in a notepad beforehand: paste, don't type live.

**Pacing.** Never wait on a spinner. If you upload a recording live, start it at the beginning of step 4 and come back to it in step 6. Any live step not done in ~60 s: say what it is doing, move on, return later. When showing the upload, say the one line that matters: «датасет помечает этот звонок RU, а система по звуку определила KZ».

## 0. Frame (30 s, slide 1)

One sentence: we score every operator chat and call against a versioned checklist, with a reason and the exact turn for each verdict, on our own GPU by default, in about 30 s per dialog (per-criterion mode). Accuracy is about 0.93 on DEV (0.931–0.939 in two runs), and we expect ≈ 0.91–0.93 on unseen chats. Our labels match five other teams' published DEV labels at 94.6–99.3%; a sixth, manual set agrees 86.7% (it reads C7 «прощание без итога» as «Да»), and the one fully blind manual set (14 dialogs) is lower, at 84% (`bench/gold/README.md`).

## 1. Checklist setup (60 s): «добавить критерий, изменить, поменять вес»

**Чек-листы** → `chat` → edit:
- add «Предупреждение об ожидании»: answer type «Да / Нет», tick «N/A допустимо» and give the N/A condition («оператор не ставил клиента на ожидание»), weight 5;
- change the wording of an existing criterion;
- change the weight of c07 «Завершение» from 5 to 10, and lower c05 from 15 to 5 so the weights still sum to 100 (the editor shows «Σ весов: … · должно быть 100» until they do).

Save. A new version (v2) is created, and v1 stays readable; the page offers «К диалогам для переоценки». Rules and edge cases live in the checklist notes, not in the code, so QA changes the rules without a developer.

## 2. Getting dialogs (30 s)

**Диалоги** → group DEV, loaded from the organizers' API. Filters: channel, language (RU/KZ/EN) and «Только с грубыми ошибками». Point out the 8 gross-error dialogs, including the KZ chat p1-kz-015, where an account restriction was revealed before identification (#3106).

## 3. Evaluation (45 s)

Select 2 dialogs → **Оценить выбранные**: progress is live; the batch finishes in about 35–70 s (rehearsal: 3 chats took 69 s), so start it and talk over it. Dialogs evaluated now use the new checklist v2, so their totals differ from the morning run. This is also the step the jury may ask to see on their own transcripts (#3327).

## 4. Viewing results (90 s): «результаты конкретного диалога, почему ошибка»

1. **p1-ru-022**, gross error: the operator offers to take the money personally, «в обход компании». Open the c08 row and its evidence: the highlighted turn. The flag is reported separately and does not zero the total (31.25).
2. **p1-ru-029**: the score ring, points as `x / weight`, and «Почему снижена оценка» with «Перейти к фрагменту». Two N/A: c02 «Выявление потребности» (the client gave everything up front) and c03 «Идентификация» (no account data was disclosed); each reason is shown, and the weight is redistributed. Mention that this dialog also carries the gross-error flag (total 46.15), so the badge on the card is expected; it is one of the 8.
3. «Факты диалога»: first operator response against the 3-minute SLA, the longest client wait, masked data. It is computed from the transcript without an LLM.
4. **Аналитика** (10 s): mean total, pass rate per criterion, by language and channel.

## 5. Appeal and manual re-evaluation (90 s)

1. On p1-ru-029: «Оспорить оценку» on c06, with a comment.
2. **Апелляции** → the appeal is in the queue → «Изменить»: pick the new value (c06: 10), fill «Проверяющий» and the reason → the final total is recomputed (rehearsal: 46.15 → 69.23, «Исходный итог: 46,15»). The raw and the final score are both kept, and history shows who changed what. Now click «Выгрузить дело» on this evaluation: the ZIP holds the appeal and the decision.
3. Manual re-evaluation under the new rules: open **p1-ru-028** (the operator says «Сейчас проверю путь» and later «Спасибо за ожидание») → «Переоценить по текущему чек-листу» (~15 s). The new criterion «Предупреждение об ожидании» gets a verdict with evidence, and «Сравнение оценок» shows v1 against v2 with only the changed criteria expanded. Do not re-evaluate p1-ru-029 after its appeal: a re-evaluation is a new evaluation and does not inherit appeal decisions, and there the new criterion is N/A.

## 6. Calls: our approach (60 s), per #3397 «почему это важно для бизнеса»

Open the call **p4-ru-003**. The organizers' transcript is unusable for QA («идентификацию успешно проеданная»), and a wrong transcript means a wrong score. In the «Транскрипт» switch:
- the card opens on «Организатор (API)»: click **FreedomSpeech** (Freedom's own STT) and the «проеданная» line is gone;
- 9 benchmarked models, each with a quality badge;
- «Вставить свой транскрипт».

«Распознать заново» on T-one or GigaAM-v3 runs on our H200: ASR alone takes 19–30 s on average, 7–57 s per call (`bench/asr/summary.md`), plus role assignment and masking by the LLM. Do not re-transcribe live with Gemini or WhisperX: their slowest calls took 110 s and 163 s (per-call maxima; means 71 s and 60 s). Roles are assigned and personal data masked by our own model by default, so customer data stays on our GPU. Click an evidence turn and the audio seeks to that moment.

**Your own recording.** «Диалоги» → **Загрузить звонок или чат** → pick an audio file (e.g. the Kazakh call `1234`, which the dataset labels RU), language «определить автоматически», model WhisperX (H200) → «Распознать и добавить». It takes about 1–1.5 min on WhisperX for 3 minutes of audio: the language comes out KZ, roles are assigned, personal data masked. Then «Оценить по этому транскрипту» (~70 s for this call; `up-call-002` is already evaluated on the demo machine: 84.62; a rehearsal re-run gave 88.24, so do not quote the number as fixed) → the usual result card, appeal and «Выгрузить дело». A pasted chat goes the same way in seconds. Everything lands in the group `UPLOADS`.

## If they ask for laptop access

Hand over the dialogs tab. Everything above is safe to click; live evaluation of one DEV dialog takes about 30–35 s.

## If they ask

- **C7 «Завершение».** We read the checklist literally: a summary or an offer of further help, **and** a goodbye. A goodbye alone («Пожалуйста. Хорошего дня!») is «Нет»; the organizers' reply «Внимательно перечитайте чеклист по данному пункту» (#2814) most likely answers this very question (#2686, see `docs/organizer-answers.md`). Teams split on it. In our submitted DEV output C7 is «Нет» in 50 of 60 chats, and in 32 of them it is the only criterion that loses points (`results/dev/results.json`). If the reference reads it more softly, we lose up to most of one criterion out of eight. The rule lives in the checklist's notes and can be edited in the UI in a minute; the prompt and the scoring do not change.
- **Why not a fine-tuned model.** 65 DEV dialogs, model-made labels, no held-out set; most remaining misses are gold ties. A judge tuned to 8 fixed criteria would handle «add a criterion» worse.
- **Calls accuracy.** Not claimed: external call labels agree 69–79% and CER is agreement with FreedomSpeech, not accuracy.
- **Reproducibility.** Two full DEV runs on the final rules agree on 514 of 520 verdicts (98.8%) and on all 8 gross errors. The same model at temperature 0 can still flip a borderline cell, and a call's score also moves with its ASR transcript (the uploaded Kazakh call scored 88.24 and 84.62 in two runs).
