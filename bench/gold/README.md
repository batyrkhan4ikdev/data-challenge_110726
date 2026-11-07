# Разметка gold-набора

У каждого разметчика 8 диалогов. Файл с назначениями: `bench/gold/assignments.json`.

1. Откройте свой CSV `bench/gold/labels.<ваш логин>.csv` и транскрипты в `bench/gold/transcripts/<id>.md`.
2. Прочитайте чек-лист `docs/CQA_Chat_Quality_Checklist.md`; для звонков ещё `data/checklists/call.default.json`; и `docs/organizer-answers.md`.
3. В колонке `gold_verdict` укажите ровно одно значение из колонки `allowed` (например `yes`, `no`, `na` или ступень шкалы `0`/`5`/`10`).
4. В `gold_evidence` укажите номера реплик (`[N]` в транскрипте), через пробел.
5. Не правьте колонки `prefill_*`.
6. Судите независимо: prefill — только подсказка и может ошибаться.
7. Сомнения пишите в `note`.
8. Когда всё заполнено, запустите `python -m bench.run --set gold --profiles <профили> ...`.

Файл открывается в Excel (UTF-8 с BOM); сохраняйте его как CSV UTF-8. Пока `gold_verdict` не пуст, `python -m bench.prefill` отказывается перезаписывать файл.

`labels.consensus.csv` — gold для 5 диалогов, собранный из 4 способов модельной разметки и ручной проверки; как он получен и какие оценки спорные, см. `calibration/README.md`. `load_gold` читает все `labels.*.csv` по алфавиту, и при повторе того же диалога побеждает последний файл. `p1-en-011` и `p4-ru-005` уже есть в `labels.consensus.csv`, поэтому в своём CSV оставьте их `gold_verdict` пустыми или правьте спорные оценки прямо в `labels.consensus.csv`.
