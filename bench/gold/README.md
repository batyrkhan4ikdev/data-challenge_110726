# Разметка gold-набора

У каждого разметчика 8 диалогов. Файл с назначениями: `bench/gold/assignments.json`.

1. Откройте свой CSV `bench/gold/labels.<ваш логин>.csv` и транскрипты в `bench/gold/transcripts/<id>.md`.
2. Прочитайте чек-лист `docs/CQA_Chat_Quality_Checklist.md`; для звонков ещё `data/checklists/call.default.json`; и `docs/internal/organizer-answers.md`. Для звонков (`p4-*`) читайте транскрипт FreedomSpeech `bench/gold/transcripts/freedomspeech/<id>.md` — он точнее ASR фикстуры; номера реплик для `gold_evidence` берите из `transcripts/<id>.md`.
3. В колонке `gold_verdict` укажите ровно одно значение из колонки `allowed` (например `yes`, `no`, `na` или ступень шкалы `0`/`5`/`10`).
4. В `gold_evidence` укажите номера реплик (`[N]` в транскрипте), через пробел.
5. Не правьте колонки `prefill_*`.
6. Судите независимо: prefill — только подсказка и может ошибаться.
7. Сомнения пишите в `note`.
8. Когда всё заполнено, запустите `python -m bench.run --set gold --profiles <профили> ...`.

Файл открывается в Excel (UTF-8 с BOM); сохраняйте его как CSV UTF-8. Пока `gold_verdict` не пуст, `python -m bench.prefill` отказывается перезаписывать файл.

`labels.consensus.csv` — модельный gold для всех 65 DEV-диалогов, собранный из 4 способов разметки (GPT-6 Astra и Claude Opus 5.5 xhigh, пачками и по одному диалогу): раунд 1 (5 диалогов, с ручной проверкой `p1-ru-007`) — `calibration/README.md`, раунд 2 (60 диалогов) — `calibration/round2/README.md`. Ручные строки из `labels.<login>.csv` перекрывают consensus построчно; `python -m bench.run --set gold --gold human` использует только ручные.

## Сверка с разметкой других команд (2026-11-07)

Эталона организаторов нет (#2966), поэтому наш gold и вывод модели сверены с разметкой DEV, которую другие команды выложили в своих публичных репозиториях. Чистые чаты (60 × 8 клеток), клетки, помеченные авторами как спорные (`uncertain`), исключены.

| набор (репо, файл) | как размечен | vs наш gold | vs gemma (`results/dev`) |
|---|---|---|---|
| `alibek2007/cqa-freedom-hackathon` `eval/dev_reference.json` | вручную | 96.4% | 94.7% |
| `dosmuhamedkemelbekov-ui` `gold/gold.json` | команда + агент | 96.5% | 95.2% |
| `kelpopope/cqa-freedom` `data/gt/dev_labels.json` | черновик Claude + ручная проверка | 99.3% | 96.8% |
| `sabr2007/cqa-datachallenge26` `eval/gold.json` | вручную, местами двойная | 94.6% | 92.5% |
| `Azalytical/freedom-cqa` `data/gold/dev_gold_v2.json` | AI + арбитраж | 96.0% | 93.8% |
| `azimxxd/cqa-hackathon` `eval/labels/*.json` | вручную | 86.7% | 84.8% |
| `anuarkenzh1bekov/cqa-judge` `eval/gold.json` | полностью слепая ручная, 14 диалогов (112 клеток) | 83.9% | 75.6% |
| `AkhmadAssentay/cqa-freedom` `eval/gold_labels.json` | два прохода Claude по тексту чек-листа, 44 диалога | 94.8% | 91.2% |

Звонки (единственные внешние метки на p4): `Iza-git/cqa-hackathon` `research/labels.csv` 11/16 клеток с нашим gold (68.8%); `AkhmadAssentay` 19/24 с gold (79.2%), 12/21 с моделью (57.1%).

- Расхождение с `azimxxd` почти целиком в C7: там «прощание без итога» = Да (C7 совпадает на 40%). Мы, как и `alibek2007`, `dosmuhamedkemelbekov-ui`, `kelpopope`, `sabr2007`, требуем итог/предложение помощи **и** прощание — это буквальный текст чек-листа и #2814.
- Единственный полностью слепой ручной набор (`anuarkenzh1bekov`) — самый низкий: 83.9% с gold, 75.6% с моделью, но это 14 диалогов. Его не прячем: это нижняя граница внешней сверки.
- Ручных из перечисленных только часть (`alibek2007`, `sabr2007`, `azimxxd`, `anuarkenzh1bekov`); остальные — LLM с проверкой человеком. Это чужие разметчики, а не эталон. Используем только как внешний ориентир уровня точности; промпт и notes по этим меткам не подгонялись, `results/dev` не правился. Сами чужие метки в репо не копируем — только итоговые доли; источник — их публичные репозитории, путь к файлу указан.
