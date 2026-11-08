# Предложение Astra: CQA в языке Freedom

## 1. Вердикт

Рекомендую светлый рабочий интерфейс по образцу Freedom Bank с точечными акцентами Freedom Broker.
Белая навигация, нейтральный фон, тёмный текст и зелёный выбор лучше передают измеренный бренд, чем большая тёмно-зелёная полоса.
Первое изменение с высокой отдачей: вернуть на мобильном экране подписанную навигацию и убрать горизонтальный скролл всей страницы.
Второе: поднять итог оценки выше транскрипта на мобильном, раскрыть названия критериев и объяснения, сохранить переход к доказательству рядом с причиной снижения.
Третье: заменить разрозненные зелёные, состояния и размеры единым набором контрастных токенов и компонентов.
Кольцо, баллы, апелляции, версии и переоценка остаются; градиент получает только маленький декоративный участок около названия продукта.
Это предложение и изолированный CSS-прототип, не реализация и не подтверждение работы в D365.

## 2. Аудит текущего интерфейса

### Метод и границы доказательств

Исследованы исходники и все 14 baseline-снимков, все PNG Freedom reference и `computed-styles.json`. Размеры: desktop 1440×900, mobile 390×844. Desktop baseline иногда содержит всю страницу, mobile только первый экран. Дополнительно открыты все семь маршрутов живого приложения; модальное окно открыто без отправки. Запросы браузера, кроме GET/HEAD, блокировались. Ни одного блокированного запроса при съёмке прототипа не было.

Это независимый одноконтекстный разбор. Методика impeccable использована частично, без заявления о полном двухагентном `critique`. P0 означает блокировку основной операции, P1 существенное затруднение или подтверждённый дефект доступности, P2 улучшение иерархии или соответствия бренду. Подтверждённых P0 нет. Отсутствие записи звонка в fixture не является P0 интерфейса.

Снимки ниже с префиксом `baseline/` находятся в `../../baseline/`. Снимки модального окна находятся рядом с предложением. Измерения содержатся в [audit-evidence.json](audit-evidence.json) и [prototype-evidence.json](prototype-evidence.json). Для состояний непустой очереди, сохранения и сетевых ошибок выводы по коду помечены отдельно: эти сценарии не отправлялись на общий сервер.

### Shell и sidebar

- **P1, mobile, доступность.** При ширине ≤860 подписи ссылок скрываются через `display:none`, сами ссылки не имеют `aria-label`, а SVG имеет `aria-hidden=true`. В живом DOM у всех четырёх ссылок `innerText` пустой. Получаются безымянные ссылки для accessibility tree. Источники: `web/cqa.css:832`, `web/src/main.ts:66`, `web/src/ui/icons.ts:11`. Снимок: [dialogs.mobile.png](../../baseline/dialogs.mobile.png). Вернуть видимые подписи, добавить независимые accessible names.
- **P1, mobile, responsive.** Постоянная полоса 64 px забирает 16,4% ширины экрана 390 px до внутренних отступов. Источник: `web/cqa.css:825`. На [result-chat.mobile.png](../../baseline/result-chat.mobile.png) и [analytics.mobile.png](../../baseline/analytics.mobile.png) полезный контент уходит за правый край. Перевести меню в верхнюю сетку из четырёх ссылок.
- **P2, desktop, Freedom fit.** Зелёная область 236 px шириной и высотой viewport доминирует над данными. Это нынешний CQA, но не измеренная светлая оболочка Bank/Broker. Источники: `web/cqa.css:6`, `web/cqa.css:45`, `web/cqa.css:93`. Снимок: [dialogs.desktop.png](../../baseline/dialogs.desktop.png); сравнение с [freedom-bank.png](../../reference/freedom-bank.png).
- **P2, оба размера.** В структуре shell нет skip-link, а загрузка страницы представлена обычным абзацем. Источники: `web/src/main.ts:71`, `web/src/main.ts:103`. Снимок привязки: [review.desktop.png](../../baseline/review.desktop.png); клавиатурный обход всех маршрутов не выполнен. Добавить ссылку к main и `role=status` для загрузки, не заменять рабочие ссылки меню кнопками.

### Диалоги

- **P1, mobile, responsive.** Таблица вставляется прямо в root без scroll-container. `scrollWidth` живого документа 588 при viewport 390. Итог и грубая ошибка находятся вне первого экрана; ID ломается на две строки. Источники: `web/src/views/dialogs.ts:220`, `web/cqa.css:366`, `web/cqa.css:391`. Снимок: [dialogs.mobile.png](../../baseline/dialogs.mobile.png). Нужны локальный скролл как безопасный промежуточный шаг и мобильная строка с итогом и ошибкой в видимой части.
- **P2, оба размера, иерархия.** Настройки batch занимают отдельную полноразмерную панель даже при нуле выбранных строк. На мобильном она отодвигает список вниз; на desktop фильтр и параметры запуска выглядят почти одинаково. Источники: `web/src/views/dialogs.ts:209`, `web/cqa.css:982`. Снимки: [desktop](../../baseline/dialogs.desktop.png), [mobile](../../baseline/dialogs.mobile.png). Развести поиск и действие над выбранными строками; параметры режима и k оставить раскрываемыми, чек-лист и запуск не удалять.
- **P1, компоненты.** Граница поля `#B9C4BD` на белом даёт 1,80:1. В белой панели граница является основным обозначением поля. Источники: `web/cqa.css:289`, `web/cqa.css:338`. Снимок: [dialogs.desktop.png](../../baseline/dialogs.desktop.png). Для интерактивной границы принять отдельный токен ≥3:1; декоративные линии таблицы могут оставаться светлее.
- Сохранить существующий выбор нескольких строк, indeterminate у select-all и фильтр грубых ошибок: `web/src/views/dialogs.ts:57`, `web/src/views/dialogs.ts:68`. Не вводить постраничность до дедлайна только ради 65 строк.

### Результат: чат

- **P1, mobile, иерархия.** Транскрипт предшествует оценке в DOM, а мобильная высота его панели ограничена 420 px. Кольцо появляется только в нижней части первого экрана, причины снижения ещё ниже. Источники: `web/src/views/result.ts:345`, `web/cqa.css:1409`. Снимок: [result-chat.mobile.png](../../baseline/result-chat.mobile.png). На телефоне начинать с итога и критериев, затем причины и транскрипт.
- **P1, оба размера, содержимое.** Название критерия и объяснение обрезаются до одной строки; полная строка доступна через `title`, который не заменяет текст на touch. Источники: `web/cqa.css:1170`, `web/cqa.css:1242`, `web/src/views/result.ts:176`, `web/src/views/result.ts:187`. Снимки: [desktop](../../baseline/result-chat.desktop.png), [mobile](../../baseline/result-chat.mobile.png). Названия переносить полностью; объяснения показывать полностью либо через явное раскрытие, не hover-only.
- **P2, desktop, действия.** Пять одинаковых насыщенных кнопок перехода к фрагменту конкурируют с переоценкой. Источник: `web/src/views/result.ts:191`. Снимок: [result-chat.desktop.png](../../baseline/result-chat.desktop.png). Переход сделать спокойным зелёным outline/tint, апелляцию белой outline; основной насыщенный CTA оставить для запуска операции.
- **P1, mobile.** Ширина живой страницы 409 px при 390 px. Источники минимальных размеров и nowrap: `web/cqa.css:1170`, `web/cqa.css:1248`. Снимок: [result-chat.mobile.png](../../baseline/result-chat.mobile.png). Исправлять min-width и группы действий, не маскировать ошибку глобальным `overflow-x:hidden`.

### Результат: звонок

- **P1, mobile.** Те же 409 px ширины документа; плеер и системные сообщения занимают первый экран раньше результата. Источники: `web/src/views/result.ts:345`, `web/src/ui/transcript.ts:49`, `web/cqa.css:1409`. Снимок: [result-call.mobile.png](../../baseline/result-call.mobile.png). Сохранить native audio, дать компактную ссылку к транскрипту, результат поставить первым.
- **P2, desktop, чтение.** Разные цвета имени клиента, оператора, бота и системы добавляют ещё один набор семантических цветов рядом с оценкой. Источники: `web/cqa.css:1058`, `web/cqa.css:1062`, `web/cqa.css:1065`. Снимок: [result-call.desktop.png](../../baseline/result-call.desktop.png). Роль остаётся текстом; обычные имена нейтральные, доказательство обозначается заливкой и подписью.
- **P1, reduced motion.** JS всегда вызывает smooth-scroll, а reduced-motion блок не отключает `cqa-flash`. Источники: `web/src/ui/transcript.ts:75`, `web/src/views/result.ts:24`, `web/cqa.css:874`, `web/cqa.css:889`. Привязка: [result-call.desktop.png](../../baseline/result-call.desktop.png); анимация по статичному PNG не проверяется. В JS учитывать `matchMedia`, CSS-анимацию под reduce отключить отдельно.
- Не ломать `audio.currentTime = offset_s`: `web/src/ui/transcript.ts:76`. Звук 0:00 в baseline является ограничением данных из BRIEF, а не доказательством неисправного seek.

### Проверка апелляций

- **P2, desktop и mobile, пустое состояние.** Счётчик и одиночная фраза разбросаны по почти пустому экрану, не объясняют следующий шаг. Источники: `web/src/views/review.ts:165`, `web/src/views/review.ts:167`, `web/cqa.css:241`. Снимки: [desktop](../../baseline/review.desktop.png), [mobile](../../baseline/review.mobile.png). Одна спокойная область: "Открытых апелляций нет", пояснение, ссылка "К диалогам".
- **P1, непустая очередь, [INFERENCE].** На узком экране форма решения предшествует доказательству в одноколоночной карточке. Это побуждает принять решение до просмотра фрагмента. Источники: `web/src/views/review.ts:141`, `web/src/views/review.ts:149`, `web/cqa.css:854`. Непустой снимок отсутствует; [review.mobile.png](../../baseline/review.mobile.png) показывает только пустую очередь. Переставить мобильное чтение в порядок "оспариваемый критерий → комментарий → фрагмент → решение".
- Положительный контракт: обоснование обязательно, после решения есть сообщение с пересчитанным итогом. Сохранить `web/src/views/review.ts:95`, `web/src/views/review.ts:108`. Эти POST-сценарии исследованы только по коду.

### Чек-листы

- **P1, mobile, responsive.** Таблица без wrapper расширяет документ до 564 px, версия справа не видна. Источники: `web/src/views/checklists.ts:27`, `web/cqa.css:391`. Снимок: [checklists.mobile.png](../../baseline/checklists.mobile.png). Название и версия должны быть в первой строке мобильной записи, канал и ID во второй.
- **P2, desktop, иерархия.** Технический идентификатор занимает столько же внимания, сколько канал и версия. Источники: `web/src/views/checklists.ts:14`, `web/src/views/checklists.ts:15`, `web/cqa.css:382`. Снимок: [checklists.desktop.png](../../baseline/checklists.desktop.png). Усилить название, ID оставить метаданными. Сохранить прямую ссылку создания и ссылку открытия редактора.

### Редактор чек-листа

- **P1, mobile, responsive.** В строке раздела ID остаётся широким, название сжимается практически до первых букв. Документ имеет ширину 418 px. Источники: `web/cqa.css:710`, `web/cqa.css:717`, `web/src/views/checklist-editor.ts:270`. Снимок: [checklist-editor.mobile.png](../../baseline/checklist-editor.mobile.png). Название раздела должно получать полную строку, ID и удаление вторую.
- **P1, сохранение, [INFERENCE].** `save()` не имеет busy-guard, а кнопка submit не переводится в loading/disabled. Возможность повторной отправки видна по коду, не проверялась отправкой. Источники: `web/src/views/checklist-editor.ts:106`, `web/src/views/checklist-editor.ts:373`. Привязка: [checklist-editor.desktop.png](../../baseline/checklist-editor.desktop.png). Добавить локальное состояние сохранения, сохранить создание новой версии.
- **P2, desktop, иерархия.** Все восемь критериев полностью раскрыты, получилась страница 3835 px высотой. Источники: `web/src/views/checklist-editor.ts:171`, `web/src/views/checklist-editor.ts:352`. Снимок: [checklist-editor.desktop.png](../../baseline/checklist-editor.desktop.png). Не переписывать редактор в wizard; дать компактный заголовок каждого критерия и необязательное сворачивание описания.
- **P1, focus, [INFERENCE].** Sticky savebar может закрыть активное поле при прокрутке, в редакторе нет общего scroll-padding/резерва под панель. Источники: `web/cqa.css:744`, `web/src/views/checklist-editor.ts:367`. Снимок: [checklist-editor.mobile.png](../../baseline/checklist-editor.mobile.png). Проверить Tab с экранной клавиатурой; заранее зарезервировать место, не делать вторую fixed-панель.

### Аналитика

- **P1, mobile, responsive.** `scrollWidth=444`, процент у правого края обрезан. Четыре KPI по одному съедают большую часть первого экрана. Источники: `web/cqa.css:1272`, `web/cqa.css:1306`, `web/src/views/analytics.ts:129`. Снимок: [analytics.mobile.png](../../baseline/analytics.mobile.png). Сетка KPI 2×2, числам отдельная колонка, таблицам локальная область прокрутки.
- **P1, графические состояния.** Жёлтый `#D99A0B` на белом даёт 2,45:1, на треке `#E3E9E5` 1,99:1. Источники: `web/cqa.css:1115`, `web/cqa.css:1337`. На [analytics.desktop.png](../../baseline/analytics.desktop.png) показан другой набор значений, поэтому это проверка токена, не утверждение о жёлтой полосе в fixture. Использовать более тёмный amber и оставить подписи значений.
- **P2, desktop, семантика.** Гистограмма имеет четыре цветовых диапазона, а средние значения и кольцо используют три. Источники: `web/src/views/analytics.ts:17`, `web/cqa.css:1369`. Снимок: [analytics.desktop.png](../../baseline/analytics.desktop.png). Не менять пороги скоринга. Добавить явные подписи диапазонов, общий набор цветов и смысл "баллы", а не "успех банка".
- **P2, поведение ссылок.** Ссылки на грубые ошибки имеют `href='#'`, переход происходит после GET. Открытие в новой вкладке не соответствует подписи. Источник: `web/src/views/analytics.ts:112`. Снимок: [analytics.desktop.png](../../baseline/analytics.desktop.png). Разрешать evaluation URL заранее и ставить настоящий href; без нового API и без скрытия списка.

### Модальное окно апелляции

- **P2, desktop, иерархия.** Рабочий native dialog уже есть, но заголовок почти равен тексту формы, окно выглядит как случайный стандартный popup. Источники: `web/src/ui/appeal-modal.ts:25`, `web/cqa.css:672`, `web/cqa.css:65`. Снимок: [appeal-modal.desktop.before.png](appeal-modal.desktop.before.png). Заголовок 20/28, padding 24, radius 16, одна тень вместо рамки с тенью.
- **P1, mobile, [INFERENCE].** Фокус принудительно ставится в textarea при открытии, нет `max-height` по доступному viewport и scroll containment. На телефоне с экранной клавиатурой действия могут уйти за доступную область. Источники: `web/src/ui/appeal-modal.ts:75`, `web/cqa.css:672`. Снимок: [appeal-modal.mobile.before.png](appeal-modal.mobile.before.png); физическая клавиатура iOS/Android не проверена. Ограничить высоту через `dvh`, оставить скролл тела и видимую отмену.
- **P2, состояния.** При отправке блокируется submit, но текст кнопки не меняется; ошибка не связана с textarea через `aria-describedby`. Источники: `web/src/ui/appeal-modal.ts:40`, `web/src/ui/appeal-modal.ts:45`. Снимок базового состояния: [appeal-modal.desktop.before.png](appeal-modal.desktop.before.png). Существующий `banner()` уже имеет `role=alert`: `web/src/ui/dom.ts:50`; не заменять его немым toast.

### Что сохранить

Native ссылки, кнопки, dialog, labels; видимый focus: `web/cqa.css:86`; числовые колонки с `tabular-nums`: `web/cqa.css:399`; доступное имя score ring: `web/src/ui/icons.ts:73`; переход evidence в transcript: `web/src/views/result.ts:307`; исходный и пересчитанный результат: `web/src/views/result.ts:211`; цепочку решения: `web/src/ui/criteria-table.ts:19`.

Диагностика Refactoring UI, экспертная оценка по восьми вопросам, не usability-тест: 3/8, округлённо 4/10. Проходят свободное пространство, второстепенные подписи и ненавязчивая глубина. Не проходят общая иерархия первого мобильного экрана, иерархия без цвета, единая шкала отступов, ограничение длинного текста и контраст всех функциональных границ. Основания перечислены выше; это не оценка бизнес-логики.

## 3. Язык Freedom для Operate-инструмента

### Выбранная оболочка

Выбираю светлый shell. Bank даёт белые блоки на `#F5F6F7`, Broker даёт графитовый текст, прохладную подложку и мятное выделение. Обе измеренные шапки светлые: `reference/computed-styles.json:35`, `reference/computed-styles.json:235`. Для офисного QA с длинными RU/KZ-транскриптами постоянная тёмная полоса не помогает чтению. Это дизайн-решение, не доказанный результат пользовательского исследования.

На desktop слева 208 px, border 1 px; main получает 24 px padding. На mobile ≤700 px сверху обычная, не fixed, панель с четырьмя подписанными пунктами. Между 701 и 1100 px сохраняется подписанный sidebar и одна колонка результата. Не вводить скрытые hamburger-разделы перед демонстрацией. Одно действие бренда: маленькая градиентная линия под названием, не фон данных.

### Цветовые токены вместо блока `web/cqa.css:2–40`

Все цвета ниже являются назначением, а не разрешением свободно смешивать любые пары. Таблицы контраста далее задают допустимые сочетания. Старые имена сохраняются там, где роль та же; новые роли вводятся только для границ, disabled и pressed. Удалять старые токены можно лишь вместе с последним потребителем.

| Токен | Значение | Роль |
|---|---|---|
| `--cqa-bg` | `#F5F6F7` | Страница |
| `--cqa-surface`, `--cqa-side` | `#FFFFFF` | Карточка, навигация, поле |
| `--cqa-surface-2`, `--cqa-info-bg` | `#F3F8FF` | Hover, справочная область |
| `--cqa-side-2`, `--cqa-good-bg` | `#DFF5EC` | Выбранный пункт, положительное состояние |
| `--cqa-text`, `--cqa-side-text` | `#323335` | Основной текст |
| `--cqa-muted` | `#526173` | Метаданные, placeholder, подписи |
| `--cqa-link`, `--cqa-accent`, `--cqa-good`, `--cqa-focus` | `#007A43` | Ссылки, действие, положительная оценка, focus |
| `--cqa-accent-dark` | `#006537` | Hover основной кнопки |
| `--cqa-accent-pressed` | `#00562F` | Нажатие основной кнопки |
| `--cqa-accent-text` | `#FFFFFF` | Текст основной кнопки |
| `--cqa-bad` / `--cqa-bad-bg` | `#B42318` / `#FDECE9` | Ошибка, снижение, gross |
| `--cqa-warn` / `--cqa-warn-bg` | `#805300` / `#FFF4D6` | Частичный балл, открытая апелляция |
| `--cqa-info` | `#235A91` | Только информационный текст на info-bg |
| `--cqa-border` | `#D5DCE2` | Декоративные разделители, не outline поля |
| `--cqa-control-border` | `#788797` | Видимая граница input, secondary button |
| `--cqa-disabled-bg`, `--cqa-track` | `#E8ECEF` | Disabled и дорожка графика |
| `--cqa-chart-low` | `#A64B16` | Диапазон 50–70, текст рядом основной |
| `--cqa-evidence`, `--cqa-evidence-border` | `#FFF4D6`, `#805300` | Найденная реплика |
| `--cqa-expected`, `--cqa-expected-border` | `#FDECE9`, `#B42318` | Ожидаемый, но отсутствующий фрагмент |
| `--cqa-operator`, `--cqa-client`, `--cqa-bot`, `--cqa-system` | `#FFFFFF` | Нейтральные реплики; роль выражена словом |
| `--cqa-operator-border`, `--cqa-client-border`, `--cqa-bot-border` | `#D5DCE2` | Разделитель реплик, не код роли |

Правила, которые обходят токены, надо заменить вместе с блоком: `web/cqa.css:1062`, `web/cqa.css:1112`, `web/cqa.css:1294`, `web/cqa.css:1332`, `web/cqa.css:1364`. Иначе новый token block не создаст единую палитру. Семантические banner-цвета также переключить с hex на пары bad/good/info, `web/cqa.css:218`.

### Вычисленный контраст

Расчёт выполнен формулой WCAG relative luminance, sRGB breakpoint 0.04045, `(Lmax+0.05)/(Lmin+0.05)`. Значения округлены до двух знаков, проверка выполняется до округления. Исходные 47 вычислений: [contrast.json](contrast.json). Воспроизведение: `node docs/internal/redesign/proposals/astra/evidence-tools.cjs`.

| Фон | `#323335`, обычный текст | `#526173`, secondary/placeholder |
|---|---:|---:|
| `#FFFFFF` | 12,65:1 | 6,33:1 |
| `#F5F6F7` | 11,69:1 | 5,85:1 |
| `#F3F8FF` | 11,85:1 | 5,94:1 |
| `#DFF5EC` | 11,09:1 | 5,55:1 |
| `#FFF4D6` | 11,54:1 | 5,78:1 |
| `#FDECE9` | 11,05:1 | 5,53:1 |
| `#E8ECEF` | 10,64:1 | 5,33:1 |

| Текст / фон | Контраст | Применение |
|---|---:|---|
| `#007A43` / `#FFFFFF` | 5,43:1 | Ссылка, положительные баллы |
| `#007A43` / `#F5F6F7` | 5,02:1 | Ссылка на странице |
| `#007A43` / `#F3F8FF` | 5,09:1 | Hover ссылки |
| `#007A43` / `#DFF5EC` | 4,76:1 | Выбранный nav, success badge, tinted action |
| `#FFFFFF` / `#007A43` | 5,43:1 | Primary default |
| `#FFFFFF` / `#006537` | 7,20:1 | Primary hover |
| `#FFFFFF` / `#00562F` | 8,85:1 | Primary active |
| `#FFFFFF` / `#B42318` | 6,57:1 | Gross badge при необходимости заливки |
| `#B42318` / `#FFFFFF` | 6,57:1 | Снижение, danger outline |
| `#B42318` / `#FDECE9` | 5,75:1 | Ошибка, error badge |
| `#805300` / `#FFFFFF` | 6,66:1 | Частичные баллы |
| `#805300` / `#FFF4D6` | 6,07:1 | Предупреждение, апелляция |
| `#235A91` / `#FFFFFF` | 7,14:1 | Информационная подпись |
| `#235A91` / `#F3F8FF` | 6,69:1 | Info banner |

Для evidence/expected текст, имена ролей и время берутся только из первых двух колонок большой таблицы. Нельзя оставлять произвольный зелёный или синий speaker поверх amber/error. Для read-only и disabled opacity не применять: `#526173` / `#E8ECEF` остаётся 5,33:1, хотя inactive controls освобождены от требования контраста.

| Нетекстовый элемент / фон | Контраст |
|---|---:|
| Граница `#788797` / белый, page, disabled | 3,68 / 3,40 / 3,10:1 |
| Зелёная линия/кольцо `#007A43` / белый, track | 5,43 / 4,57:1 |
| Amber линия `#805300` / белый, track | 6,66 / 5,60:1 |
| Красная линия `#B42318` / белый, track | 6,57 / 5,53:1 |
| Коричневая линия `#A64B16` / белый, track | 5,77 / 4,86:1 |

Не пытаться сделать соседние histogram bars различимыми только цветом: между ними gap и всегда есть диапазон и число. `#D5DCE2` допустим для необязательных разделителей, не для единственной границы интерактивного поля.

### Размеры, форма, focus и движение

| Группа | Спецификация |
|---|---|
| Типографика | Одна семья Noto Sans. UI `14/20` 400; metadata `13/18` 400; label/button `14/20` 600; transcript `15/24` 400; section `20/28` 600; page `28/35` 700, mobile `24/30`; total `32/40` 700. Табличные числа `tabular-nums` |
| Шкала spacing | 4, 8, 12, 16, 20, 24, 32, 48 px. Между строками внутри группы 8–12, между группами 20–24. `--cqa-gap:12px` |
| Контролы | Desktop минимум 40 px по высоте; компактное действие строки 32 px. Mobile 44 px, target чекбокса через label 44×44. 44 px является целевым touch-размером, не утверждением о минимуме WCAG AA, который обычно 24 px с исключениями |
| Таблица | Строки около 44 px; header 40 px; ID и баллы не ломаются посимвольно. Длинные объяснения переносятся |
| Радиусы | `--cqa-radius:8px` для input/button; `--cqa-radius-lg:12px` для секции; modal 16 px; badge 6 px. Не делать большие pill-кнопки |
| Тени | Обычные секции без тени, только border. Modal `0 16px 48px rgba(25,25,25,.18)`, без border. Sticky savebar `0 -2px 8px rgba(25,25,25,.06)` |
| Focus | 3 px `#007A43`, offset 3 px, внутренняя белая прослойка 2 px на filled control. На белом 5,43:1, на mint 4,76:1. Не заменять focus изменением заливки |
| Motion | Цвет/граница 150 ms `cubic-bezier(.2,0,0,1)`; раскрытие 180 ms; закрытие 120 ms. Без scale на hover, без entrance-анимаций. При reduce мгновенное состояние, без smooth-scroll и flash |
| Текст | Проза максимум 70ch, без ограничений длины на таблицу. Заголовки без uppercase, tracking от 0 до −.02em. Поля mobile 16 px, чтобы не провоцировать zoom клавиатуры |

Градиент `linear-gradient(91deg,#7D8DEE -1.79%,#1CCC9E 25.51%,#1AE276 82.98%)` допустим только как линия 2–3 px под брендом. Там нет текста и функционального сигнала. Не использовать его под кнопками, итогом, selected row, диаграммами или в тексте. Графит на трёх stop даёт 4,17 / 6,13 / 7,34:1; первый stop уже не проходит AA для обычного текста. Поэтому копирование маркетингового CTA Broker запрещено даже при визуальной похожести.

## 4. Шрифт и доставка в D365

Выбор: **Noto Sans, normal variable**, веса 400/500/600/700. Он менее геометрический, чем CoFo Sans, но нейтрален на длинных кириллических репликах и не добавляет инженерного характера IBM Plex. Оценка сходства визуальная, не идентичность метрик.

| Кандидат | Лицензия и первичный источник | Казахская кириллица в проверенном файле | Внешний вид и решение |
|---|---|---|---|
| Noto Sans | [SIL OFL 1.1](https://raw.githubusercontent.com/google/fonts/main/ofl/notosans/OFL.txt), [metadata](https://raw.githubusercontent.com/google/fonts/main/ofl/notosans/METADATA.pb) | Все 18 знаков `ӘәҒғҚқҢңӨөҰұҮүҺһІі` имеют ненулевой glyph ID | Нейтральный sans, ясное чтение. Выбран |
| IBM Plex Sans | [SIL OFL 1.1, reserved name Plex](https://raw.githubusercontent.com/google/fonts/main/ofl/ibmplexsans/OFL.txt), [metadata](https://raw.githubusercontent.com/google/fonts/main/ofl/ibmplexsans/METADATA.pb) | Все 18 знаков подтверждены | Хорошая плотность и меньший файл, но узнаваемый технический рисунок. Второй выбор |
| Manrope | [SIL OFL 1.1](https://raw.githubusercontent.com/google/fonts/main/ofl/manrope/OFL.txt), [metadata](https://raw.githubusercontent.com/google/fonts/main/ofl/manrope/METADATA.pb) | В проверенном файле отсутствуют `ӘәҒғҚқҢңҰұ`; наличие `cyrillic-ext` в metadata недостаточно | Геометрически ближе к желаемому впечатлению, но непригоден как единая семья для KZ без подмешивания fallback |

Проверка cmap format 4/12 выполнена по оригинальным TTF из Google Fonts, URL и результаты сохранены в [font-evidence.json](font-evidence.json), алгоритм в [evidence-tools.cjs](evidence-tools.cjs). Это проверяет наличие глифов, не качество shaping каждого возможного текста. Проверено на текущих файлах upstream на дату исследования; при смене версии проверку повторить.

**Доставка:** base64 `@font-face` внутри отдельного CSS web resource, не отдельный TTF web resource и не CDN. Пример реально использован в [font-data.css](font-data.css). Полный неизменённый Noto TTF весит 2 049 096 байт, base64 2 732 128 байт, CSS 2 732 382 байта. Это примерно 2,61 MiB и ниже 5 MB по умолчанию. Веса разделяют один variable-файл, четыре копии не нужны. Лицензия рядом в [font-license.txt](font-license.txt); при упаковке её текст должен попасть в доступный комментарий CSS или отдельный HTML web resource, поскольку `.txt` также не является целевым типом web resource.

Объявление: `font-family:'Noto Sans'; font-style:normal; font-weight:100 900; font-display:swap; src:url(data:font/ttf;base64,...) format('truetype')`. Использовать prefixed family name в итоговой упаковке, например `CqaNotoSans`, чтобы global `@font-face` не столкнулся с host. Все обычные селекторы остаются под `.cqa`. Fallback: `'Segoe UI', Arial, sans-serif`; layout обязан оставаться рабочим, если font заблокирован.

Цена полного файла ощутима для CSS; это осознанный компромисс исследовательского пакета, а не заявление о быстрой загрузке на мобильной сети. Уменьшение до WOFF2/subset разумно только с повторной проверкой всех KZ-глифов и лицензии. Размер такого subset здесь не измерен. Не обещать 50–100 KB без сборки.

В D365 формат CSS разрешён, шрифтовые типы отдельно не разрешены: [Microsoft web resources](https://learn.microsoft.com/en-us/power-apps/developer/model-driven-apps/web-resources). Data URI требует разрешения CSP `font-src data:` или подходящего fallback в политике; [Power Platform CSP](https://learn.microsoft.com/en-us/power-platform/admin/content-security-policy). **[INFERENCE]** Этот конкретный tenant может запретить data fonts. В trial D365 внедрение не проверялось. Не ослаблять CSP ради шрифта; если политика запрещает data, использовать fallback и оставить весь redesign. CDN отклонён: внешняя зависимость, CSP и недоступность в корпоративной сети.

## 5. Спецификация по экранам

### Общий контракт состояний

Этот контракт применяется к каждому экрану ниже; статические числа не получают фиктивные hover/active/disabled. Формы используют native disabled, не одну opacity. Все новые строки добавляются в `web/src/i18n.ts`, все layout-правила в `web/cqa.css`.

| Состояние | Обязательное поведение |
|---|---|
| Default | Белая поверхность, основной текст; один filled CTA на область принятия решения |
| Hover | Для ссылок underline сохраняется; для secondary tint `#F3F8FF`; primary dark. Данные без действия не получают cursor:pointer |
| Focus | Описанное кольцо; visible label и accessible name; элемент не закрывается sticky-панелью |
| Active | Filled primary `#00562F`; выбор строки mint + checkbox; навигация mint + контрастная рамка + `aria-current` |
| Disabled | Нейтральная заливка, читаемая подпись, без hover; причина недоступности текстом, если не очевидна из счётчика |
| Loading | Существующее содержимое не исчезает при локальной операции; `aria-busy`, текст действия "Сохранение…"/"Переоценка…"; `role=status`. Для первой загрузки спокойные статические skeleton-строки, без shimmer |
| Empty | Название ситуации, причина если известна, один доступный путь дальше. Не рисовать fake KPI, успех или демонстрационные записи |
| Error | Inline banner через существующий helper; сохранить ввод/данные; связать поле и ошибку `aria-describedby`, выставить `aria-invalid`. Повтор доступен, когда запрос завершён |

### Shell/sidebar

- Desktop: 208 px nav, main свободной ширины с padding 24. Название `CQA` и при одобренном брендировании подпись `Freedom`; настоящий SVG не перерисовывать приблизительно. Mobile: верхняя панель 4 равных колонок с icon + label, не fixed, scroll страницы обычный. Модель fake остаётся доступной в служебной информации, на demo её не маскировать как production.
- Состояния: hover/focus/active из общего контракта. Disabled для маршрутов не вводить. Loading/error в main не блокируют меню. Empty/notfound показывает ссылку на диалоги.
- **CSS-only:** `.cqa`, `.cqa-sidebar`, `.cqa-brand`, `.cqa-nav`, `.cqa-nav-link`, `.cqa-model-badge`, `.cqa-main`, `.cqa-heading`, `.cqa-page-*`.
- **TS/DOM:** `web/src/main.ts`: `aria-label` ссылкам, skip-link `.cqa-skip-link`, focus main после явной смены маршрута без перехвата ввода, live status первой загрузки. Новая визуальная подпись не должна менять href или ключи NAV_ITEMS.

### Диалоги

- Desktop: заголовок, строка фильтров, отдельная полоса batch, затем таблица. Итог справа, gross рядом; источник данных и счётчик не спорят с заголовком. Показаны все 65 записей, без нового pagination.
- Mobile: в записи первая строка содержит checkbox, ID и итог; вторая канал/язык/реплики и gross. Не скрывать gross как второстепенную колонку. Режим/k можно свернуть в native details "Параметры оценки", чек-лист, счётчик выбранных и запуск остаются снаружи. До такого DOM-перехода допустим локальный horizontal scroll, но не scroll всего document.
- Состояния: hover только строка/ссылка, focus на checkbox и ссылке; selected остаётся при фильтрации согласно текущему Set. Disabled запуска при 0 выбранных или running. Loading batch показывает числитель/знаменатель; loading списка сохраняет прежние строки. Empty предлагает сбросить фильтры; error оставляет предыдущие строки и пояснение. Не запускать оценку кликом по всей строке.
- **CSS-only:** `.cqa-toolbar`, `.cqa-toolbar--batch`, `.cqa-table`, `.cqa-dialogs`, `.cqa-check-cell`, `.is-selected`, `.cqa-progress*`, `.cqa-num`.
- **TS/DOM:** `web/src/views/dialogs.ts`: wrapper `.cqa-table-wrap` с label/tabindex, modifier `.cqa-table--dialogs`, устойчивые классы ячеек `.cqa-cell-id`, `.cqa-cell-total`, `.cqa-cell-gross`, видимые mobile labels. Сохранить native table/header association; если CSS grid меняет accessibility tree, добавить явные table/row/cell roles и проверить screen reader. Одна копия данных и чекбоксов, не два независимых selected state. `web/src/i18n.ts`: recovery-copy и подпись parameters.

### Результат чата

- Desktop: transcript и score рядом, соотношение 5:6; transcript 15/24, до 70ch; score ring 112 px. Названия критериев и причины не обрезать. В каждой причине переход и апелляция сгруппированы с текстом. Для длинного explanation допустим native details с кратким началом, полный текст всегда доступен клавиатурой.
- Mobile: summary/score первым, затем причины, transcript и details. Кольцо 96 px, числа `x / weight` остаются справа каждой строки. В production DOM сначала score, затем transcript, desktop размещает transcript слева через grid areas. Логический порядок для чтения остаётся "оценка → доказательства"; это надо проверить с screen reader, не оставлять лишь CSS order.
- Состояния: hover/focus у перехода и апелляции; active evidence получает подпись "Фрагмент критерия" плюс фон. Disabled переход имеет видимую причину "Фрагмент не найден". Loading переоценки сохраняет старое кольцо и маркирует состояние. Empty потерянных баллов: "Снижений нет"; total null не равен нулю. Error transcript не убирает score, error переоценки возвращает возможность повтора. Открытая апелляция остаётся warn-badge вместо повторной кнопки.
- **CSS-only:** `.cqa-split`, `.cqa-pane--transcript`, `.cqa-turn*`, `.cqa-score-*`, `.cqa-ring*`, `.cqa-mark*`, `.cqa-pts-*`, `.cqa-why-*`, `.cqa-details`, `.cqa-facts*`.
- **TS/DOM:** `web/src/views/result.ts`: логический порядок, кнопка/ссылка возврата от evidence к критерию, доступная причина disabled, общий status. `web/src/ui/transcript.ts`: focus target `tabindex=-1`, reduced-motion scroll, подпись evidence/expected. `web/src/ui/criteria-table.ts`: сохранить original → decision → final и локальный wrapper деталей. Не менять band thresholds и расчёт.

### Результат звонка

- Desktop: та же сетка, плеер сверху transcript, нативные controls. Sticky audio имеет непрозрачный белый фон и не перекрывает заголовок/фокус. Mobile: оценка первой; ссылка "К записи и транскрипту" переходит к тому же audio, не создаёт второй плеер. Плеер width 100%, максимум ширины панели.
- Состояния: общий контракт результата. Audio loading сохраняет место, unavailable/error даёт видимое объяснение без фиктивной волны. Play/pause/seek остаются native; focus evidence меняет `currentTime`, но не включает autoplay. Empty transcript не подменяется системной фразой. Active реплика имеет и номер, и временную метку, а не только цвет.
- **CSS-only:** `.cqa-audio`, `.cqa-audio-bar`, `.cqa-turn-time`, `.cqa-pane--transcript` и общие result-классы.
- **TS/DOM:** `web/src/ui/transcript.ts`: обработчики metadata/error для статуса аудио и сохранение seek; `web/src/views/result.ts`: anchor к записи. Fixture 0:00 не заменять fake duration. При отсутствии рабочего аудио acceptance seek остаётся обязательной проверкой с отдельными разрешёнными данными, не считается пройденной.

### Проверка апелляций

- Desktop: карточка апелляции с критерием, диалогом и состоянием; слева объяснение/комментарий/решение, справа evidence. Mobile: заголовок, комментарий, evidence, затем форма. Поля и радио доступны без горизонтального скролла. Решённая карточка остаётся с результатом и ссылкой к диалогу, не исчезает внезапно.
- Состояния: hover/focus у radio, select и кнопок; active radio ясно меняет набор полей; disabled только отправка текущей карточки. Loading сохраняет reason; empty показывает "Открытых апелляций нет" и "К диалогам". Error не сбрасывает reason/new verdict. Success показывает исходный и новый итог текстом, без одной зелёной галочки.
- **CSS-only:** `.cqa-appeal*`, `.cqa-fragment`, `.cqa-decision`, `.cqa-radio*`, `.cqa-empty`, `.is-resolved`.
- **TS/DOM:** `web/src/views/review.ts`: отдельные блоки `.cqa-appeal-context`, `.cqa-appeal-evidence`, `.cqa-appeal-decision` с корректным DOM-порядком; status busy; `web/src/i18n.ts`: пустое состояние. `api.decide` и вывод recomputed total не переписывать.

### Чек-листы

- Desktop: таблица "Название / Канал / Версия / ID"; ID второстепенный. Mobile: карточка-строка, название и версия сверху, канал/ID снизу. Создать доступно в заголовке и не превращается в floating action button.
- Состояния: hover/focus настоящих ссылок; active nav остаётся checklist; disabled к статическим строкам неприменим. Loading показывает две placeholder-строки; empty предлагает "Создать чек-лист"; error предлагает повтор GET, не новый пустой список. Открытие ссылки не меняет текущую версию.
- **CSS-only:** `.cqa-table`, `.cqa-heading`, `.cqa-badge--info`, `.cqa-btn`.
- **TS/DOM:** `web/src/views/checklists.ts`: `.cqa-table--checklists`, типизированные классы ячеек, mobile label/version placement, wrapper. Не навешивать CSS на общий nth-child без типа таблицы.

### Редактор чек-листа

- Desktop: header с названием и version picker; основная форма до 1120 px; критерии последовательными секциями, не сеткой карточек. ID/тип/вес компактны; название/описание широкие. Savebar показывает сумму, состояние изменений и сохранение новой версии.
- Mobile: один столбец. Раздел: название на полной строке, ID+удаление ниже. Ступень: значение компактно, описание полной ширины. Кнопки reorder минимум 44 px, название критерия переносится. Savebar sticky в потоке с резервом ≥80 px; при открытой клавиатуре не перекрывает активное поле.
- Состояния: hover/focus все поля; active редактируемое поле имеет focus, не новый цвет страницы. Disabled старая версия через существующий fieldset, явная подпись read-only. Loading/save блокирует повтор, не стирает значения. Empty разделов/критериев показывает соответствующую кнопку добавления. Error сохраняет draft и привязывается к полям, если сервер дал путь; success сообщает новый номер версии и оставляет путь к переоценке результата.
- **CSS-only:** `.cqa-grid`, `.cqa-span-*`, `.cqa-section-row`, `.cqa-step*`, `.cqa-criterion*`, `.cqa-savebar`, `.cqa-version-picker`, `.cqa-sum*`.
- **TS/DOM:** `web/src/views/checklist-editor.ts`: save busy-state, подписи ID/name в разделах, optional native details для длинных описаний, сохранение focus после reorder, предупреждение о несохранённом draft при уходе. Новые классы `.cqa-section-id`, `.cqa-section-title`, `.cqa-editor-status`. Не включать autosave: он меняет модель версий и выходит за redesign.

### Аналитика

- Desktop: четыре KPI в строке, затем criteria 6/11 и histogram+breakdowns 5/11. Red/amber отражают значения, не бренд. Грубые ошибки остаются ниже отдельным списком ссылок.
- Mobile: KPI 2×2, критерии полной ширины, histogram, breakdowns, gross list. Каждому проценту 64 px, число не выпадает из viewport. Подписи длинных критериев переносятся. Гистограмма сохраняет четыре диапазона и отдельные count-labels.
- Состояния: hover/focus лишь у настоящих ссылок, никакого hover на статическом KPI. Active route в nav. Disabled не применим к метрикам. Loading статические placeholders вместо нулей; empty "Нет оценённых диалогов" со ссылкой к группе; error с повтором GET. По клику gross-link нельзя молча ничего не делать при сетевой ошибке.
- **CSS-only:** `.cqa-kpis`, `.cqa-kpi*`, `.cqa-analytics-grid`, `.cqa-bar*`, `.cqa-hist*`, `.cqa-gross-list`, `.cqa-table`.
- **TS/DOM:** `web/src/views/analytics.ts`: настоящие href для gross-list после разрешения evaluation IDs, error/status для неразрешённой ссылки; wrapper breakdown-таблиц и доступное описание диапазонов. Ни новых графических библиотек, ни изменения агрегации.

### Модальное окно

- Desktop: 560 px максимум, padding 24, заголовок 20/28, критерий отдельной строкой, textarea минимум 5 строк. Actions справа, отмена вторичная. Mobile: `width:calc(100vw - 24px)`, max-height `calc(100dvh - 24px)`, body scroll, controls 44 px. Не имитировать полный экран через transform.
- Состояния: hover/focus/active стандартные; native dialog удерживает focus. Disabled только submit во время отправки; loading текстом "Отправка…". Empty comment является незаполненным полем, не отдельной иллюстрацией. Error сохраняет комментарий, ставит aria-invalid и фокус в поле. Escape/Отмена закрывают, focus возвращается к исходной кнопке. Перед отправкой критерий остаётся видимым, без дополнительных маркетинговых обещаний.
- **CSS-only:** `.cqa-modal`, `.cqa-form`, `.cqa-form-actions`, `.cqa-textarea`, `.cqa-form-errors`.
- **TS/DOM:** `web/src/ui/appeal-modal.ts`: сохранить reference opener, вернуть focus после remove, `aria-labelledby`/`aria-describedby`, id ошибки, busy label; на coarse pointer первоначальный focus на заголовок с `tabindex=-1`, чтобы не открывать клавиатуру без выбора поля. Сохранить native `showModal()` и обязательный комментарий.

## 6. Доказательства прототипа

Прототип внедрён через Playwright `page.addStyleTag`, отдельно font-data и override. Каждая пара before/after снята на новой странице, чтобы hash-навигация не переносила stylesheet на следующий before. Выполнение воспроизводится командой `node docs/internal/redesign/proposals/astra/capture-prototype.cjs`. Скрипт не делает POST, PATCH, PUT или DELETE, не нажимает submit/evaluate/save. Модальное окно открывается и закрывается Escape.

| Экран | Desktop before → after | Mobile before → after |
|---|---|---|
| Диалоги | [before](dialogs.desktop.before.png) → [after](dialogs.desktop.after.png) | [before](dialogs.mobile.before.png) → [after](dialogs.mobile.after.png) |
| Чат | [before](result-chat.desktop.before.png) → [after](result-chat.desktop.after.png) | [before](result-chat.mobile.before.png) → [after](result-chat.mobile.after.png) |
| Звонок | [before](result-call.desktop.before.png) → [after](result-call.desktop.after.png) | [before](result-call.mobile.before.png) → [after](result-call.mobile.after.png) |
| Апелляция | [before](appeal-modal.desktop.before.png) → [after](appeal-modal.desktop.after.png) | [before](appeal-modal.mobile.before.png) → [after](appeal-modal.mobile.after.png) |

![Чат desktop после override](result-chat.desktop.after.png)

![Чат mobile после override](result-chat.mobile.after.png)

Полная страница с причинами и транскриптом: [desktop](result-chat.desktop.full.after.png), [mobile](result-chat.mobile.full.after.png). CSS: [prototype.css](prototype.css). Снимки показывают реальные fake-model ответы, не сочинённые объяснения.

Измерено: dialogs mobile `588→390`, chat `409→390`, call `409→390` для `document.documentElement.scrollWidth`, viewport 390. Desktop у всех трёх `1440→1440`. Подписи четырёх nav-link появились. Noto загружен до съёмки через `document.fonts.ready`. Эти данные подтверждают отсутствие общего overflow на трёх проверенных маршрутах, а не полную доступность приложения.

Что не решено и не должно попасть в production как готовый результат:

1. В мобильном dialogs CSS-прототип оставил локальный горизонтальный scroll. Итог и gross всё ещё правее первого видимого столбца. Нужен описанный TS/DOM вариант строки; это не принимается как окончательный mobile-дизайн.
2. В score prototype используется `order:-1`, поэтому визуальный порядок и DOM-порядок расходятся. Production должен менять DOM, а не копировать этот приём.
3. Mobile score помещает все восемь строк в первый экран, но "Почему снижена оценка" начинается ниже. Это приемлемее baseline с транскриптом первым; compact anchor к причинам ещё требует markup.
4. Поле k продолжает обрезать placeholder, а uppercase header таблицы сохранился из более специфичного существующего selector. В implementation менять исходные правила, не дописывать ещё один хвост override.
5. Шрифт normal variable не включает настоящий italic. Системные реплики пока используют browser synthetic italic; в итоговом дизайне сделать их обычным начертанием с muted color, не загружать вторую семью.
6. Prototype не доказывает keyboard focus после перехода к evidence, submit/loading/error, screen-reader table semantics, D365 CSP или аудио seek. Submit-действия намеренно не выполнялись. Непустая review-очередь не была создана.
7. Бренд в прототипе ограничен палитрой и линией около CQA; официальный логотип и окончательная подпись продукта не подменялись случайным SVG.

## 7. Порядок изменений до stop-code

Каждый пункт должен быть отдельной законченой поставкой. Не начинать следующий, если нельзя закончить его до 12:00 8 ноября. После любого пункта остаются четыре nav-раздела, ring, `x / weight`, причины снижения, переход, апелляция, gross-filter, audio seek, цепочка решения и версии с переоценкой. Пороговые формулы, API и типы generated не менять. Checks ниже являются acceptance для implementation, не заявлением, что они уже пройдены.

| № | Законченный шаг | Файлы и тип | Риск | Наблюдаемая проверка |
|---|---|---|---|---|
| 1 | Единая контрастная палитра и состояния | `web/cqa.css`, CSS-only | Низкий; прямые hex могут пережить замену | `#/dialogs/DEV`, `#/evaluation/p1-ru-001-132ab7e5`, 1440/390: primary 5,43:1, metadata ≥5,33:1, focus видим, gross красный; все старые действия остались |
| 2 | Светлая оболочка и подписанная навигация | `web/cqa.css`, `web/src/main.ts`, `web/src/i18n.ts`, CSS+TS | Средний; порядок focus | Все маршруты, 1440/390: четыре видимых имени, active с `aria-current`, nav accessible names не пусты, Tab и skip-link достигают main; текст выбранного пункта 4,76:1 |
| 3 | Локальный скролл таблиц без потери колонок | `web/cqa.css`, `web/src/views/dialogs.ts`, `web/src/views/checklists.ts`, `web/src/views/analytics.ts`, CSS+DOM | Низкий; table semantics | `#/dialogs/DEV`, `#/checklists`, `#/analytics/DEV`, 390: document width=390, wrapper прокручивается клавиатурой, итог/версия/gross доступны справа; desktop таблицы прежнего состава |
| 4 | Мобильные строки диалогов и компактный batch | `web/cqa.css`, `web/src/views/dialogs.ts`, `web/src/i18n.ts`, CSS+TS | Средний; selection при фильтре | `#/dialogs/DEV`, 390: ID, итог и gross одной записи видны без горизонтального scroll; checkbox и select-all не потеряли выбор; mode/k раскрываются, запуск выбранных доступен; выбранная строка текст ≥5,55:1 |
| 5 | Приоритет оценки и читаемые объяснения | `web/cqa.css`, `web/src/views/result.ts`, CSS+DOM | Средний; DOM/read order | Chat и call routes из BRIEF, 1440/390: ring и все `x / weight` сохранены, названия переносятся, explanation раскрывается touch/keyboard; mobile начинается с оценки, "Почему снижена оценка" доступно без поиска в details |
| 6 | Надёжный переход к доказательству и native audio | `web/cqa.css`, `web/src/ui/transcript.ts`, `web/src/views/result.ts`, `web/src/ui/criteria-table.ts`, CSS+TS | Высокий; seek и focus | Call route, 1440/390: click/Enter "Перейти к фрагменту" выделяет нужную реплику и меняет `currentTime` на offset на разрешённой рабочей записи; возврат к критерию; reduce не анимирует scroll; evidence text ≥5,78:1 |
| 7 | Апелляция как законченная форма | `web/cqa.css`, `web/src/ui/appeal-modal.ts`, `web/src/i18n.ts`, CSS+TS | Средний; dialog focus и повтор submit | Chat route, 1440/390: modal не шире viewport, Escape возвращает focus, пустой submit связан с полем, loading не допускает повтор. В отдельном разрешённом store отправка создаёт одну апелляцию |
| 8 | Review от доказательства к решению | `web/cqa.css`, `web/src/views/review.ts`, `web/src/i18n.ts`, CSS+TS | Высокий; demo-цепочка | `#/review`, 1440/390: пустое состояние со ссылкой; на разрешённом тестовом store evidence перед mobile-формой, reason обязателен; confirm/change показывает пересчитанный total, результат отражает original→decision→final |
| 9 | Чек-листы и редактор без сжатых полей | `web/cqa.css`, `web/src/views/checklists.ts`, `web/src/views/checklist-editor.ts`, `web/src/i18n.ts`, CSS+TS | Высокий; версия и draft | `#/checklists`, `#/checklists/chat`, 1440/390: версия списка видна, название раздела читается, savebar не закрывает Tab-focus; один Save создаёт одну новую версию в разрешённом store, старая read-only, затем работает "Переоценить" |
| 10 | Читаемая аналитика и настоящие ссылки | `web/cqa.css`, `web/src/views/analytics.ts`, `web/src/i18n.ts`, CSS+TS | Средний; асинхронные URL | `#/analytics/DEV`, 1440/390: четыре KPI, все значения, четыре histogram ranges, RU/KZ/EN и gross-list сохранены; полосы ≥3:1 к track; gross-link открывает нужную evaluation в новой вкладке |
| 11 | Лицензированный Noto Sans без CDN | `web/cqa.css`, отдельный font CSS web resource и подключающий HTML по существующей упаковке, CSS/assets | Средний; CSP и вес файла | Все семь маршрутов, 1440/390, обычный и blocked-font режим: `ӘәҒғҚқҢңӨөҰұҮүҺһІі` видимы, line-wrap без overflow, ресурс <лимита tenant, нет внешнего font request. При запрете data работает fallback |
| 12 | Финальная проверка матрицы и фиксация stop-code | Существующие UI-tests/скриншоты и `docs/demo.md`, verification/docs, без нового поведения | Низкий при наличии времени; не начинать переработку | Все семь маршрутов + modal, 1440/390, 200% zoom, keyboard, reduced-motion; на отдельном store полный demo appeal→review→recomputed total и checklist edit→version→reevaluate. Зафиксировать ограничения fake audio и D365, не объявлять непроверенное пройденным |

Для шагов 7–9 финальный end-to-end выполняется только в отдельном разрешённом store/fixture. Исследовательский сервер 8791 для этого не использовать. До пункта 11 UI остаётся согласованным на system fallback, поэтому подключение шрифта не является условием работающего demo. До пункта 4 локальный scroll пункта 3 сохраняет все колонки и выбор, хотя это ещё не конечная мобильная композиция.

## 8. Риски и решения для пользователя

| Решение | Рекомендованный default | Почему / ограничение |
|---|---|---|
| Светлый или тёмный sidebar | Светлый | Совпадает с измеренными Bank/Broker reference и не отнимает внимание у красных/amber результатов. Не вводить theme toggle до stop-code |
| Насколько буквально копировать Broker | Только цвета, форма и маленькая gradient-line | Большие заголовки, hero, 3D, градиентные CTA мешают Operate и имеют контрастные ловушки |
| Логотип Freedom | Только предоставленный/одобренный SVG; до этого текст CQA | Не скачивать случайную эмблему и не выдавать приблизительную геометрию за официальную. После одобрения brandmark занимает то же место без смены навигации |
| Noto и размер CSS | Полный проверенный Noto через data CSS, optional для demo | Пакет измерен, лицензия включена. При строгом CSP оставить system fallback; не ослаблять tenant security ради начертания |
| Мобильная работа | Поддерживать чтение, review и редактирование, не делать phone read-only | Нельзя убрать demo-critical действия ради красивого первого экрана. Риск сложных форм закрывается явными labels и 44 px targets |
| Кольцо и пороги | Сохранить текущее кольцо и числа | Это требование demo, а не необязательная декорация. Не менять scoring thresholds во время redesign |
| Непустой review | Проверить отдельно на разрешённых данных | Live queue сейчас пустая. Макет непустой очереди основан на коде и помечен [INFERENCE], не на сфабрикованном снимке |
| Аудио 0:00 | Честный статус fixture, отдельная разрешённая запись для seek acceptance | Не рисовать waveform или длительность, которых сервер не дал |
| 65 строк и performance | Без виртуализации перед дедлайном | Исследование не измеряло проблемы производительности; новая виртуализация создаст риск для select-all, Tab и скринридера |
| Ошибки/загрузка | Сохранять существующий контент и ввод | Не заменять ошибку пустой таблицей или успешным toast. Статические skeleton только до первой загрузки |
| D365 iframe | Проверять внутри фактической ширины web resource | viewport breakpoints приложения относятся к iframe, не к окну CRM. Tenant CSP, размер ресурса и screen reader внутри host пока не подтверждены |
| Срок | Поставлять пункты последовательно, не начинать незавершаемый TS-шаг | Завершённая меньшая поставка предпочтительнее частично переставленного review/editor. Полная спецификация остаётся целевой, урезание согласуется явно |

## 9. Журнал навыков и проверок

### Прочитано

- `C:/Users/sydyk/.agent/skills/ui-ux-pro-max/SKILL.md`.
- `C:/Users/sydyk/.agents/skills/impeccable/SKILL.md` и `reference/critique.md`, `audit.md`, `operate.md`, `mode-operate.md`, `craft-floor.md`.
- `C:/Users/sydyk/.agents/skills/refactoring-ui/SKILL.md`.
- `C:/Users/sydyk/.agents/skills/web-design-guidelines/SKILL.md`.
- `skill://using-superpowers`, `skill://unslop`, `skill://research`, `skill://brainstorming`. Для delegated research approval/commit-процедуры не применялись: задача прямо запрещает implementation/commit и уже разрешает throwaway prototype. Отдельный план или документация вне назначенной папки не создавались.

### Команды и запросы

```text
.venv/Scripts/python.exe C:/Users/sydyk/.agent/skills/ui-ux-pro-max/scripts/search.py "enterprise banking QA dashboard" --design-system
.venv/Scripts/python.exe C:/Users/sydyk/.agent/skills/ui-ux-pro-max/scripts/search.py "responsive data table keyboard" --domain ux
.venv/Scripts/python.exe C:/Users/sydyk/.agent/skills/ui-ux-pro-max/scripts/search.py "internal analytics dashboard" --design-system
C:/Users/sydyk/.agents/skills/impeccable/scripts/impeccable context --target web/cqa.css
cmd.exe /d /s /c C:\Users\sydyk\.agents\skills\impeccable\scripts\impeccable.cmd detect --json web/src
.venv/Scripts/python.exe -c "import importlib.util; print(importlib.util.find_spec('fontTools')); print(importlib.util.find_spec('brotli'))"
node docs/internal/redesign/proposals/astra/capture-prototype.cjs
node docs/internal/redesign/proposals/astra/evidence-tools.cjs
git status --short
```

- **ui-ux-pro-max:** первый design-system предложил Minimalism & Swiss и IBM Plex, но marketing-шаблон Trust & Authority с Contact Sales не подходит внутреннему QA. Повтор с `internal analytics dashboard` дал Data-Dense Dashboard, но снова Enterprise Gateway/Contact Sales; этот layout и сине-золотая палитра отклонены. Взяты density, tabular scanning и отсутствие декоративной анимации. Targeted UX-запрос вернул Table Handling и Bulk Actions: приняты wrapper/card-row и сохранение multiselect. Совет об autoplay video нерелевантен и не использован.
- **impeccable:** приняты Operate, один font, знакомые native controls, функциональные state colors, отсутствие маркетингового hero. `context` через shell не запустился из-за CRLF: `set: invalid option`, затем syntax error. Выполнен fallback: поиск `PRODUCT.md;DESIGN.md`, файлов нет. Детектор через Windows `.cmd` завершился 0 с `[]`. Это статический детектор по динамическому TypeScript, а не доказательство отсутствия accessibility-дефектов. Browser overlay не запускался. Полный двухагентный critique не заявлен; отдельный независимый proposal является назначенной работой. Craft-floor не использован как повод удалить обязательный score ring.
- **refactoring-ui:** применены ограниченная шкала размеров, числовая иерархия, отделение data от labels, одна глубина на секцию. Отклонены предложения про большие marketing-отступы, иллюстрации empty state и несколько font families. Текущая диагностическая оценка объяснена в разделе 2.
- **web-design-guidelines:** свежий источник получен через read: [command.md](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md). Применены accessible names, native semantics, focus not obscured, real href, tabular numerals, mobile overflow и сохранение ввода при ошибке. Английский Title Case и типографские указания не переносились механически на русскую UI-копию. Не добавлялись React/Tailwind или virtualization только потому, что они упомянуты в guidelines.
- **research:** использованы первичные OFL/metadata Google Fonts, binary cmap, Microsoft Learn, измеренный reference. Наличие `cyrillic-ext` не принято за доказательство поддержки казахского. `fontTools` и `brotli` в venv отсутствуют; пакеты не устанавливались, использован небольшой cmap parser.
- **unslop:** текст проверен вручную на рекламные утверждения, неподтверждённые "готово" и пустые рекомендации. `skill://unslop/linter/README.md` отсутствует, поэтому автоматический prose-linter не заявлен выполненным.

Финальная проверка артефактов включает наличие девяти разделов, существование ссылок на исходники и допустимость номеров строк, вычисления контраста и Git status. Build, lint, unit tests, mutation end-to-end и D365 smoke не запускались: это фаза исследования. Исходный Git status до работы уже содержал untracked `docs/CQA_Hackathon_Student_Guide_v3.pdf`, `docs/Data_pres.pdf`, `docs/internal/redesign/`. Все созданные этой работой файлы находятся в `docs/internal/redesign/proposals/astra/`; изменения соседнего proposal не являются изменениями Astra.
