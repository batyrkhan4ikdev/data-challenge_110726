# Organizer answers

Case-relevant messages from the Telegram chat `Data Challenge'26` (id 4473389149), quoted verbatim with their message ids. All times are UTC+5. Updated every 2 h until the stop-code (plan task I1).

## 2026-11-07

**#2155** 12:04, Announcements: "Кейс уже объявлен, файлы прикрепленны здесь. Можете начинать решение"
→ T0 = 12:00.

**#2286 / #2310** 12:31, Максим (@Rough_coconut) / Announcements: `CQA_Chat_Quality_Checklist.pdf`
→ Stored as `docs/CQA_Chat_Quality_Checklist.pdf` and `.md`. It is the source of `data/checklists/chat.default.json`.

**#2292 / #2317** 12:32, Nikolay Borovinskiy (@BorovinskiyNA) / Announcements:
> Основным критерием будет точность AI-оценки диалогов. На контрольном этапе команды получат дополнительный набор из 10 ранее неизвестных транскриптов. Мы сравним выставленные системой оценки с заранее подготовленными эталонными оценками (Ground Truth). Чем ближе результаты к эталону, тем лучше.
> Помимо точности, будем учитывать: 1. Функциональность и уникальные возможности … 2. Удобство использования … 3. Корректность процесса: действительно ли система анализирует новые диалоги и применяет заданные критерии, а не воспроизводит заранее подготовленные результаты. 4. Разнообразие технических подходов: … в частности решений на локальных LLM и облачных AI-сервисах.

→ The benchmark is built against hand-labeled gold (B4–B7). Every evaluation keeps a raw audit record. Self-hosted models are preferred.

**#2303** 12:35, Максим (@Rough_coconut), Freedom Broker topic, answering #2284 (TS + Tailwind on the frontend): "Да, можно"
→ The TypeScript frontend is allowed.

**#2338** 12:40, Announcements: "С 13:00 до 15:00 в Ballroom Left будут проходит менторские сессии. Вы можете вживую задать вопросы Freedom брокеру"

**#2342** 12:42, Максим (@Rough_coconut), answering "репозиторий каждая команда свой создает?" (#2339): "Да. Публичный"

**#2343** 12:43, Nikolay Borovinskiy (@BorovinskiyNA):
> Чек-лист из 8 критериев, который мы предоставили, изначально разработан для оценки чатов. Для телефонных звонков логика оценки аналогичная, но критерии, связанные с письменной коммуникацией, должны адаптироваться к устной речи.
> В частности, по критерию №6 для звонков следует оценивать логичность ведения разговора, понятность объяснений, отсутствие неуместных выражений, корректность речевых формулировок и управление паузами. При наличии аудио также можно анализировать темп речи, дикцию и разборчивость произношения.
> По критерию №4 оценивается корректность и полнота консультации: ответил ли оператор на вопросы клиента, не предоставил ли ошибочную информацию, объяснил ли необходимые действия.
> Что касается справочника, у нас есть материалы с информацией по продуктам и услугам Freedom Broker. Однако отдельный справочник с эталонными ответами для каждого контрольного разговора участникам пока не предоставляется.
> При этом важно учитывать, что задача хакатона заключается не только в оценке по конкретным восьми критериям, но и в реализации гибкой системы, позволяющей создавать и применять различные чек-листы, в том числе для телефонных разговоров.

→ This is the source of `data/checklists/call.default.json` (plan task 0.2). It is also why the system supports several named checklists.

**#2334** 12:39, Nikolay Borovinskiy: "Условия отбора топ 50 строятся не только по метрикам, отбор не прозрачный. … полноценного лидерборда скорее всего не будет."

### Update 15:45 (topics Freedom Broker 732, Q&A Organizers 4, Announcements 5; messages through #2861)

The Telegram tool does not expose which message a reply points to, so each answer below is matched to its question by content and timing. These matches are inference.

**#2729** 15:03, Максим, answering #2705 «деплоить обязательно?»: "Нет, не обязательно. Можете демонстрировать на локальных машинках"
→ A public deploy is optional. I3 (the Cloudflare tunnel) drops to nice-to-have, and the demo runs on localhost.

**#2814** 15:28, Максим. Most likely answers #2686 (team −60HZ, 5 questions), because every point fits:
> 1. Внимательно перечитайте чеклист по данному пункту 2. N/a 3. На ваше усмотрение 4. не понял вопроса 5. Как вы решите

| Question in #2686 | Answer | Rule for prompt and gold |
|---|---|---|
| C7: operator answered and said goodbye, but gave no summary and no offer of further help | reread the checklist | Checklist: «Да — подвёл итог **или** предложил дальнейшую помощь **и** попрощался». A goodbye alone is **Нет** |
| C2: client gave every detail up front (some to the bot), operator answered without clarifying | **N/A** | «данных хватало с самого начала» also covers details the client gave the bot |
| C3/C8: operator revealed account data before identification | our call | Team default: C3 «Нет»; C8 «Да» only when the revealed data is confidential (balance, account, personal data) **and** no identification happened before it. Pin this in the B2 prompt |
| Calls C1: does IVR count; recording starts after the greeting; does «[Имя скрыто]» count as introducing oneself | did not understand | Open. Team default: «[Имя скрыто]» counts as introducing oneself. If the operator's greeting is not in the record, C1 «Нет» (C1 has no N/A) |
| Control: is accuracy per criterion or on the total; file format | «Как вы решите» (your call) | We pick the format: export per-criterion verdicts and the total (A5 `out/<group>.results.json`, plus a CSV) |

**#2815** 15:28, Максим, answering #2813 (should we account for intonation, voice volume, speed?): "можете сделать, если считаете нужным"
**#2825** 15:33: "Да", answering #2812 «наша модель же исключительно проверяет готовый транскрипт по критериям?»
**#2826** 15:34: "Именно. Как дополнительный источник к транскрипту", answering #2810 «чтобы проверяющий мог прослушать запись при проверке»
**#2827** 15:34: "Вызвав апи", answering #2508 / #2811 (how the control set and audio arrive)
**#2834 / #2838** 15:35–15:36: "А что ваша модель будет делать с аудиозаписями? Нужна ли транскрипция аудио?" … "Только если хотите упороться после реализации основного функционала"
→ Scoring is transcript-only. Audio is for the reviewer to listen to (player plus seek, C4). Audio analysis is optional, after the core works. The control set arrives through the same API.

**#2832–#2833** 15:35, dauka (organizers): "после дедлайна сдачи кейса, организаторы прогонят тесты и отберут некоторое количество команд … и только они будут питчить". **#2829**: "питчинг будет примерно с 12.30 и дальше".
→ Results must be ready and visible right at the stop-code (12:00). Only shortlisted teams pitch.

**#2845** 15:38, Максим to #2843/#2844 (Батырхан (BDA) re-posted our `docs/mentor-questions.md` as #2502): "Отвечено". Aryn asked for a link to the answer (#2855); no reply yet.

**Still unanswered:**
- How the comparison with Ground Truth works.
- A labeled example.
- Whether the control set includes calls.
- Whether the swapped criterion keeps its weight, and whether to re-score.
- C1 when the bot answers first.
- Whether there is a knowledge base for C4 (#2343 says one exists but has not been shared).

### Update 16:05 (through #2968)

**#2966** 16:02, Максим, answering #2965 (how you compare with the reference; can we get DEV dialogs with expert scores): "Эталона у вас нет, ребят. Прод версию получите по этой же апишке"
→ No reference labels will be given. Our 24-dialog gold set (B5) stays the only accuracy signal. The control set arrives through the same API, with a different `group_id`.

**#2968** 16:04, Максим: "Хотите делайте презентацию на локальной машине, хотите захостите аппку. Главное чтобы можно было тыкать в ui в реалтайме"
→ The UI must work live during the check: evaluate, appeal and swap a criterion in real time. Local is fine.

### Update 17:00 (through #2991)

**#2978** 16:10, Максим, answering Dimash's 7 questions (#2859):
> 1. По ответу на каждый критерий 2. Только чаты 3. Как бы вы это сделали? На второй вопрос, да 4. N/a 5. Как бы вы реализовали данную проверку? 6. База есть. Система как индикатор если что-то пошло не так, не по сценарию. Для проведения апелляции и переработке скрипта ответов 7. Да

| Question (#2859) | Answer | Our decision |
|---|---|---|
| Compare against the reference per criterion, on the total, or both? Is the gross-error flag counted? | **per criterion** | The benchmark ranks by weighted per-criterion agreement (B4/B6) |
| Control set: chats only, or calls too? | **chats only** | Tune the prompt mainly on chats. Calls stay supported |
| Does the new criterion replace one with the same weight? Re-score the control dialogs? | our call; **yes, re-score** | The weight is whatever the organizers give. «Переоценить по текущему чек-листу» is one click in the UI, plus `run_batch.py --refresh` |
| Calls: greeting not in the recording → «Нет» or N/A? | **N/A** | `call.default.json` c01: `na_allowed=true`, with N/A condition «приветствие оператора не попало в запись» |
| Calls: is asking full name + address/phone enough for identification? | our call | Team rule: the operator asked for identification data and the client gave it (masks in the transcript count) |
| Knowledge base for consultation? | exists, not shared; the system is an indicator of deviation from the script | C4 is judged by the logic and completeness of the answer; no invented facts |
| Round half up to 2 decimals (50.625 → 50.63)? | **yes** | Already done this way (A3) |

**#2980** 16:11, Максим, answering «вы будете чекать ридми и сами пробовать запускать?»: "Ридми да, запускать нет"

**#2981** 16:18, Nikolay Borovinskiy:
> Мы не ожидаем идеального совпадения с экспертными оценками до каждого балла. … При сравнении с Ground Truth мы будем смотреть на близость результатов и адекватность оценки в целом … N/A, грубые ошибки, неполные данные и спорные утверждения должны обрабатываться разумно. Если информации недостаточно для уверенного вывода, система не должна придумывать факты. … Нам важнее увидеть, что ваша система действительно умеет анализировать новые разговоры, а результаты выглядят обоснованными и воспроизводимыми.

**#2991** 16:28, Nikolay Borovinskiy. The demo is a live product:
> Покажите все диалоги, в которых система обнаружила грубые ошибки, и объяснения … как оператор может отправить результат оценки на апелляцию … как изменить чек-лист: добавить новый критерий, изменить существующий или поменять его вес … результаты оценки конкретного диалога, включая обоснование … можем попросить предоставить доступ к запущенному решению, например на вашем ноутбуке.

→ UI changes: a gross-error filter in the dialog list, and the gross-error badge jumps to the explanation. «Воспроизводимыми» argues for temperature 0 and k=1, or a fixed vote count, for the control run.
