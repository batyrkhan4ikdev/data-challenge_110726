# Demo script (5 minutes)

The demo is the live product (#2991): slides are optional, the UI is clicked in real time. Each block answers one of the organizers' demo requests.

## Before the pitch

1. Start the app: `.venv/Scripts/python.exe -m uvicorn server.app:app --port 8787`, then open `http://localhost:8787/#/dialogs/DEV`.
2. Check that `data/store` holds the DEV results; the list should show totals for all 65 dialogs. If it doesn't, run `python scripts/run_batch.py DEV --refresh`, which takes about 7 minutes.
3. Check the model endpoint with `curl --ssl-no-revoke https://hk-gemma.sek.su/health`. If it is down, live evaluation still works on `aigw-sonnet`: pick that profile in the batch dialog.
4. Have a spare tab open on the control group, `#/dialogs/<CONTROL_GROUP>`.

## 1. What it is (30 s)

Freedom Broker CQA scores operator chats and calls (RU/KZ/EN) against a versioned checklist. Each verdict comes with a justification, evidence turns and N/A handling. The total is weighted, and gross errors are flagged separately. Operators can appeal a verdict, and a reviewer decides. The model is self-hosted (gemma-4 31B on an H200), costing about $0.002 per dialog, with a cloud fallback. Tell the jury which result we're presenting: the control set is raw system output, with no manual edits.

## 2. Gross errors and why (60 s): «Покажите все диалоги с грубыми ошибками»

1. **Диалоги** → filter «Грубые ошибки». 8 DEV dialogs are flagged, including the KZ chat p1-kz-015, where an account restriction was revealed before identification (#3106).
2. Open **p1-ru-022**. The operator offers to have the money sent to them personally, «в обход компании». The c08 row shows the explanation; click its evidence to jump to the highlighted turn.
3. Open **p1-en-013**. The flagged quote is «I charge for private advice», a paid private consultation; the same pattern appears in RU in p1-ru-023 and in KZ in p1-kz-013.
4. Point out that the flag does not zero the total. Totals are 31.25 and 69.23, as the organizers' rules require; the flag is reported separately.

## 3. One dialog, fully explained (60 s): «результаты оценки конкретного диалога»

1. Open **p1-ru-029** (rude phrase, total 46.15). Show:
   - the score ring;
   - per-criterion points as `x / weight`;
   - «Почему снижена оценка», which lists each lost criterion with one line of reasoning and «Перейти к фрагменту».
2. Show one N/A. c03 «Идентификация» is N/A when the request needs no account data. The N/A reason is shown, and the weight is redistributed, so the maximum is still 100.
3. Open the call **p4-ru-003**. Click an evidence turn and the audio seeks to that moment. Turns are numbered from 1, the same way as in `results.json`.

## 4. Appeal and review (60 s): «как оператор может отправить результат на апелляцию»

1. On p1-ru-029, click «Оспорить оценку» on c06 «Управление диалогом». Enter a comment, for example «Оператор ответил в пределах 3 минут», and submit.
2. Open **Апелляции**. The appeal is in the queue. Choose «Изменить», set a new value with a reason, and decide.
3. Back on the card, the final total is recomputed. Both the raw and the final score are kept, and history shows who changed what.

## 5. Checklist editing (60 s): «добавить новый критерий, изменить существующий, поменять вес»

1. **Чек-листы** → `chat` → edit:
   - add a criterion, for example «Предупреждение об ожидании», yes/no/N/A, weight 5;
   - change the wording of an existing one;
   - change the weight of c07 «Завершение» from 5 to 10.
2. Save. A new version (v2) is created; v1 stays readable in the version history.
3. Open any dialog and click «Переоценить по текущему чек-листу». The new criterion gets a verdict with evidence, and the total is recomputed under v2. History shows both versions.

## 6. Analytics and close (30 s)

**Аналитика** shows, for the group:
- mean total and gross-error count;
- the per-criterion pass rate and N/A share;
- breakdowns by channel and language;
- the score distribution.

Close on reproducibility. The control results are produced by a single command: `python scripts/run_batch.py <CONTROL_GROUP> --refresh --submit prod` writes and validates `results/prod/results.json`.

## If they ask for laptop access

Hand over the browser tab with the dialogs list. The safe things to click are all of the above; live evaluation of any DEV dialog takes about 6 s.
