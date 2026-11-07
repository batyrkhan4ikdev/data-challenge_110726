"""Organizer submission file `results/<dev|prod>/results.json` (CQA Student Guide appendix, format 1.0).

Maps our evaluations onto the fixed schema: named criterion codes, `true`/`false`/`null` values, scale
points as numbers before weighting, and `evidence_turns` numbered from 1 over the raw transcript array.
"""

from collections.abc import Iterable, Mapping
from typing import Any

from server.config import Profile
from server.models import Evaluation

SCHEMA_VERSION = '1.0'

# Default checklist ids -> appendix criterion codes, in appendix order.
CODES: dict[str, str] = {
    'c01': 'contact',
    'c02': 'discovery',
    'c03': 'identification',
    'c04': 'consultation',
    'c05': 'empathy',
    'c06': 'dialogue',
    'c07': 'closure',
    'c08': 'critical',
}

# Allowed values per code, from the appendix table. `None` = N/A.
ALLOWED: dict[str, tuple[Any, ...]] = {
    'contact': (True, False),
    'discovery': (True, False, None),
    'identification': (True, False, None),
    'consultation': (0, 5, 10, 15, 20, None),
    'empathy': (True, False),
    'dialogue': (0, 4, 7, 10),
    'closure': (True, False, None),
    'critical': (True, False),
}


def _value(verdict: str) -> bool | int | float | None:
    match verdict:
        case 'yes':
            return True
        case 'no':
            return False
        case 'na':
            return None
    number = float(verdict)
    return int(number) if number.is_integer() else number


def model_block(profiles: Iterable[Profile]) -> dict[str, str]:
    """`model` object: mode is local / external_api, or hybrid when both kinds scored dialogs."""
    used = sorted({p.name: p for p in profiles}.values(), key=lambda p: p.name)
    modes = {p.hosting for p in used}
    mode = modes.pop() if len(modes) == 1 else 'hybrid'
    return {'mode': mode, 'name': ', '.join(dict.fromkeys(p.model for p in used))}


def result_entry(ev: Evaluation) -> dict[str, Any]:
    by_id = {i.criterion_id: i for i in ev.items}
    missing = [cid for cid in CODES if cid not in by_id]
    if missing:
        raise ValueError(f'{ev.conversation_id}: evaluation lacks criteria {missing} (non-default checklist?)')
    criteria = [
        {
            'criterion_id': code,
            'value': _value(by_id[cid].verdict),
            'rationale': by_id[cid].explanation,
            'evidence_turns': [i + 1 for i in by_id[cid].evidence_idx],
        }
        for cid, code in CODES.items()
    ]
    return {
        'conversation_id': ev.conversation_id,
        'status': 'ok',
        'criteria': criteria,
        'score': {'final_score': ev.score.total, 'critical_flag': ev.score.gross_error},
    }


def error_entry(conversation_id: str, error: str) -> dict[str, Any]:
    return {'conversation_id': conversation_id, 'status': 'error', 'criteria': [], 'score': None, 'error': error}


def build(
    team_name: str,
    conversation_ids: list[str],
    evaluations: Mapping[str, Evaluation],
    failed: Mapping[str, str],
    profiles: Mapping[str, Profile],
) -> dict[str, Any]:
    """One entry per id in dataset order; dialogs without an evaluation become `status: error`."""
    results = []
    for cid in conversation_ids:
        ev = evaluations.get(cid)
        if ev is not None:
            results.append(result_entry(ev))
        else:
            results.append(error_entry(cid, failed.get(cid) or 'Оценка не получена.'))
    used = [profiles[ev.profile] for ev in evaluations.values()]
    return {
        'schema_version': SCHEMA_VERSION,
        'team_name': team_name,
        'model': model_block(used),
        'results': results,
    }


def validate(doc: Mapping[str, Any], expected_ids: Iterable[str] | None = None) -> list[str]:
    """Return problems against the appendix rules; empty means the file is valid."""
    problems: list[str] = []
    if doc.get('schema_version') != SCHEMA_VERSION:
        problems.append(f'schema_version must be {SCHEMA_VERSION!r}')
    if not str(doc.get('team_name') or '').strip():
        problems.append('team_name is empty')
    model = doc.get('model') or {}
    if model.get('mode') not in ('local', 'external_api', 'hybrid') or not str(model.get('name') or '').strip():
        problems.append('model needs mode local|external_api|hybrid and a name')
    results = doc.get('results')
    if not isinstance(results, list):
        return [*problems, 'results must be a list']

    seen: set[str] = set()
    for n, r in enumerate(results):
        cid = r.get('conversation_id')
        where = f'results[{n}] {cid}'
        if not isinstance(cid, str) or not cid:
            problems.append(f'{where}: conversation_id missing')
        elif cid in seen:
            problems.append(f'{where}: duplicate conversation_id')
        seen.add(cid)
        if r.get('status') == 'error':
            if r.get('criteria') != [] or r.get('score') is not None or not r.get('error'):
                problems.append(f'{where}: error entry needs criteria [], score null and an error message')
            continue
        if r.get('status') != 'ok':
            problems.append(f'{where}: status must be ok or error')
            continue
        codes = [c.get('criterion_id') for c in r.get('criteria', [])]
        if sorted(codes) != sorted(ALLOWED):
            problems.append(f'{where}: needs each of the 8 criteria exactly once, got {codes}')
        values: dict[str, Any] = {}
        for c in r.get('criteria', []):
            code, value = c.get('criterion_id'), c.get('value')
            values[code] = value
            allowed = ALLOWED.get(code, ())
            # bool is an int subclass: True must not pass as 1 for scales, nor 0 as False.
            if not any(value is a if a is None or isinstance(a, bool) else (type(value) is int and value == a)
                       for a in allowed):
                problems.append(f'{where}: {code} value {value!r} not in {allowed}')
            turns = c.get('evidence_turns')
            if not isinstance(turns, list) or any(type(t) is not int or t < 1 for t in turns):
                problems.append(f'{where}: {code} evidence_turns must be integers >= 1')
            if not str(c.get('rationale') or '').strip():
                problems.append(f'{where}: {code} rationale is empty')
        score = r.get('score') or {}
        final = score.get('final_score')
        if type(final) not in (int, float) or not 0 <= final <= 100 or round(final, 2) != final:
            problems.append(f'{where}: final_score must be a number 0..100 with at most 2 decimals')
        if score.get('critical_flag') is not values.get('critical'):
            problems.append(f'{where}: critical_flag must equal the critical value')
    if expected_ids is not None:
        expected = list(expected_ids)
        lost = [i for i in expected if i not in seen]
        extra = sorted(seen - set(expected))
        if lost:
            problems.append(f'missing conversation_ids: {lost}')
        if extra:
            problems.append(f'unexpected conversation_ids: {extra}')
    return problems
