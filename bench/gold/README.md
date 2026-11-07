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
