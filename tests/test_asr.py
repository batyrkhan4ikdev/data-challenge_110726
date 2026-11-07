import json
import random

import pytest

from bench.asr import cer, edit_distance, normalize, wer
from server.asr.audio import extract_source_url, mp3_duration_s, split_mp3
from server.asr.base import AsrError, AsrResult, AsrSegment
from server.asr.providers import (
    AsrProvider,
    load_asr_providers,
    parse_diarized_text,
    parse_labeled_text,
    parse_openai_audio,
    transcribe,
)
from server.asr.to_record import LEAK_SCHEMA, split_long_segments, MASK_NAME, MASK_PD, SCHEMA, asr_to_record, mask_digits, merge_roles, segment_starts, scrub
from server.config import Profile
from server.dataset import normalize_response
from server.llm.client import Completion
from server.models import Record, Turn

PROFILE = Profile(name='t', provider='fake', model='m')


# ---------------------------------------------------------------- providers / parsing

def test_config_loads_without_env(monkeypatch):
    providers = load_asr_providers()
    for p in providers.values():  # the developer's .env must not leak in
        for var in (p.base_url_env, p.api_key_env):
            if var:
                monkeypatch.delenv(var, raising=False)
    assert {'freedomspeech', 'aigw-whisper', 'alem-whisper-turbo', 'alem-gigaam', 'kuspeech'} <= set(providers)
    assert providers['freedomspeech'].kind == 'freedomspeech'
    assert providers['freedomspeech'].extra_form['prettify'] is False
    assert providers['h200-whisperx'].extra_form['diarize'] is True
    assert providers['h200-whisperx'].hosting == 'local'
    assert providers['openrouter-audio'].kind == 'openrouter_audio'
    assert providers['openrouter-audio'].enabled is False
    for p in providers.values():
        assert p.label and p.hosting in ('local', 'external_api')
        assert not p.configured()


async def test_not_configured_error(monkeypatch):
    monkeypatch.delenv('FREEDOMSPEECH_API_KEY', raising=False)
    provider = load_asr_providers()['freedomspeech']
    with pytest.raises(AsrError, match='не настроен'):
        await transcribe(provider, b'audio')


async def test_not_configured_when_base_url_env_unset(monkeypatch):
    monkeypatch.delenv('NOPE_URL', raising=False)
    monkeypatch.setenv('NOPE_KEY', 'k')
    provider = AsrProvider(
        name='x', kind='openai_audio', base_url_env='NOPE_URL', api_key_env='NOPE_KEY', model='m', label='X', hosting='local'
    )
    assert provider.missing_env() == ['NOPE_URL']
    with pytest.raises(AsrError, match='не настроен'):
        await transcribe(provider, b'audio')


def test_freedomspeech_text_parsing():
    text = (
        '[speaker-0 | 0.5-4.25] Здравствуйте, вы позвонили.\n'
        '[speaker-1 | 4.5-6.0] Алло.\n'
        'продолжение той же реплики\n'
        '[speaker-0 | 1:02-1:05.5] Ещё одна.\n'
        'не-размеченная строка в конце продолжает реплику'
    )
    segs = parse_diarized_text(text)
    assert [(s.speaker, s.start, s.end) for s in segs] == [
        ('speaker-0', 0.5, 4.25),
        ('speaker-1', 4.5, 6.0),
        ('speaker-0', 62.0, 65.5),
    ]
    assert segs[1].text == 'Алло. продолжение той же реплики'
    assert segs[2].text.startswith('Ещё одна.')
    assert parse_diarized_text('просто текст без меток') == []
    # the live API joins the segments with a space instead of a newline
    one_line = '[speaker-0 | 0.5-4.0] Здравствуйте! Слушаю вас. [speaker-1 | 3.9-7.8] Добрый день. [speaker-0 | 7.9-13.6] Да.'
    segs = parse_diarized_text(one_line)
    assert [(s.speaker, s.start, s.end, s.text) for s in segs] == [
        ('speaker-0', 0.5, 4.0, 'Здравствуйте! Слушаю вас.'),
        ('speaker-1', 3.9, 7.8, 'Добрый день.'),
        ('speaker-0', 7.9, 13.6, 'Да.'),
    ]


def test_labeled_text_parsing():
    segs = parse_labeled_text('[Оператор | 01:23] Добрый день\n[Клиент] Здравствуйте')
    assert [(s.speaker, s.start, s.text) for s in segs] == [('Оператор', 83.0, 'Добрый день'), ('Клиент', None, 'Здравствуйте')]


def test_verbose_json_segments():
    data = {
        'text': 'a b',
        'segments': [
            {'id': 0, 'start': 0.0, 'end': 3.72, 'text': ' Привет. '},
            {'id': 1, 'start': 3.72, 'end': 5.0, 'text': ''},
            {'id': 2, 'start': 5.0, 'end': 7.5, 'text': 'Пока'},
        ],
    }
    segs, diarized = parse_openai_audio(data)
    assert [(s.start, s.end, s.text) for s in segs] == [(0.0, 3.72, 'Привет.'), (5.0, 7.5, 'Пока')]
    assert not diarized


def test_words_fallback_groups_by_pause_and_punctuation():
    words = [
        {'word': 'алло', 'start': 0.0, 'end': 0.4},
        {'word': 'здравствуйте.', 'start': 0.5, 'end': 1.0},
        {'word': 'да', 'start': 1.1, 'end': 1.3},
        {'word': 'слушаю', 'start': 1.4, 'end': 1.8},
        {'word': 'вас', 'start': 3.5, 'end': 3.8},
    ]
    segs, _ = parse_openai_audio({'text': '', 'segments': [], 'words': words})
    assert [(s.start, s.end, s.text) for s in segs] == [
        (0.0, 1.0, 'алло здравствуйте.'),
        (1.1, 1.8, 'да слушаю'),
        (3.5, 3.8, 'вас'),
    ]


def test_text_only_fallback():
    segs, diarized = parse_openai_audio({'text': 'Первое. Второе предложение! Третье?', 'segments': None, 'words': None})
    assert [s.text for s in segs] == ['Первое.', 'Второе предложение!', 'Третье?']
    assert all(s.start is None and s.end is None for s in segs)
    assert not diarized
    long, _ = parse_openai_audio({'text': ' '.join(['слово'] * 60)})
    assert [len(s.text.split()) for s in long] == [25, 25, 10]


def test_extract_source_url_unescapes():
    page = '<audio controls><source src="https://h.example/a.mp3?x=1&amp;sig=2" type="audio/mpeg"></audio>'
    assert extract_source_url(page) == 'https://h.example/a.mp3?x=1&sig=2'
    assert extract_source_url('<html></html>') is None


def test_mp3_duration_from_xing_header():
    # MPEG-2 layer III, 16 kHz mono, Xing header with 100 frames of 576 samples = 3.6 s
    header = bytes([0xFF, 0xF3, 0x88, 0xC4])
    body = bytearray(4 + 9 + 12)
    body[9 : 9 + 4] = b'Xing'
    body[9 + 7] = 1
    body[9 + 8 : 9 + 12] = (100).to_bytes(4, 'big')
    assert mp3_duration_s(header + bytes(body)) == pytest.approx(3.6)
    assert mp3_duration_s(b'not an mp3') is None


# ---------------------------------------------------------------- masking / merge

def test_digit_safety_net():
    assert mask_digits('ИИН 990101123456 назвал') == f'ИИН {MASK_PD} назвал'
    assert mask_digits('телефон +7 777 123 45 67 ок') == f'телефон {MASK_PD} ок'
    assert mask_digits('телефон 8 (777) 123-45-67') == f'телефон {MASK_PD}'
    assert mask_digits('код 1234') == f'код {MASK_PD}'
    assert mask_digits('сумма 25 $ и 2 %, пункт 3') == 'сумма 25 $ и 2 %, пункт 3'
    assert mask_digits('в 12 30') == 'в 12 30'


def test_merge_roles():
    items = [
        ('bot', 0.0, 'a'),
        ('bot', 1.0, 'b'),
        ('client', 2.0, 'c'),
        ('operator', 3.0, 'd'),
        ('operator', 4.0, 'e'),
        ('client', 5.0, 'f'),
    ]
    assert merge_roles(items) == [('bot', 0.0, 'a b'), ('client', 2.0, 'c'), ('operator', 3.0, 'd e'), ('client', 5.0, 'f')]


def test_segment_starts_interpolates_missing_times():
    segs = [AsrSegment(start=None, end=None, speaker=None, text='x' * n) for n in (10, 30, 60)]
    assert segment_starts(segs, 100.0) == pytest.approx([0.0, 10.0, 40.0])
    mixed = [AsrSegment(start=5.0, end=6.0, speaker=None, text='a'), AsrSegment(start=None, end=None, speaker=None, text='b')]
    assert segment_starts(mixed, 10.0)[1] >= 5.0


# ---------------------------------------------------------------- asr_to_record

class ScriptedLLM:
    """Answers from a function of the numbered fragments in the prompt; records every request."""

    def __init__(self, answer, leaks=lambda lines: []):
        self.answer = answer
        self.leaks = leaks  # the second (leak finder) pass: lines of the masked transcript -> findings
        self.leak_requests: list[str] = []
        self.requests: list[str] = []

    async def complete(self, messages, schema, temperature, n):
        user = messages[-1]['content']
        if schema == LEAK_SCHEMA:
            self.leak_requests.append(user)
            return [Completion(text=json.dumps({'findings': self.leaks(user)}), finish_reason='stop', prompt_tokens=0, completion_tokens=0, seconds=0.0)]
        assert schema == SCHEMA and n == 1
        self.requests.append(user)
        fragments = []
        for line in user.splitlines():
            if line.startswith('['):
                idx, _, rest = line.partition('] ')
                rest = rest.partition(' ')[2]  # drop the mm:ss
                if rest.startswith('('):
                    rest = rest.partition(') ')[2]  # drop the speaker label
                fragments.append((int(idx[1:]), rest))
        return [
            Completion(
                text=json.dumps({'segments': self.answer(fragments)}, ensure_ascii=False),
                finish_reason='stop',
                prompt_tokens=0,
                completion_tokens=0,
                seconds=0.0,
            )
        ]


def _turn(idx, stamp, offset, speaker, text):
    return Turn(idx=idx, timestamp=stamp, offset_s=offset, speaker=speaker, text=text)


def base_record() -> Record:
    # wall timeline: recording starts at 0.1 s, is paused from 40 s to 70 s (the audio has no such 30 s)
    return Record(
        conversation_id='c-1',
        channel='voice call',
        language='RU',
        audio_url='https://example.test/player',
        transcript=[
            _turn(0, '2026-11-03T10:00:00.000000+00:00', 0.0, 'system', 'Язык диалога изменён.'),
            _turn(1, '2026-11-03T10:00:00.100000+00:00', 0.1, 'system', 'Запись и транскрибирование запущены.'),
            _turn(2, '2026-11-03T10:00:40.000000+00:00', 40.0, 'system', 'Запись и транскрибирование приостановлены.'),
            _turn(3, '2026-11-03T10:00:55.000000+00:00', 55.0, 'system', 'Агент присоединился к разговору с клиентом.'),
            _turn(4, '2026-11-03T10:01:10.000000+00:00', 70.0, 'system', 'Запись и транскрибирование возобновлены.'),
            _turn(5, '2026-11-03T10:02:00.000000+00:00', 120.0, 'system', 'Клиент завершил разговор.'),
        ],
    )


def asr_result(duration=100.0) -> AsrResult:
    rows = [
        (0.0, 'speaker-0', 'Вы позвонили в компанию.'),
        (10.0, 'speaker-0', 'Нажмите один.'),
        (45.0, 'speaker-1', 'Здравствуйте, меня зовут Иван.'),
        (50.0, 'speaker-1', 'Чем могу помочь?'),
        (60.0, 'speaker-2', 'Мой ИИН 990101123456.'),
    ]
    segs = [AsrSegment(start=s, end=s + 5, speaker=sp, text=t) for s, sp, t in rows]
    return AsrResult(
        provider='p', model='m', language='ru', duration_s=duration, seconds=1.0, diarized=True,
        segments=segs, text=' '.join(s.text for s in segs),
    )


def by_content(fragments):
    out = []
    for i, text in fragments:
        role = 'bot' if 'компанию' in text or 'Нажмите' in text else 'operator' if i in (2, 3) else 'client'
        masked = text.replace('Иван', '[Имя скрыто]')
        out.append({'i': i, 'role': role, 'masked_text': masked})
    return out


async def test_asr_to_record_end_to_end():
    llm = ScriptedLLM(by_content)
    record = await asr_to_record(asr_result(), base_record(), PROFILE, llm)

    assert record.conversation_id == 'c-1' and record.channel == 'voice call' and record.language == 'RU'
    assert record.audio_url == 'https://example.test/player'
    assert [t.idx for t in record.transcript] == list(range(len(record.transcript)))

    speakers = [t.speaker for t in record.transcript]
    # system events are copied from the base and placed by audio time; consecutive same-role segments are merged
    assert speakers == ['system', 'system', 'bot', 'system', 'system', 'system', 'operator', 'client', 'system']
    texts = [t.text for t in record.transcript]
    assert texts[2] == 'Вы позвонили в компанию. Нажмите один.'
    assert texts[6] == 'Здравствуйте, меня зовут [Имя скрыто]. Чем могу помочь?'
    assert 'Иван' not in ' '.join(texts)
    assert texts[7] == f'Мой ИИН {MASK_PD}.'  # digit safety net on top of the model's output
    assert texts[0] == 'Язык диалога изменён.' and texts[-1] == 'Клиент завершил разговор.'

    # pause correction: audio 45 s is after the pause start (audio 39.9 s) -> wall 45 + 30 + 0.1 shift
    operator = record.transcript[6]
    assert operator.offset_s == pytest.approx(45.0 + 30.0 + 0.1, abs=0.2)
    assert operator.timestamp.startswith('2026-11-03T10:01:15')
    bot = record.transcript[2]
    assert bot.offset_s == pytest.approx(0.1)
    # the pause, hold and resume events sit between the bot and the operator, in base order
    assert [t.text for t in record.transcript[3:6]] == [
        'Запись и транскрибирование приостановлены.',
        'Агент присоединился к разговору с клиентом.',
        'Запись и транскрибирование возобновлены.',
    ]
    # copied events keep their own timestamps
    assert record.transcript[3].timestamp == '2026-11-03T10:00:40.000000+00:00'
    assert record.transcript[3].offset_s == 40.0


async def test_asr_to_record_output_is_organizer_payload():
    record = await asr_to_record(asr_result(), base_record(), PROFILE, ScriptedLLM(by_content))
    payload = {
        'isSuccess': True,
        'data': {
            'records': [
                {
                    'conversation_id': record.conversation_id,
                    'channel': record.channel,
                    'language': record.language,
                    'transcript': [{'timestamp': t.timestamp, 'speaker': t.speaker, 'text': t.text} for t in record.transcript],
                    'audio_url': record.audio_url,
                }
            ]
        },
    }
    [parsed] = normalize_response(payload, 'DEV')
    assert [t.speaker for t in parsed.transcript] == [t.speaker for t in record.transcript]
    assert parsed.transcript[6].offset_s == pytest.approx(record.transcript[6].offset_s, abs=1e-3)


async def test_chunking_passes_previous_roles_and_retries_missing():
    segs = [AsrSegment(start=float(i), end=i + 0.5, speaker=None, text=f'реплика {i}') for i in range(130)]
    result = AsrResult(
        provider='p', model='m', language='ru', duration_s=140.0, seconds=0.1, diarized=False, segments=segs, text='x'
    )
    base = Record(conversation_id='c-2', channel='voice call', language='RU', audio_url=None, transcript=[])
    calls = {'n': 0}

    def answer(fragments):
        calls['n'] += 1
        out = [{'i': i, 'role': 'operator' if (i // 10) % 2 else 'client', 'masked_text': t} for i, t in fragments]
        return out[:-1] if calls['n'] == 1 else out  # first answer drops a fragment: it must be asked again

    llm = ScriptedLLM(answer)
    record = await asr_to_record(result, base, PROFILE, llm)
    first_prompts = [r for r in llm.requests if '[0] ' in r]
    assert len(first_prompts) == 1 and 'Роли последних реплик' not in first_prompts[0]
    later = [r for r in llm.requests if '[60] ' in r]
    assert later and 'Роли последних реплик предыдущей части: ' in later[0]
    assert len(record.transcript) == 13  # 130 fragments, ten per same-role run
    assert ' '.join(t.text for t in record.transcript) == ' '.join(s.text for s in segs)


async def test_missing_fragment_is_never_passed_through_unmasked():
    llm = ScriptedLLM(lambda fragments: [{'i': i, 'role': 'client', 'masked_text': t} for i, t in fragments if i != 1])
    result = asr_result()
    with pytest.raises(AsrError, match='замаскировать'):
        await asr_to_record(result, base_record(), PROFILE, llm)


async def test_leak_pass_masks_what_the_first_pass_missed():
    def leaks(user):
        # flags a surname the first pass left in, and nothing once it is gone
        return [{'quote': 'петров', 'kind': 'name'}] if 'Петров' in user else []

    def answer(fragments):
        return [{'i': i, 'role': 'client', 'masked_text': t.replace('Иван', 'Иван Петров')} for i, t in fragments]

    llm = ScriptedLLM(answer, leaks)
    record = await asr_to_record(asr_result(), base_record(), PROFILE, llm)
    text = ' '.join(t.text for t in record.transcript)
    assert 'Петров' not in text and f'Иван {MASK_NAME}' in text
    assert len(llm.leak_requests) == 2  # one pass that finds it, one that confirms it is gone
    # a finding that is not in the text is ignored, system events are not sent
    llm2 = ScriptedLLM(by_content, lambda user: [{'quote': 'призрак', 'kind': 'name'}])
    record2 = await asr_to_record(asr_result(), base_record(), PROFILE, llm2)
    assert '[Имя скрыто]' in ' '.join(t.text for t in record2.transcript)
    assert 'Язык диалога' not in llm2.leak_requests[0]


async def test_scrub_failure_is_an_error(monkeypatch):
    async def no_sleep(_):
        return None

    monkeypatch.setattr('server.asr.to_record.asyncio.sleep', no_sleep)
    class Broken:
        async def complete(self, *a, **k):
            raise RuntimeError('down')

    turns = [Turn(idx=0, timestamp='00:00', offset_s=0.0, speaker='client', text='x')]
    with pytest.raises(AsrError, match='маскирования'):
        await scrub(Broken(), turns)


async def test_empty_result_is_an_error():
    empty = AsrResult(provider='p', model='m', language=None, duration_s=None, seconds=0, diarized=False, segments=[], text='')
    with pytest.raises(AsrError):
        await asr_to_record(empty, base_record(), PROFILE)


# ---------------------------------------------------------------- benchmark metrics

def test_normalize_drops_masks_and_punctuation():
    assert normalize('Здравствуйте, [Имя скрыто]!  Ёлка — тут.') == 'здравствуйте елка тут'


def test_edit_distance_matches_reference_dp():
    def dp(a, b):
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, 1):
            cur = [i]
            for j, cb in enumerate(b, 1):
                cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
            prev = cur
        return prev[-1]

    rng = random.Random(1)
    for _ in range(300):
        a = ''.join(rng.choice('abc') for _ in range(rng.randint(0, 30)))
        b = ''.join(rng.choice('abc') for _ in range(rng.randint(0, 30)))
        assert edit_distance(a, b) == dp(a, b), (a, b)
    assert edit_distance(['a', 'b'], ['a', 'c', 'b']) == 1


def test_cer_wer():
    assert cer('привет мир', 'привет мир') == 0
    assert wer('один два три', 'один три') == pytest.approx(1 / 3)
    assert cer('', 'x') is None
    assert wer('Привет, [Имя скрыто]!', 'привет') == 0


def test_split_mp3_cuts_equal_pieces_at_frame_boundaries():
    # MPEG-2 layer III, 16 kHz, 32 kbit/s: 576 samples per frame = 0.036 s, 72 * 32000 / 16000 = 144 bytes
    frame = bytes([0xFF, 0xF3, 0x48, 0xC4]) + bytes(140)
    audio = frame * 1000  # 36 s
    pieces = split_mp3(audio, 20.0)
    assert [round(o, 3) for o, _ in pieces] == [0.0, 18.0]
    # every piece starts with a Xing frame, so a decoder does not have to guess its duration from the first frame's bitrate
    assert sum(len(b) - 144 for _, b in pieces) == len(audio)
    assert all(len(b) % 144 == 0 for _, b in pieces)
    assert [mp3_duration_s(b) for _, b in pieces] == pytest.approx([18.0, 18.0], abs=0.05)
    assert split_mp3(audio, 60.0) == [(0.0, audio)]
    assert split_mp3(b'garbage', 1.0) == [(0.0, b'garbage')]


def test_words_with_speakers_win_over_a_whole_file_segment():
    words = [
        {'word': 'Здравствуйте.', 'start': 0.5, 'end': 1.5, 'speaker': 0},
        {'word': 'Слушаю', 'start': 1.6, 'end': 2.0, 'speaker': 0},
        {'word': 'вас', 'start': 2.0, 'end': 2.3, 'speaker': 0},
        {'word': 'Алло', 'start': 2.4, 'end': 2.8, 'speaker': 1},
        {'word': 'добрый', 'start': 2.8, 'end': 3.2, 'speaker': 1},
    ]
    data = {'text': 'x', 'segments': [{'id': 0, 'start': 0, 'end': 28.4, 'text': 'всё вместе'}], 'words': words}
    segs, diarized = parse_openai_audio(data)
    assert diarized
    assert [(s.speaker, s.start, s.end, s.text) for s in segs] == [
        ('speaker-0', 0.5, 1.5, 'Здравствуйте.'),
        ('speaker-0', 1.6, 2.3, 'Слушаю вас'),
        ('speaker-1', 2.4, 3.2, 'Алло добрый'),
    ]


def test_coarse_whisper_segments_are_split_by_words_but_fine_ones_are_kept():
    words = [{'word': 'а', 'start': 0.0, 'end': 0.5}, {'word': 'б', 'start': 10.0, 'end': 10.5}]
    coarse = {'segments': [{'start': 0.0, 'end': 30.0, 'text': 'а б'}], 'words': words}
    assert [s.text for s in parse_openai_audio(coarse)[0]] == ['а', 'б']
    fine = {'segments': [{'start': 0.0, 'end': 5.0, 'text': 'а б'}], 'words': words}
    assert [s.text for s in parse_openai_audio(fine)[0]] == ['а б']


def test_realistic_multiline_diarized_text():
    lines = [
        '[speaker-0 | 0.5-4.0] Добрый день! Вас приветствует Фридом Финанс.',
        '[speaker-1 | 3.9-7.8] Здравствуйте, у меня вопрос по счёту.',
        '[speaker-0 | 7.9-13.6] Слушаю вас внимательно. Назовите, пожалуйста, ИИН.',
        '[speaker-1 | 17.8-54.6] ' + 'Это длинный ответ клиента. ' * 5,
    ]
    for joiner in ('\n', ' '):
        segs = parse_diarized_text(joiner.join(lines))
        assert [s.speaker for s in segs] == ['speaker-0', 'speaker-1', 'speaker-0', 'speaker-1']
        assert segs[2].start == 7.9 and segs[2].end == 13.6
        assert segs[3].text.startswith('Это длинный ответ')


def test_long_segments_are_split_into_sentences_with_interpolated_times():
    text = ' '.join(f'Предложение номер {i} достаточно длинное.' for i in range(60))  # ~2400 chars
    [piece] = [AsrSegment(start=10.0, end=110.0, speaker='speaker-0', text=text)]
    out = split_long_segments([piece, AsrSegment(start=111.0, end=112.0, speaker=None, text='коротко')])
    assert len(out) > 5 and out[-1].text == 'коротко'
    long = out[:-1]
    assert all(len(s.text) <= 600 for s in long) and ' '.join(s.text for s in long) == text
    assert long[0].start == 10.0 and long[-1].end == pytest.approx(110.0)
    assert [s.start for s in long] == sorted(s.start for s in long)
    assert {s.speaker for s in long} == {'speaker-0'}


async def test_truncated_model_output_fails_loudly():
    def answer(fragments):
        return [{'i': i, 'role': 'client', 'masked_text': t[:3]} for i, t in fragments]

    with pytest.raises(AsrError, match='сократила'):
        await asr_to_record(asr_result(), base_record(), PROFILE, ScriptedLLM(answer))


async def test_known_speaker_roles_are_passed_to_later_chunks():
    segs = [AsrSegment(start=float(i), end=i + 0.5, speaker=f'speaker-{i % 2}', text=f'реплика {i}') for i in range(90)]
    result = AsrResult(provider='p', model='m', language='ru', duration_s=100.0, seconds=0.1, diarized=True, segments=segs, text='x')
    base = Record(conversation_id='c-3', channel='voice call', language='RU', audio_url=None, transcript=[])
    llm = ScriptedLLM(lambda fr: [{'i': i, 'role': 'operator' if i % 2 else 'client', 'masked_text': t} for i, t in fr])
    record = await asr_to_record(result, base, PROFILE, llm)
    later = [r for r in llm.requests if '[60] ' in r]
    assert 'speaker-0 = client' in later[0] and 'speaker-1 = operator' in later[0]
    assert 'Метки говорящих' not in llm.requests[0]
    assert len(record.transcript) == 90


async def test_pieces_shift_times_and_prefix_speakers(monkeypatch):
    import server.asr.providers as prov

    frame = bytes([0xFF, 0xF3, 0x48, 0xC4]) + bytes(140)
    audio = frame * 1000  # 36 s -> two pieces of 18 s
    calls = []

    async def fake_kind(provider, piece, filename):
        calls.append(len(piece))
        seg = AsrSegment(start=1.0, end=2.0, speaker='SPEAKER_00', text=f'часть {len(calls)}')
        return {'text': seg.text, 'duration': 18.0}, [seg], True

    monkeypatch.setitem(prov._KINDS, 'openai_audio', fake_kind)
    monkeypatch.setenv('X_URL', 'http://x')
    provider = AsrProvider(
        name='x', kind='openai_audio', base_url_env='X_URL', model='m', label='X', hosting='local', max_audio_s=20
    )
    result = await transcribe(provider, audio)
    assert [(s.start, s.end, s.speaker) for s in result.segments] == [(1.0, 2.0, 'p0:SPEAKER_00'), (19.0, 20.0, 'p1:SPEAKER_00')]
    assert result.duration_s == 36.0 and result.diarized and result.text == 'часть 1\nчасть 2'


def test_benchmark_payload_never_carries_the_signed_url():
    from bench.asr import api_payload

    url = 'https://example.test/invoke/Conversation/x?api-version=1&sv=1.0&sig=SECRETSIG&rsct=audio'
    rec = Record(conversation_id='p4-ru-001', channel='voice call', language='RU', audio_url=url,
                 transcript=[Turn(idx=0, timestamp='00:00', offset_s=0.0, speaker='client', text='Алло')])
    payload = api_payload([rec], 'x')
    out = payload['data']['records'][0]['audio_url']
    assert 'SECRETSIG' not in out and 'sig=REDACTED' in out and out.endswith('&rsct=audio')
    normalize_response(payload, 'DEV')  # still loadable by the app
