from server.models import Checklist, Criterion, Record
from server.scoring import allowed_verdicts

_LABELS = {'yes': 'Да', 'no': 'Нет', 'na': 'N/A'}

_RULES = """\
Ты — эксперт по контролю качества контакт-центра Freedom Broker. Оцениваешь работу ОПЕРАТОРА по чек-листу.

Участники диалога
- operator — оператор. Оценивается только работа оператора.
- client — клиент. Его реплики служат контекстом.
- bot и system — бот и системные сообщения. Это контекст: их действия оператору не засчитываются и не ставятся в вину.
Ссылаться можно на любую реплику транскрипта, включая реплики бота и системные сообщения.

Правила ответа
1. По каждому критерию сначала найди подтверждающие реплики и только потом выставляй вердикт.
2. Ссылайся на реплики ТОЛЬКО по их номеру [idx] из транскрипта; номера пиши в evidence_idx.
3. explanation — 1–2 предложения на русском языке. Короткие фрагменты цитируй на языке оригинала диалога.
4. «Нет» за действие, которое было нужно, но не выполнено: evidence_idx может быть пустым, а в expected_range = [from, to] укажи номера реплик, где действие ожидалось. В остальных случаях expected_range = null.
5. N/A: заполни na_reason — какое условие N/A выполнено. В остальных случаях na_reason = null.
6. В verdict пиши код вердикта из списка допустимых: "yes" — «Да», "no" — «Нет», "na" — N/A, число — ступень шкалы.

Порядок N/A
N/A ставь ТОЛЬКО если критерий его допускает И его условие N/A буквально выполнено. Иначе отвечай «Да», «Нет» или ступенью шкалы. «Нет» означает, что действие было нужно, но оператор его пропустил или выполнил неправильно.

Шкалы
Выбирай только одну из перечисленных ступеней.

Строгость
Не будь снисходительным. Если есть сомнение и нет подтверждающей реплики, ставь «Нет» или более низкую ступень.

Грубые ошибки
Для критериев типа «грубая ошибка» «Да» означает, что найдено хотя бы одно нарушение; укажи эти реплики в evidence_idx. «Нет» доказательств не требует.
"""


def _verdict_line(c: Criterion, verdict: str) -> str:
    if verdict in _LABELS:
        return f'- "{verdict}" — {_LABELS[verdict]}'
    step = next(s for s in c.steps or [] if str(s.value) == verdict)
    return f'- "{verdict}" — {step.description}'


def _criterion_block(c: Criterion, sections: dict[str, str]) -> str:
    answer_type = 'Да/Нет' if c.answer_type == 'yes_no' else 'шкала'
    if c.kind == 'gross_error':
        answer_type += ', грубая ошибка (без баллов)'
    na = f'Условие N/A: {c.na_condition}' if c.na_allowed else 'N/A не допускается.'
    lines = [
        f'### {c.id}. {c.title}',
        f'Раздел: {sections.get(c.section_id or "", "—")}',
        f'Описание: {c.description}',
        f'Тип ответа: {answer_type}',
        'Допустимые вердикты:',
        *(_verdict_line(c, v) for v in allowed_verdicts(c)),
        na,
    ]
    return '\n'.join(lines)


def _system(checklist: Checklist, criterion_ids: list[str]) -> str:
    by_id = {c.id: c for c in checklist.criteria}
    sections = {s.id: s.title for s in checklist.sections}
    blocks = '\n\n'.join(_criterion_block(by_id[cid], sections) for cid in criterion_ids)
    return f'{_RULES}\nПравила чек-листа\n{checklist.notes}\n\nКритерии\n\n{blocks}\n'


def _user(record: Record, criterion_ids: list[str]) -> str:
    header = (
        f'Канал: {record.channel}; язык диалога: {record.language}; '
        f'диалог: {record.conversation_id}'
    )
    turns = [
        f'[{t.idx}] ({t.timestamp}) {t.speaker}: {" ".join(t.text.splitlines())}'
        for t in record.transcript
    ]
    last = f'Верни JSON строго по схеме для критериев: {", ".join(criterion_ids)}'
    return '\n'.join([header, '', 'Транскрипт:', *turns, '', last])


def build_messages(record: Record, checklist: Checklist, criterion_ids: list[str]) -> list[dict]:
    return [
        {'role': 'system', 'content': _system(checklist, criterion_ids)},
        {'role': 'user', 'content': _user(record, criterion_ids)},
    ]
