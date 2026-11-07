"""ASR result -> masked, role-labelled `Record` in the shape of the organizer transcript.

One LLM call per chunk of ~60 segments assigns the role (operator / client / bot) and returns the masked text. A regex
safety net then removes any digit run that survived, consecutive same-role segments are merged, and the base record's
system events are copied back in at the matching audio time (the recording pause is taken into account).
"""

from __future__ import annotations

import asyncio
import json
import re
from collections import Counter
from datetime import datetime, timedelta
from typing import Any

from server.asr.base import AsrError, AsrResult, AsrSegment
from server.config import Profile
from server.dataset import _parse_iso
from server.llm.client import LLMClient, LLMError, make_client
from server.models import Record, Turn

CHUNK_SEGMENTS = 60
CHUNK_CHARS = 3500  # keeps the answer (the masked text is returned in full) inside the profile's max_tokens
CONTEXT_ROLES = 3
MAX_SEGMENT_CHARS = 600  # a longer segment is split into sentences before the LLM pass (a long answer gets truncated)
MIN_KEPT_RATIO = 0.7  # masking may shrink the text by names and numbers, not by a third
ATTEMPTS = 2
ROLES = ('operator', 'client', 'bot')
FALLBACK_CHARS_PER_S = 14.0  # speaking rate used to place segments of a provider with no timestamps when no duration is known

MASK_NAME = '[Имя скрыто]'
MASK_PD = '[Персональные данные скрыты]'
MASK_ID = '[Данные идентификации скрыты]'

_DIGIT_RUN = re.compile(r'\+?\d{4,}')
_DIGIT_GROUPS = re.compile(r'\+?(?<!\d)\d{1,4}(?:[ \-–]{1,2}\(?\d{1,4}\)?){2,}(?!\d)')
_PHONE_PARENS = re.compile(r'\+?\d{1,2}\s?\(\d{2,4}\)[\d\s\-–]{5,}')

SYSTEM_PROMPT = f"""Ты размечаешь расшифровку телефонного звонка в службу поддержки брокера Freedom Broker (автоматическое распознавание речи, с ошибками). Тебе дают пронумерованные фрагменты. Для КАЖДОГО фрагмента верни роль и текст с замаскированными персональными данными.

Роли:
- operator: сотрудник Freedom Broker. Представляется («Фридом брокер, меня зовут …»), задаёт вопросы для идентификации клиента, консультирует. Коллеги оператора, подключившиеся к разговору, тоже operator.
- client: звонящий клиент.
- bot: автоответчик, IVR, голосовой робот: приветствие компании, меню, «нажмите», «пожалуйста, оставайтесь на линии», музыка и записи на казахском или русском до подключения оператора.
Если у фрагмента есть метка говорящего (speaker-N, A, Оператор …), опирайся на неё: один говорящий — одна роль. Если меток нет, определяй роль по содержанию и по ходу диалога (вопрос — ответ, оператор ведёт разговор). Перед фрагментами показаны роли последних реплик предыдущей части разговора.

Маскирование в masked_text. Всё остальное оставь БЕЗ изменений, слово в слово, с теми же ошибками распознавания, ничего не исправляй, не переводи, не пересказывай и не удаляй:
- имена и фамилии людей (клиента, оператора, коллег, третьих лиц) → {MASK_NAME};
- ИИН, номера телефонов, карт, счетов, договоров, поручений и заявок, коды из СМС (OTP), пароли, адреса и их части (улица, номер дома и квартиры, в том числе названные словами: «дом двадцать, квартира пять»), город проживания клиента, дата рождения → {MASK_PD};
- то же самое, если это ответ клиента на просьбу идентифицироваться (назвать ИИН, кодовое слово, дату рождения, последние цифры и т.п.) → {MASK_ID};
- числа и коды, названные словами («семь семьсот …»), тоже маскируются, если это такие данные.
Суммы, названия тикеров, компаний, продуктов и тарифов не маскируй.
Верни ровно по одной записи на каждый номер фрагмента, номера i такие же, как во входе."""

SCHEMA: dict[str, Any] = {
    'type': 'object',
    'properties': {
        'segments': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'i': {'type': 'integer'},
                    'role': {'type': 'string', 'enum': list(ROLES)},
                    'masked_text': {'type': 'string'},
                },
                'required': ['i', 'role', 'masked_text'],
                'additionalProperties': False,
            },
        }
    },
    'required': ['segments'],
    'additionalProperties': False,
}


LEAK_SCHEMA: dict[str, Any] = {
    'type': 'object',
    'properties': {
        'findings': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'quote': {'type': 'string'},
                    'kind': {'type': 'string', 'enum': ['name', 'id_number', 'phone', 'address', 'other']},
                },
                'required': ['quote', 'kind'],
                'additionalProperties': False,
            },
        }
    },
    'required': ['findings'],
    'additionalProperties': False,
}
LEAK_PROMPT = f"""Ты проверяешь, что в расшифровке звонка не осталось персональных данных. Персональные данные уже заменены метками {MASK_NAME}, {MASK_PD} и {MASK_ID}. Найди то, что осталось НЕ замаскированным:
- имена, фамилии и отчества людей, в том числе искажённые распознаванием (name);
- ИИН, номера документов, карт, счетов, договоров, заявок, коды из СМС, в том числе названные словами или частями (id_number);
- номера телефонов (phone);
- адреса, улицы, дома, город проживания клиента (address).
Названия компаний (Freedom Broker, Фридом), тикеры, суммы, названия продуктов, общие слова и сами метки в скобках — не персональные данные. Имя оператора, который представляется в начале разговора, разрешено: его не указывай.
Для каждой находки верни quote — точная цитата из текста (1-5 слов) — и kind. Если ничего нет, верни пустой список."""
SCRUB_ROUNDS = 3


# ---------------------------------------------------------------- pure helpers

def split_long_segments(segments: list[AsrSegment]) -> list[AsrSegment]:
    """Split segments over MAX_SEGMENT_CHARS into sentences (or word runs); times are interpolated by text position."""
    out: list[AsrSegment] = []
    for seg in segments:
        if len(seg.text) <= MAX_SEGMENT_CHARS:
            out.append(seg)
            continue
        pieces: list[str] = []
        for sentence in re.split(r'(?<=[.!?…])\s+', seg.text.strip()):
            words = sentence.split()
            run: list[str] = []
            for w in words:
                if run and len(' '.join(run)) + 1 + len(w) > MAX_SEGMENT_CHARS * 2 // 3:
                    pieces.append(' '.join(run))
                    run = []
                run.append(w)
            if run:
                pieces.append(' '.join(run))
        # sentences are small, so merge neighbours up to a third of the cap to avoid hundreds of tiny fragments
        merged: list[str] = []
        for piece in pieces:
            if merged and len(merged[-1]) + 1 + len(piece) <= MAX_SEGMENT_CHARS // 3:
                merged[-1] = f'{merged[-1]} {piece}'
            else:
                merged.append(piece)
        total = sum(len(p) for p in merged) or 1
        done = 0
        for piece in merged:
            frac = done / total
            start = end = None
            if seg.start is not None and seg.end is not None:
                start = seg.start + (seg.end - seg.start) * frac
                end = seg.start + (seg.end - seg.start) * (done + len(piece)) / total
            elif seg.start is not None:
                start = seg.start
            out.append(AsrSegment(start=start, end=end, speaker=seg.speaker, text=piece))
            done += len(piece)
    return out


def mask_digits(text: str) -> str:
    """Safety net: no run of 4+ digits survives; spaced / dashed / bracketed digit groups of 7+ digits (phones) go too."""

    def groups(m: re.Match[str]) -> str:
        return MASK_PD if sum(c.isdigit() for c in m.group()) >= 7 else m.group()

    text = _PHONE_PARENS.sub(MASK_PD, text)
    text = _DIGIT_GROUPS.sub(groups, text)
    return _DIGIT_RUN.sub(MASK_PD, text)


def merge_roles(items: list[tuple[str, float, str]]) -> list[tuple[str, float, str]]:
    """Merge consecutive same-role (role, start, text) items; the merged item starts at the first one."""
    merged: list[tuple[str, float, str]] = []
    for role, start, text in items:
        if merged and merged[-1][0] == role:
            prev = merged[-1]
            merged[-1] = (role, prev[1], f'{prev[2]} {text}'.strip())
        else:
            merged.append((role, start, text))
    return merged


def segment_starts(segments: list[AsrSegment], duration_s: float | None) -> list[float]:
    """Start of every segment: the provider's own, or (providers with no timestamps) interpolated by text position."""
    total = sum(len(s.text) for s in segments) or 1
    span = duration_s if duration_s and duration_s > 0 else total / FALLBACK_CHARS_PER_S
    starts: list[float] = []
    done = 0
    last = 0.0
    for s in segments:
        if s.start is not None:
            t = float(s.start)
        else:
            t = span * done / total
        t = max(t, last)  # keep the order monotonic
        starts.append(t)
        last = t
        done += len(s.text)
    return starts


class _Clock:
    """Maps the audio timeline (seconds in the MP3) onto the conversation timeline of the base record.

    The organizer timeline is wall time from the first turn; the recording is paused while the call waits for an operator
    ('Запись и транскрибирование приостановлены' ... 'возобновлены'), so the audio is shorter than the conversation.
    """

    def __init__(self, base: Record) -> None:
        self.start_shift = 0.0
        self.pauses: list[tuple[float, float]] = []  # (wall start, wall end)
        opened: float | None = None
        started = False
        for t in base.transcript:
            if t.speaker != 'system' or t.offset_s is None:
                continue
            low = t.text.lower()
            if 'запущен' in low and not started:
                self.start_shift, started = t.offset_s, True
            elif 'приостановлен' in low and opened is None:
                opened = t.offset_s
            elif 'возобновлен' in low and opened is not None:
                self.pauses.append((opened, t.offset_s))
                opened = None

    def to_audio(self, wall: float) -> float:
        a = wall - self.start_shift
        for p, r in self.pauses:
            if wall >= r:
                a -= r - p
            elif wall > p:
                a -= wall - p
        return max(a, 0.0)

    def to_wall(self, audio: float) -> float:
        wall = audio + self.start_shift
        cum = 0.0
        for p, r in self.pauses:
            pause_audio_start = p - self.start_shift - cum
            if audio > pause_audio_start:
                wall += r - p
            cum += r - p
        return wall


def _base_t0(base: Record) -> datetime | None:
    for t in base.transcript:
        if 'T' in t.timestamp:
            try:
                return _parse_iso(t.timestamp)
            except ValueError:
                return None
        return None
    return None


def _clock_text(offset: float) -> str:
    return f'{int(offset) // 60:02d}:{int(offset) % 60:02d}'


# ---------------------------------------------------------------- LLM

def _parse_answer(text: str | None, wanted: set[int]) -> dict[int, tuple[str, str]]:
    if not text:
        return {}
    text = text.strip()
    if text.startswith('```'):
        text = re.sub(r'^```[a-zA-Z]*\s*|\s*```$', '', text)
    try:
        data = json.loads(text)
    except ValueError:
        return {}
    out: dict[int, tuple[str, str]] = {}
    for item in (data.get('segments') if isinstance(data, dict) else None) or []:
        if not isinstance(item, dict):
            continue
        i, role, masked = item.get('i'), item.get('role'), item.get('masked_text')
        if isinstance(i, int) and i in wanted and role in ROLES and isinstance(masked, str) and masked.strip():
            out[i] = (role, masked.strip())
    return out


def _user_message(items: list[tuple[int, AsrSegment, float]], prev_roles: list[str], known: dict[str, str]) -> str:
    lines = []
    if prev_roles:
        lines.append('Роли последних реплик предыдущей части: ' + ', '.join(prev_roles))
    if known:
        lines.append(
            'Метки говорящих, уже определённые в предыдущих частях (держись их, если метка явно не смешивает голоса): '
            + ', '.join(f'{label} = {role}' for label, role in known.items())
        )
    lines.append('Фрагменты:')
    for i, seg, start in items:
        label = f' ({seg.speaker})' if seg.speaker else ''
        lines.append(f'[{i}] {_clock_text(start)}{label} {seg.text}')
    return '\n'.join(lines)


async def _ask(
    llm: LLMClient, items: list[tuple[int, AsrSegment, float]], prev_roles: list[str], known: dict[str, str]
) -> dict[int, tuple[str, str]]:
    messages = [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': _user_message(items, prev_roles, known)},
    ]
    try:
        completions = await llm.complete(messages, SCHEMA, 0.0, 1)
    except LLMError as exc:
        raise AsrError(f'Разметка ролей не удалась: {exc}') from None
    return _parse_answer(completions[0].text if completions else None, {i for i, _, _ in items})


async def _label_chunk(
    llm: LLMClient, items: list[tuple[int, AsrSegment, float]], prev_roles: list[str], known: dict[str, str]
) -> dict[int, tuple[str, str]]:
    got: dict[int, tuple[str, str]] = {}
    for _ in range(ATTEMPTS):
        pending = [x for x in items if x[0] not in got]
        if not pending:
            return got
        got.update(await _ask(llm, pending, prev_roles, known))
    pending = [x for x in items if x[0] not in got]
    if not pending:
        return got
    if len(pending) == 1:
        raise AsrError(f'Модель не вернула разметку фрагмента {pending[0][0]}; безопасно замаскировать его нельзя')
    mid = len(pending) // 2  # a long or truncated answer: retry the missing part in smaller pieces
    got.update(await _label_chunk(llm, pending[:mid], prev_roles, known))
    got.update(await _label_chunk(llm, pending[mid:], prev_roles, known))
    return got


def _chunks(items: list[tuple[int, AsrSegment, float]]) -> list[list[tuple[int, AsrSegment, float]]]:
    chunks: list[list[tuple[int, AsrSegment, float]]] = []
    cur: list[tuple[int, AsrSegment, float]] = []
    chars = 0
    for item in items:
        if cur and (len(cur) >= CHUNK_SEGMENTS or chars + len(item[1].text) > CHUNK_CHARS):
            chunks.append(cur)
            cur, chars = [], 0
        cur.append(item)
        chars += len(item[1].text)
    if cur:
        chunks.append(cur)
    return chunks


async def find_leaks(llm: LLMClient, turns: list[Turn]) -> list[dict]:
    """Second pass over masked turns: personal data the first pass missed, as [{idx, kind, quote}]. AsrError if it cannot run."""
    lines = '\n'.join(f'[{t.idx}] {t.speaker}: {t.text}' for t in turns if t.speaker != 'system')
    messages = [{'role': 'system', 'content': LEAK_PROMPT}, {'role': 'user', 'content': lines}]
    last = ''
    findings: list = []
    for attempt in range(3):
        try:
            completions = await llm.complete(messages, LEAK_SCHEMA, 0.0, 1)
            findings = json.loads((completions[0].text or '').strip())['findings']
            break
        except Exception as exc:  # noqa: BLE001  a flaky network or a malformed answer: ask again
            last = type(exc).__name__
            await asyncio.sleep(2 * (attempt + 1))
    else:
        raise AsrError(f'Проверка маскирования не удалась ({last})')
    haystack = {t.idx: t.text.lower() for t in turns if t.speaker != 'system'}
    out = []
    for f in findings:
        quote = str(f.get('quote', '')).strip() if isinstance(f, dict) else ''
        if not quote or re.fullmatch(r'\[[^\]]*скрыт[^\]]*\]', quote):
            continue
        where = [i for i, text in haystack.items() if quote.lower() in text]
        if where:  # a quote that is not in the text is a hallucination
            out.append({'idx': where[0], 'kind': f.get('kind'), 'quote': quote})
    return out


async def scrub(llm: LLMClient, turns: list[Turn]) -> list[Turn]:
    """Mask what `find_leaks` still finds (names -> «[Имя скрыто]», anything else -> «[Персональные данные скрыты]»)."""
    for _ in range(SCRUB_ROUNDS):
        leaks = await find_leaks(llm, turns)
        if not leaks:
            break
        for leak in leaks:
            mask = MASK_NAME if leak['kind'] == 'name' else MASK_PD
            pattern = re.compile(re.escape(leak['quote']), re.IGNORECASE)
            turns = [
                t.model_copy(update={'text': pattern.sub(mask, t.text)}) if t.speaker != 'system' else t for t in turns
            ]
    return turns


async def asr_to_record(
    result: AsrResult, base: Record, profile: Profile, llm: LLMClient | None = None
) -> Record:
    segments = split_long_segments([s for s in result.segments if s.text.strip()])
    if not segments:
        raise AsrError('Пустой результат распознавания: нечего разбирать на реплики')
    llm = llm or make_client(profile)
    starts = segment_starts(segments, result.duration_s)
    items = [(i, seg, starts[i]) for i, seg in enumerate(segments)]

    labelled: dict[int, tuple[str, str]] = {}
    prev_roles: list[str] = []
    votes: dict[str, Counter[str]] = {}  # diarization label -> roles assigned so far
    for chunk in _chunks(items):
        known = {label: c.most_common(1)[0][0] for label, c in votes.items()}
        labelled.update(await _label_chunk(llm, chunk, prev_roles, known))
        prev_roles = [labelled[i][0] for i, _, _ in chunk][-CONTEXT_ROLES:]
        for i, seg, _ in chunk:
            if seg.speaker:
                votes.setdefault(seg.speaker, Counter())[labelled[i][0]] += 1

    kept = sum(len(labelled[i][1]) for i in range(len(segments)))
    original = sum(len(s.text) for s in segments)
    if kept < MIN_KEPT_RATIO * original:
        raise AsrError(
            f'Модель сократила текст звонка до {kept / original:.0%} при маскировании (порог {MIN_KEPT_RATIO:.0%}): '
            'часть речи потеряна'
        )
    merged = merge_roles([(labelled[i][0], starts[i], mask_digits(labelled[i][1])) for i in range(len(segments))])

    clock = _Clock(base)
    t0 = _base_t0(base)
    entries: list[tuple[float, int, Turn]] = []  # (audio time, 0 event / 1 asr turn, turn)
    for role, start, text in merged:
        wall = clock.to_wall(start)
        stamp = (t0 + timedelta(seconds=wall)).isoformat() if t0 else _clock_text(wall)
        entries.append((start, 1, Turn(idx=0, timestamp=stamp, offset_s=wall, speaker=role, text=text)))
    for t in base.transcript:
        if t.speaker == 'system' and t.offset_s is not None:
            entries.append((clock.to_audio(t.offset_s), 0, t.model_copy()))
    # stable sort: events before an ASR turn that starts at the same moment, base order kept among events
    entries.sort(key=lambda e: (e[0], e[1]))
    transcript = []
    for idx, (_, _, turn) in enumerate(entries):
        transcript.append(turn.model_copy(update={'idx': idx}))
    transcript = await scrub(llm, transcript)
    return Record(
        conversation_id=base.conversation_id,
        channel=base.channel,
        language=base.language,
        transcript=transcript,
        audio_url=base.audio_url,
    )
