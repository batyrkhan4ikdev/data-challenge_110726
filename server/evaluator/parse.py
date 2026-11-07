import json
from typing import Any

from server.models import Checklist, Criterion, Item, Record
from server.scoring import allowed_verdicts


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _load(text: str) -> Any:
    start, end = text.find('{'), text.rfind('}')
    if start < 0 or end < start:
        raise ValueError('в ответе нет JSON-объекта')
    return json.loads(text[start : end + 1])


def _check(raw: Any, c: Criterion, n: int) -> Item | str:
    if not isinstance(raw, dict):
        return 'значение критерия не является объектом'
    verdict = raw.get('verdict')
    allowed = allowed_verdicts(c)
    if verdict not in allowed:
        return f'недопустимый вердикт {verdict!r}; допустимо: {", ".join(allowed)}'
    explanation = raw.get('explanation')
    if not isinstance(explanation, str):
        return 'explanation должен быть строкой'
    evidence = raw.get('evidence_idx')
    if not isinstance(evidence, list) or not all(_is_int(i) for i in evidence):
        return 'evidence_idx должен быть массивом целых чисел'
    for i in evidence:
        if not 0 <= i < n:
            return f'evidence_idx {i} вне диапазона реплик 0..{n - 1}'
    expected = raw.get('expected_range')
    if expected is not None:
        if not (isinstance(expected, list) and len(expected) == 2 and all(_is_int(i) for i in expected)):
            return 'expected_range должен быть парой целых чисел [from, to] или null'
        a, b = expected
        if not 0 <= a <= b < n:
            return f'expected_range {expected} некорректен: нужно 0 ≤ from ≤ to ≤ {n - 1}'
    na_reason = raw.get('na_reason')
    if na_reason is not None and not isinstance(na_reason, str):
        return 'na_reason должен быть строкой или null'

    gross = c.kind == 'gross_error'
    if verdict == 'na':
        if not (na_reason or '').strip():
            return 'для N/A нужно указать na_reason'
    elif verdict == 'no':
        if not gross and not evidence and expected is None:
            return 'для «Нет» нужны evidence_idx или expected_range'
    elif not evidence:
        what = 'для «Да» по грубой ошибке' if gross else f'для вердикта {verdict!r}'
        return f'{what} нужны непустые evidence_idx'

    return Item(
        criterion_id=c.id,
        verdict=verdict,
        explanation=explanation,
        evidence_idx=sorted(set(evidence)),
        expected_range=tuple(expected) if expected is not None else None,
        na_reason=na_reason,
        votes={},
    )


def parse_items(
    text: str, record: Record, checklist: Checklist, criterion_ids: list[str]
) -> tuple[dict[str, Item], dict[str, str]]:
    try:
        data = _load(text)
    except ValueError as e:
        return {}, {cid: f'невалидный JSON: {e}' for cid in criterion_ids}

    by_id = {c.id: c for c in checklist.criteria}
    n = len(record.transcript)
    items: dict[str, Item] = {}
    errors: dict[str, str] = {}
    for cid in criterion_ids:
        if cid not in data:
            errors[cid] = 'критерий отсутствует в ответе'
            continue
        result = _check(data[cid], by_id[cid], n)
        if isinstance(result, Item):
            items[cid] = result
        else:
            errors[cid] = result
    return items, errors
