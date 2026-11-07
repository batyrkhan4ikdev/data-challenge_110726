"""Детерминированные факты диалога по транскрипту (без LLM). Только для показа в UI."""

import re
from datetime import datetime

from server.models import DialogEvent, DialogFacts, MaskedToken, Record, Turn

SLA_S = 180
_MASKED = re.compile(r'\[[^\[\]]*скрыт[^\[\]]*\]', re.IGNORECASE)
_CLOCK = re.compile(r'^(?:(\d+):)?(\d{1,2}):(\d{2})$')
_ESCALATION = (
    'эскалация на оператора',
    'чат операторға жіберілді',
    'chat transferred to an agent',
    'агент присоединился к разговору',
)


def _seconds(turn: Turn) -> float | None:
    if turn.offset_s is not None:
        return turn.offset_s
    ts = turn.timestamp.strip()
    m = _CLOCK.match(ts)
    if m:
        h, mm, ss = m.groups()
        return int(h or 0) * 3600 + int(mm) * 60 + int(ss)
    try:
        return datetime.fromisoformat(ts.replace('Z', '+00:00')).timestamp()
    except ValueError:
        return None


def _is_escalation(text: str) -> bool:
    low = text.lower()
    return any(k in low for k in _ESCALATION)


def _is_verified(text: str) -> bool:
    low = text.lower()
    return 'verified' in low or 'верифицирован' in low


def dialog_facts(record: Record) -> DialogFacts:
    turns = record.transcript
    times = [_seconds(t) for t in turns]
    known = [x for x in times if x is not None]
    duration = max(0.0, known[-1] - known[0]) if len(known) >= 2 else None

    counts: dict[str, int] = {}
    masked: dict[str, MaskedToken] = {}
    events: list[DialogEvent] = []
    escalation: int | None = None
    verified: int | None = None
    for t, at in zip(turns, times):
        counts[t.speaker] = counts.get(t.speaker, 0) + 1
        for tok in _MASKED.findall(t.text):
            if tok in masked:
                masked[tok].count += 1
            else:
                masked[tok] = MaskedToken(token=tok, count=1, first_idx=t.idx)
        if t.speaker == 'system':
            events.append(DialogEvent(idx=t.idx, text=t.text, offset_s=t.offset_s))
            if escalation is None and _is_escalation(t.text):
                escalation = t.idx
            if verified is None and _is_verified(t.text):
                verified = t.idx

    # Старт отсчёта первой реакции: эскалация, иначе первая реплика клиента.
    start_pos: int | None = None
    for pos, t in enumerate(turns):
        if (escalation is not None and t.idx == escalation) or (escalation is None and t.speaker == 'client'):
            start_pos = pos
            break
    first_pos: int | None = None
    resp_s: float | None = None
    if start_pos is not None:
        for pos in range(start_pos + 1, len(turns)):
            if turns[pos].speaker == 'operator':
                first_pos = pos
                a, b = times[start_pos], times[pos]
                if a is not None and b is not None:
                    resp_s = max(0.0, b - a)
                break

    wait_s: float | None = None
    wait_idx: int | None = None
    if first_pos is not None:
        pending: float | None = None
        for pos in range(first_pos + 1, len(turns)):
            t, at = turns[pos], times[pos]
            if t.speaker == 'client' and pending is None and at is not None:
                pending = at
            elif t.speaker == 'operator' and pending is not None:
                if at is not None and (wait_s is None or at - pending > wait_s):
                    wait_s, wait_idx = max(0.0, at - pending), t.idx
                pending = None

    return DialogFacts(
        duration_s=duration,
        escalation_idx=escalation,
        first_response_s=resp_s,
        first_response_idx=turns[first_pos].idx if first_pos is not None and resp_s is not None else None,
        sla_s=SLA_S,
        sla_ok=None if resp_s is None else resp_s <= SLA_S,
        max_wait_s=wait_s,
        max_wait_idx=wait_idx,
        turns=counts,
        masked=list(masked.values()),
        events=events,
        identity_verified_idx=verified,
    )
