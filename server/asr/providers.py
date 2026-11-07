"""ASR providers: config loading, HTTP calls and response parsing."""

from __future__ import annotations

import asyncio
import base64
import os
import re
import time
import tomllib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from server.asr.audio import mp3_duration_s, split_mp3
from server.asr.base import AsrError, AsrResult, AsrSegment
from server.http import new_session

TIMEOUT_S = 600
ATTEMPTS = 3
RETRY_STATUSES = {429}
HEADERS = {'User-Agent': 'Mozilla/5.0 (cqa)'}  # Cloudflare in front of FreedomSpeech answers 1010 without a browser UA

# A pause this long between two words starts a new segment when a provider gives only word timestamps.
WORD_GAP_S = 0.8
SENTENCE_END = re.compile(r'[.!?…]["»)]*$')
LONG_SEGMENT_WORDS = 40
SPLIT_WORDS = 25

OPENROUTER_PROMPT = (
    'Это запись телефонного звонка в службу поддержки брокера Freedom Broker. Дословно расшифруй весь разговор '
    'на языке оригинала (русский и казахский), ничего не пропуская и не пересказывая. Каждая реплика на отдельной '
    'строке в формате `[Роль | мм:сс] текст`, где Роль: Оператор, Клиент или Бот (автоответчик, IVR), '
    'а мм:сс — время начала реплики от начала записи. Ничего, кроме этих строк, не пиши.'
)


class AsrProvider(BaseModel):
    name: str
    kind: Literal['openai_audio', 'freedomspeech', 'openrouter_audio']
    base_url: str | None = None
    base_url_env: str | None = None
    api_key_env: str | None = None
    model: str
    label: str  # Russian UI name
    hosting: Literal['local', 'external_api']
    enabled: bool = True
    extra: dict[str, Any] = {}  # kind-specific options: response_format, prompt
    extra_form: dict[str, Any] = {}  # additional multipart form fields, e.g. diarize = true
    extra_json: dict[str, Any] = {}  # JSON body mode (base64 input_audio) with these top-level fields, e.g. provider options
    timeout_s: float = TIMEOUT_S
    attempts: int = ATTEMPTS
    max_audio_s: float | None = None  # the endpoint rejects longer audio: the call is cut into equal pieces at frame boundaries
    # The endpoint takes a `language` field: a caller hint overrides `extra_form['language']`, and a Kazakh
    # re-run becomes possible. Measured on record `1234`: auto-detect lost a third of the words (config/asr.toml).
    accepts_language: bool = False

    def resolved_base_url(self) -> str | None:
        value = (os.environ.get(self.base_url_env) if self.base_url_env else None) or self.base_url
        return value.rstrip('/') if value else None

    def api_key(self) -> str | None:
        return (os.environ.get(self.api_key_env) or None) if self.api_key_env else None

    def missing_env(self) -> list[str]:
        missing = []
        if not self.resolved_base_url() and self.base_url_env:
            missing.append(self.base_url_env)
        if self.api_key_env and not self.api_key():
            missing.append(self.api_key_env)
        return missing

    def configured(self) -> bool:
        return not self.missing_env()


def load_asr_providers(path: Path = Path('config/asr.toml')) -> dict[str, AsrProvider]:
    with Path(path).open('rb') as f:
        tables = tomllib.load(f).get('providers', {})
    return {name: AsrProvider(name=name, **table) for name, table in tables.items()}


# ---------------------------------------------------------------- parsing (pure)

_SPEAKER_MARK = re.compile(r'\[\s*([^|\]]+?)\s*\|\s*([\d:.,]+)\s*-\s*([\d:.,]+)\s*\]')
_LABELED_LINE = re.compile(r'^\s*\[\s*([^|\]]+?)\s*(?:\|\s*([\d:.,]+)\s*)?\]\s*(.*?)\s*$')


def _seconds(value: str) -> float | None:
    """`12.5`, `1:02`, `01:02.5` or `1:01:02` -> seconds."""
    try:
        total = 0.0
        for part in value.replace(',', '.').split(':'):
            total = total * 60 + float(part)
        return total
    except ValueError:
        return None


def parse_diarized_text(text: str) -> list[AsrSegment]:
    """FreedomSpeech diarized_json: segment times are 0, the real ones are in `[speaker-N | start-end] text` markers
    (separated by a newline or just a space)."""
    marks = list(_SPEAKER_MARK.finditer(text))
    segments: list[AsrSegment] = []
    for n, m in enumerate(marks):
        end = marks[n + 1].start() if n + 1 < len(marks) else len(text)
        body = ' '.join(text[m.end() : end].split())
        if body:
            segments.append(AsrSegment(start=_seconds(m.group(2)), end=_seconds(m.group(3)), speaker=m.group(1), text=body))
    return segments


def parse_labeled_text(text: str) -> list[AsrSegment]:
    """LLM transcript: `[Оператор | 01:23] text` or `[Клиент] text` lines."""
    segments: list[AsrSegment] = []
    for line in text.splitlines():
        m = _LABELED_LINE.match(line)
        if m:
            speaker, start, body = m.groups()
            segments.append(AsrSegment(start=_seconds(start) if start else None, end=None, speaker=speaker, text=body))
        elif line.strip() and segments:
            segments[-1].text = f'{segments[-1].text} {line.strip()}'.strip()
    return [s for s in segments if s.text]


def _speaker_label(word: dict) -> str | None:
    sp = word.get('speaker')
    if sp is None or sp == '':
        return None
    return f'speaker-{sp}' if isinstance(sp, int) else str(sp)


def _segments_from_words(words: list[dict]) -> list[AsrSegment]:
    """Group words into segments: a new one at a pause of WORD_GAP_S, at sentence punctuation or when the speaker changes."""
    segments: list[AsrSegment] = []
    cur: list[dict] = []

    def flush() -> None:
        if cur:
            text = ' '.join(str(w.get('word', '')).strip() for w in cur).strip()
            if text:
                segments.append(
                    AsrSegment(start=cur[0].get('start'), end=cur[-1].get('end'), speaker=_speaker_label(cur[0]), text=text)
                )
            cur.clear()

    for w in words:
        if cur and (
            (w.get('start') or 0) - (cur[-1].get('end') or 0) >= WORD_GAP_S or _speaker_label(w) != _speaker_label(cur[-1])
        ):
            flush()
        cur.append(w)
        if SENTENCE_END.search(str(w.get('word', '')).strip()):
            flush()
    flush()
    return segments


def _segments_from_text(text: str) -> list[AsrSegment]:
    """No timestamps at all: split into sentences, long unpunctuated runs into ~25-word pieces."""
    pieces: list[str] = []
    for sentence in re.split(r'(?<=[.!?…])\s+', text.strip()):
        words = sentence.split()
        if len(words) > LONG_SEGMENT_WORDS:
            pieces.extend(' '.join(words[i : i + SPLIT_WORDS]) for i in range(0, len(words), SPLIT_WORDS))
        elif words:
            pieces.append(sentence.strip())
    return [AsrSegment(start=None, end=None, speaker=None, text=p) for p in pieces]


COARSE_SEGMENT_S = 12.0  # Whisper segments this long mix speakers; word timestamps, when present, split them better


def parse_openai_audio(data: dict) -> tuple[list[AsrSegment], bool]:
    """verbose_json -> segments. Words are used instead when they carry speaker labels, when `segments` is empty, or when the
    segments are coarse (long). Falls back to the sentences of `text` when there are no timestamps at all.
    The bool says whether the provider labelled speakers."""
    segments = [
        AsrSegment(start=s.get('start'), end=s.get('end'), speaker=_speaker_label(s), text=str(s.get('text') or '').strip())
        for s in (data.get('segments') or [])
        if isinstance(s, dict)
    ]
    segments = [s for s in segments if s.text]
    words = [w for w in (data.get('words') or []) if isinstance(w, dict) and str(w.get('word', '')).strip()]
    spans = [(s.end or 0) - (s.start or 0) for s in segments]
    coarse = bool(spans) and sum(spans) / len(spans) > COARSE_SEGMENT_S
    if words and (any(_speaker_label(w) for w in words) or not segments or coarse):
        from_words = _segments_from_words(words)
        if from_words:
            segments = from_words
    if not segments:
        segments = _segments_from_text(str(data.get('text') or ''))
    return segments, any(s.speaker for s in segments)


def parse_freedomspeech(data: dict) -> tuple[list[AsrSegment], bool]:
    segments = parse_diarized_text(str(data.get('text') or ''))
    if not segments:  # no `[speaker | s-e]` lines: take the segments as they are (times may be real in other deployments)
        segments = [
            AsrSegment(start=s.get('start'), end=s.get('end'), speaker=s.get('speaker'), text=str(s.get('text') or '').strip())
            for s in (data.get('segments') or [])
            if isinstance(s, dict) and str(s.get('text') or '').strip()
        ]
    return segments, any(s.speaker for s in segments)


# ---------------------------------------------------------------- HTTP

def _not_configured(provider: AsrProvider) -> AsrError:
    need = ', '.join(provider.missing_env())
    return AsrError(f'{provider.label} не настроен: задайте {need}')


async def _post(url: str, provider: AsrProvider, **kwargs: Any) -> Any:
    session = new_session()
    last = ''
    for attempt in range(provider.attempts):
        try:
            resp = await session.post(url, timeout=provider.timeout_s, **kwargs)
        except Exception as exc:
            last = f'сбой соединения: {type(exc).__name__}'
        else:
            if resp.status_code == 200:
                return resp
            body = (resp.text or '')[:200].replace('\n', ' ')
            last = f'HTTP {resp.status_code}: {body}'
            if not (resp.status_code in RETRY_STATUSES or resp.status_code >= 500):
                raise AsrError(f'{provider.label}: {last}')
        if attempt < provider.attempts - 1:
            await asyncio.sleep(2.0 * (attempt + 1))
    raise AsrError(f'{provider.label}: {last} (попыток: {provider.attempts})')


def _form_value(value: Any) -> str:
    return str(value).lower() if isinstance(value, bool) else str(value)


def _json(resp: Any, provider: AsrProvider) -> dict:
    try:
        data = resp.json()
    except Exception:
        raise AsrError(f'{provider.label}: ответ не JSON') from None
    if not isinstance(data, dict):
        raise AsrError(f'{provider.label}: неожиданная форма ответа')
    return data


async def _openai_audio(provider: AsrProvider, audio: bytes, filename: str, language: str | None = None) -> tuple[dict, list[AsrSegment], bool]:
    url = f'{provider.resolved_base_url()}/audio/transcriptions'
    response_format = str(provider.extra.get('response_format', 'verbose_json'))
    headers = dict(HEADERS)
    if provider.api_key():
        headers['Authorization'] = f'Bearer {provider.api_key()}'
    if provider.extra_json:
        # OpenRouter-style JSON body: base64 audio plus provider-specific options that multipart cannot carry
        fmt = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'mp3'
        body = {
            'model': provider.model,
            'input_audio': {'data': base64.b64encode(audio).decode(), 'format': fmt},
            'response_format': response_format,
            **provider.extra_json,
        }
        resp = await _post(url, provider, json=body, headers=headers)
    else:
        form = {'model': provider.model, 'response_format': response_format}
        form.update({k: _form_value(v) for k, v in provider.extra_form.items()})
        if language:
            form['language'] = language
        resp = await _post(url, provider, files={'file': (filename, audio, 'audio/mpeg')}, data=form, headers=headers)
    data = _json(resp, provider)
    segments, diarized = parse_openai_audio(data)
    return data, segments, diarized


async def _freedomspeech(provider: AsrProvider, audio: bytes, filename: str, language: str | None = None) -> tuple[dict, list[AsrSegment], bool]:
    host = (provider.resolved_base_url() or '').removesuffix('/v1')
    form = {'response_format': str(provider.extra.get('response_format', 'diarized_json')), 'prettify': 'false'}
    form.update({k: _form_value(v) for k, v in provider.extra_form.items()})
    headers = {**HEADERS, 'X-API-Key': provider.api_key() or ''}
    resp = await _post(
        f'{host}/v1/audio/transcriptions', provider, files={'file': (filename, audio, 'audio/mpeg')}, data=form, headers=headers
    )
    data = _json(resp, provider)
    segments, diarized = parse_freedomspeech(data)
    return data, segments, diarized


async def _openrouter_audio(provider: AsrProvider, audio: bytes, filename: str, language: str | None = None) -> tuple[dict, list[AsrSegment], bool]:
    fmt = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'mp3'
    body = {
        'model': provider.model,
        'temperature': 0,
        'messages': [
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': str(provider.extra.get('prompt') or OPENROUTER_PROMPT)},
                    {'type': 'input_audio', 'input_audio': {'data': base64.b64encode(audio).decode(), 'format': fmt}},
                ],
            }
        ],
    }
    headers = {**HEADERS, 'Content-Type': 'application/json', 'Authorization': f'Bearer {provider.api_key()}'}
    resp = await _post(f'{provider.resolved_base_url()}/chat/completions', provider, json=body, headers=headers)
    data = _json(resp, provider)
    try:
        text = str(data['choices'][0]['message']['content'] or '')
    except (KeyError, IndexError, TypeError):
        raise AsrError(f'{provider.label}: в ответе нет текста') from None
    segments = parse_labeled_text(text)
    if not segments:
        segments = _segments_from_text(text)
    return {'text': text}, segments, any(s.speaker for s in segments)


_KINDS = {'openai_audio': _openai_audio, 'freedomspeech': _freedomspeech, 'openrouter_audio': _openrouter_audio}


KAZAKH_LETTERS = frozenset('әғқңөұүһі')
KAZAKH_SHARE_MIN = 0.15  # below this a Russian transcript's stray «і»/«қ» would trigger a pointless re-run
_WORD = re.compile(r'[а-яёәғқңөұүһі]+')


def kazakh_share(text: str) -> float:
    """Share of words carrying a Kazakh-only letter. Russian text scores ~0; Kazakh speech scored 0.71."""
    words = _WORD.findall(text.lower())
    return sum(1 for w in words if KAZAKH_LETTERS & set(w)) / len(words) if words else 0.0


REPEAT_MIN = 5  # Whisper's decoding loop: on record 1234 it wrote «өте» 109 times in a row
_REPEAT = re.compile(r'(?<!\w)(\w+)(?:[\s,.!?…-]+\1(?!\w)){' + str(REPEAT_MIN - 1) + r',}', re.IGNORECASE)
REPEAT_MARK = '[…повтор распознавания убран]'


def collapse_repeats(text: str) -> tuple[str, int]:
    """Replaces a run of the same word repeated `REPEAT_MIN`+ times by one copy and a mark; (text, words removed).
    No speaker says a word five times in a row, a decoding loop does, and it would inflate both the word count and
    the Kazakh-letter share."""
    removed = 0

    def keep_one(m: re.Match[str]) -> str:
        nonlocal removed
        removed += len(m.group(0).split()) - 1
        return f'{m.group(1)} {REPEAT_MARK}'

    return _REPEAT.sub(keep_one, text), removed


async def transcribe(provider: AsrProvider, audio: bytes, filename: str = 'call.mp3', language: str | None = None) -> AsrResult:
    """`language`: ISO code for providers that take one (`accepts_language`); otherwise the provider's own default.

    An auto-detecting provider that comes back with Kazakh speech is re-run with `kk`: on record `1234` that
    recovered a third of the words. The dataset's `language` label is not trusted, only the audio.
    """
    result = await _transcribe_once(provider, audio, filename, language)
    if provider.accepts_language and (language or '').lower() != 'kk' and kazakh_share(result.text) >= KAZAKH_SHARE_MIN:
        forced = await _transcribe_once(provider, audio, filename, 'kk')
        if kazakh_share(forced.text) > kazakh_share(result.text):
            return forced.model_copy(update={'seconds': result.seconds + forced.seconds})
    return result


async def _transcribe_once(provider: AsrProvider, audio: bytes, filename: str, language: str | None) -> AsrResult:
    # `enabled` only decides what is offered and run by default; an explicitly requested provider is called.
    if not provider.configured():
        raise _not_configured(provider)
    started = time.perf_counter()
    parts = split_mp3(audio, provider.max_audio_s) if provider.max_audio_s else [(0.0, audio)]
    segments: list[AsrSegment] = []
    texts: list[str] = []
    diarized = False
    detected: str | None = None  # what the endpoint reports; `language` stays the request hint
    reported = 0.0
    for k, (offset, piece) in enumerate(parts):
        data, part_segments, part_diarized = await _KINDS[provider.kind](provider, piece, filename, language)
        for s in part_segments:  # pieces are transcribed separately: put their times back on the whole-call timeline
            segments.append(
                s.model_copy(
                    update={
                        'start': None if s.start is None else s.start + offset,
                        'end': None if s.end is None else s.end + offset,
                        # speaker labels are per piece and do not match across pieces: prefix them with the piece index
                        'speaker': f'p{k}:{s.speaker}' if s.speaker and len(parts) > 1 else s.speaker,
                    }
                )
            )
        texts.append(str(data.get('text') or '').strip() or '\n'.join(s.text for s in part_segments))
        diarized = diarized or part_diarized
        detected = detected or (data.get('language') if isinstance(data.get('language'), str) else None)
        duration = data.get('duration')
        reported += float(duration) if isinstance(duration, int | float) and duration > 0 else 0.0
    seconds = time.perf_counter() - started
    text, _ = collapse_repeats('\n'.join(t for t in texts if t))
    segments = [s.model_copy(update={'text': collapse_repeats(s.text)[0]}) for s in segments]
    if not segments or not text:
        raise AsrError(f'{provider.label}: пустой результат распознавания')
    return AsrResult(
        provider=provider.name,
        model=provider.model,
        language=detected,
        duration_s=reported or mp3_duration_s(audio),
        seconds=seconds,
        diarized=diarized,
        segments=segments,
        text=text,
    )
