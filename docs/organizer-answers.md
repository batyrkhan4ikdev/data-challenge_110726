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

### Update 17:45 (through #3041)

**#3004** 16:44, Nikolay Borovinskiy. How the top 50 is picked:
> • Близость результатов вашей системы к нашим экспертным оценкам (Ground Truth) на контрольном датасете. • Базовая техническая проверка репозитория по внутренним критериям. • Функциональность, удобство и интересные особенности продукта. • Разнообразие технических подходов. Мы планируем сохранить баланс между решениями на локальных LLM и облачных интеграциях. … Полная методика и веса факторов раскрываться не будут.

→ GT closeness stays first. We are a local-LLM solution (h200-gemma) with a cloud fallback, and `model.mode` in results.json reports this honestly (`local`, or `hybrid` if the fallback scored any dialog).

**#3011** 16:49, Nikolay Borovinskiy: build the UI for a large corporate customer (executives, QA specialists, employees); avoid cartoonish or playful styling.
**#3015** 16:56, Alexey: an example mockup («не эталон»). It has a dark-green sidebar (Диалоги / Чек-листы / Апелляции / Аналитика), a score ring, per-criterion points, «Почему снижена оценка», «Перейти к фрагменту» and «Оспорить оценку».
→ C6 (#25) restyles the UI in this direction and adds an «Аналитика» page.

**#3041** 17:26, Nikolay Borovinskiy: «аппендикс к гайду, ту описывается как нужно результаты сложить в репозиторий» (`CQA_Student_Guide_Appendix_Results.pdf`). Key rules:
- Files: `results/dev/results.json` (DEV: 60 chats + 5 calls) and `results/prod/results.json` (10 control chats). Access to prod and how to get it are announced one hour before stop-code.
- Format 1.0: `schema_version`, `team_name`, `model {mode: local|external_api|hybrid, name}`, `results[]`. Each result has `conversation_id`, `status`, `criteria[]` (`criterion_id`, `value`, `rationale`, `evidence_turns`) and `score {final_score, critical_flag}`.
- Codes: `contact, discovery, identification, consultation, empathy, dialogue, closure, critical`.
- Values: true = «Да», false = «Нет», null = N/A; scale values are raw points before weighting (dialogue 7 = 7 of 10).
- `evidence_turns` are numbered **from 1 over the raw transcript array**, including client, bot and events.
- `final_score` is 0–100 with 2 decimals, N/A weight redistributed. `critical_flag` equals critical and does not zero the total.
- A failed dialog is kept with `status: "error"`, `criteria: []`, `score: null` and `error`.
- Prod has exactly 10 entries. The files must be pushed to the public repo before stop-code; a local commit is not enough.

→ Implemented in `server/submission.py` (builder and validator) and `scripts/run_batch.py --submit dev|prod`, with `TEAM_NAME=fantastik 4`. Our `Turn.idx` is 0-based over the raw array, so the export adds 1.

Unanswered and not ours: #3036 (expected load), #3016 (C7 goodbye only; we already apply the literal rule, see above).

### Update 18:30 (through #3088)

**#3075** 17:47, Nikolay Borovinskiy: «Для звонков, либо берите транскрипт, либо адаптируйте. Звонки тут больше для интерфейсной части нежели для проверки точности результатов.»
→ This confirms that accuracy work goes into chats. Calls stay a UI feature (audio seek, adapted checklist).

**#3082** 18:02, Nikolay Borovinskiy, answering #3079 («Клиент разве не верифицируется когда заходит в приложение?»): «Рассматривайте омниканальную систему»
→ Logging in does not imply that the client was identified, because a chat can come from any channel. C3 stays as it is: identification is needed whenever the operator handles account or personal data.

**#3086 → #3088** 18:17–18:26, Alexey, on «порог первой реакции в 3 минуты»: «это SLA»
→ The 3-minute threshold is the first-response SLA. It is already in the chat checklist `notes` and is used for C6 (speed).

**#3059** 17:36, Alexey: «Не заостряйте внимание на нагрузке. Сделайте решение, которое легко можно будет масштабировать.»

**#3060** 17:36, Yerassyl (open, no answer yet). The appendix lists `contact` as true/false only, but #2978 said that a call whose greeting is not in the recording is N/A. Can such a call be exported as `null`?
→ Our DEV export has `contact = true` for all 5 calls, so it is valid today. `server/submission.py` follows the appendix strictly (no null for contact). If a re-run produces a call with contact N/A, the validator flags it. Revisit once the organizers answer. The control set is chats only, and in the chat checklist c01 has no N/A.

### Update 19:40 (through #3116; read by the m4 watcher, then checked)

**#3104 → #3106** 19:00–19:04. Alikhan asked: «В диалогах p1-ru-009, p1-kz-015 и p1-en-014 оператор без идентификации сообщает клиенту информацию о его счёте (ограничение на вывод) … только «Нет» по 03 или также «Да» по 08? … есть ли норматив по длительности удержания клиента на линии в звонках?» Максим answered: «Как вам кажется, этот кейс является нарушением обоих критериев? Ответ на второй вопрос, нет»
→ We read the rhetorical question as a yes: disclosing an account restriction before identification breaks both C3 and C8. There is no hold-time norm for calls.
→ Our DEV output flagged p1-ru-009 and p1-en-014 under C8 but **missed p1-kz-015 (KZ)** in both runs; c03 was «Нет» in all three. The team rule in the `notes` of both default checklists now names the account status and restrictions (block, ban on withdrawals), orders and operations explicitly, and states that the rule applies in every language. DEV is re-run.

**#3049 → #3055 / #3056** 17:31–17:34 (admin). Asked when results are due and when the submission form will come: «Скоро отправим ссылку для сдачи» / «Завтра в 12:00 дедлайн».
**#3044 → #3050** 17:31, Nikolay Borovinskiy: «Каждая команда создаёт свой репозиторий, открытый на github. Там их проект + результаты, это доп гайд по контракту json с результатами.»
**#3108 → #3114** 19:29, Nikolay Borovinskiy: «Все через гит.»
→ Results go only through the team's public repo (ours is public), with a deadline of 12:00 Nov 8. The organizers will post a link for submitting the repo.

**#3080 → #3084** 18:03, Nikolay Borovinskiy: «Видео не надо» (only the presentation and the live demo).
**#3076 → #3083** 18:03, Nikolay Borovinskiy, on whether the test dialogs are the same size as DEV: «Не большие».

### Update 22:00 (through #3260)

**#3112 → #3133, #3257, #3259** 20:17–21:21, Максим. Asked: «Нам дев данные самим размечать? есть ли эталонные данные по оценкам?» He first asked what was meant («Поясните… что вы подразумеваете под «дев данные самим размечать»?»), then answered: «Для вас эталонные данные, то что вы получаете через апи» / «В текущий момент».
→ Nothing beyond what the API returns. The fresh DEV payload (preflight, 21:55) still has only `conversation_id, channel, language, transcript, audio_url`, with no labels, which matches #2966. Our gold stays the LLM consensus plus Batyrkhantzy111's 20 human rows.

**#3167** 20:35, Nikolay Borovinskiy: «Не читают, хотят тренить модельку на 65 транскриптах..» — supports our decision not to fine-tune.

### Update 23:45 (through #3314)

**#3275** 22:50 (admin, Announcements): «Submission forma https://forms.gle/Nz34xz4yK4XurwAt7 Все решение сабмитайте сюда!»
→ The form requires a Google sign-in, so a person fills it in. Aryn's decision: fill it in once the work is finished (#29).

**#3312 → #3313** 23:26 (admin): asked «если условно мы сдадим форму сейчас, можем ли делать коммиты до 12…» — «Да».
**#3314** 23:27 (admin, Announcements): «Если что коммиты можно только до 12:00 воскресенья / Если коммиты после этого, то не засчитывается решение»
→ The hard limit is the last commit before 12:00 on Nov 8, the same as our stop-code. `results/prod/results.json` must be pushed before then.

**#3303 → #3304** 23:18 (admin): «Презентация что ваще до 12 да» — «Да». The presentation is also due by 12:00.

### Update 00:55 Nov 8 (through #3355)

**#3318 → #3327** 00:01–00:02, Nikolay Borovinskiy. Asked how they will verify that the test set was processed by the project's agent and not by GPT or Claude. Answer: «Если пройдёте в топ 10+- то попросим прогнать пару транскриптов при нас.»
→ Shortlisted teams run a couple of transcripts live in front of the jury. The control path has to work on demand: `run_batch.py` and «Оценить» in the UI on gemma, which stays up until 17:00. `docs/demo.md` already covers live evaluation (about 6 s per chat).

**#3352** 00:30, unanswered: whether `contact: null` is allowed for calls whose recording starts after the greeting. The question is the same as #3060. Our DEV calls all have `contact = true`; the control set is chats only.

### Update 01:25 Nov 8 (through #3399)

**#3354 → #3356/#3358** 00:32–00:34: «какое колво команд отберут на питчинг?» — «топ-50 команд» / «50».

**#3359** 00:34, Aaron Sain, in reply to Aryn's #3355 (private repo until morning?): «Репозиторий должен быть открытым после финального коммита, к моменту стоп-кода… До этого держать его открытым или закрытым — на ваше усмотрение.»
→ Our repo is public, and a history scan of all branches finds no team keys (H200, aigw, OpenRouter, FreedomSpeech). No new repo is needed.

**#3352 → #3394/#3397** 00:49–00:53, Nikolay Borovinskiy: «DEV-звонки даны больше для UI, а не для сравнения результатов. В контрольном наборе звонков не будет. Поэтому здесь на ваше усмотрение: можете использовать транскрипт, запись или придумать собственный подход. На презентации покажите, почему ваше решение в этом вопросе важно для бизнеса… Продуманный подход с хорошим обоснованием может дать небольшой плюс, а нерациональное решение — небольшой минус.»
→ The call transcript sources, the ASR benchmark and FreedomSpeech by default are exactly that kind of «продуманный подход». The pitch has to give its business reason: the organizer call transcripts are unusable for QA, so better ASR means correct scores on calls.

**#3370 → #3396/#3398** 00:53–00:54, Nikolay Borovinskiy: «Презентацию необязательно загружать в Git — её можно корректировать и после стоп-кода. Это касается только презентации, код решения после стоп-кода не меняем. Как уже говорил, достаточно пары слайдов. Лучшая презентация — живой продукт: покажите весь цикл работы вашего решения, от настройки чек-листа и получения диалогов до оценки, просмотра результатов, апелляции и ручной переоценки. … (макс 8-10 мин с вопросами)»
→ The deck shrinks to a few slides, and the demo follows their cycle in that order (`docs/demo.md`, `docs/pitch.md`). The slides can still change after stop-code; the code can't.

**#3407 → #3410** 00:58, Nikolay Borovinskiy. Asked whether the product can be published on a cloud host instead of HTML in GitHub. Answer: «В гите должен быть код, в тч html, хелперы, апи и любые компоненты которые вы сами разработали. Публиковать для презентации можете в облако, доп балов за это не получите )»
→ Already satisfied: `web/index.html`, `web/*.css`, `web/src/**/*.ts`, `server/` (API), `scripts/`, `bench/` and `config/` are tracked. `web/dist` is build output (`npm run build --prefix web`, README «Run»). There is no cloud deploy, and it earns no bonus.
