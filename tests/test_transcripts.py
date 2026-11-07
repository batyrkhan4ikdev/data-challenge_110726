import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from litestar.testing import AsyncTestClient

import server.jobs
from server.app import create_app
from server.asr import audio, providers, to_record
from server.asr.base import AsrError
from server.models import Record
from server.transcripts import parse_custom_text
from tests.test_api import CALL, CHATS, DEFAULTS, RECORDS, fixture_loader

BASE = next(r for r in RECORDS if r.conversation_id == CALL)
CUSTOM_TEXT = 'оператор: Здравствуйте, чем помочь?\nклиент: Хочу узнать баланс\nпродолжение реплики клиента\nО: Секунду'
WHISPER = SimpleNamespace(name='aigw-whisper', label='Whisper (aigw)', hosting='external_api')
FREEDOM = SimpleNamespace(name='freedomspeech', label='FreedomSpeech', hosting='external_api')


@pytest.fixture(autouse=True)
def fake_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('LLM_PROFILE', 'fake')
    monkeypatch.delenv('EVAL_MODE', raising=False)
    monkeypatch.delenv('EVAL_K', raising=False)
    monkeypatch.delenv('FALLBACK_PROFILE', raising=False)
    monkeypatch.setattr(providers, 'load_asr_providers', lambda *a, **k: {'freedomspeech': FREEDOM, 'aigw-whisper': WHISPER})


@pytest.fixture
async def client(tmp_path: Path):
    quality = tmp_path / 'quality.json'
    quality.write_text(
        json.dumps({'freedomspeech': {'label': 'FS', 'cer_vs_api': 0.31, 'manual_score': 4.5, 'diarized': True}}),
        encoding='utf-8',
    )
    # Seed only Batyrkhan's FreedomSpeech file: the real data/calls also holds every benchmarked provider.
    calls = tmp_path / 'calls'
    calls.mkdir()
    (calls / 'freedomspeech.dev.json').write_bytes((Path('data/calls') / 'freedomspeech.dev.json').read_bytes())
    app = create_app(tmp_path / 'store', fixture_loader, DEFAULTS, calls_dir=calls, quality_path=quality)
    async with AsyncTestClient(app) as c:
        yield c


async def put_custom(client: AsyncTestClient, cid: str = CALL, text: str = CUSTOM_TEXT):
    return await client.put(f'/api/conversations/{cid}/transcripts/custom', json={'group_id': 'DEV', 'text': text})


def test_parse_custom_text_prefixes_and_continuations() -> None:
    rec = parse_custom_text(CUSTOM_TEXT + '\n\nBOT: ответ бота\nclient: Спасибо', BASE)
    assert [(t.speaker, t.text) for t in rec.transcript] == [
        ('operator', 'Здравствуйте, чем помочь?'),
        ('client', 'Хочу узнать баланс продолжение реплики клиента'),
        ('operator', 'Секунду'),
        ('bot', 'ответ бота'),
        ('client', 'Спасибо'),
    ]
    assert [t.idx for t in rec.transcript] == list(range(5))
    assert all(t.offset_s is None and t.timestamp == '' for t in rec.transcript)
    assert (rec.conversation_id, rec.channel, rec.language, rec.audio_url) == (
        BASE.conversation_id,
        BASE.channel,
        BASE.language,
        BASE.audio_url,
    )


@pytest.mark.parametrize('text', ['', '  \n \n', 'просто текст без префикса\nоператор: потом префикс'])
def test_parse_custom_text_rejects(text: str) -> None:
    with pytest.raises(ValueError):
        parse_custom_text(text, BASE)


async def test_put_custom_empty_is_400(client: AsyncTestClient) -> None:
    r = await put_custom(client, text='   ')
    assert r.status_code == 400
    assert r.json()['error']
    assert (await put_custom(client, 'nope')).status_code == 404
    chat = await put_custom(client, CHATS[0])
    assert chat.status_code == 400  # calls only


async def test_sources_listing(client: AsyncTestClient) -> None:
    rows = (await client.get(f'/api/conversations/{CALL}/transcripts')).json()
    by = {r['source']: r for r in rows}
    assert [r['source'] for r in rows] == ['api', 'freedomspeech', 'aigw-whisper', 'custom']
    assert by['api']['available'] and by['api']['kind'] == 'api'
    fs = by['freedomspeech']
    assert fs['available'] and fs['kind'] == 'asr' and fs['label'] == 'FreedomSpeech'  # seeded from data/calls
    assert fs['provider_hosting'] == 'external_api'
    assert fs['quality']['cer_vs_api'] == 0.31 and fs['quality']['manual_score'] == 4.5
    assert not by['aigw-whisper']['available'] and by['aigw-whisper']['quality'] is None
    assert not by['custom']['available']

    assert (await put_custom(client)).status_code == 200
    rows = (await client.get(f'/api/conversations/{CALL}/transcripts')).json()
    custom = next(r for r in rows if r['source'] == 'custom')
    assert custom['available'] and custom['created_at']
    # A call without a seeded FreedomSpeech transcript only has the organizer's.
    rows = (await client.get(f'/api/conversations/{CHATS[0]}/transcripts')).json()
    assert [r['source'] for r in rows if r['available']] == ['api']


async def test_record_by_source(client: AsyncTestClient) -> None:
    url = f'/api/datasets/DEV/conversations/{CALL}'
    api = (await client.get(url)).json()
    assert api == Record.model_validate(BASE).model_dump(mode='json')
    assert (await client.get(url, params={'source': 'api'})).json() == api
    fs = (await client.get(url, params={'source': 'freedomspeech'})).json()
    assert fs['conversation_id'] == CALL and fs['channel'] == 'voice call' and fs['transcript'] != api['transcript']

    assert (await client.get(url, params={'source': 'custom'})).status_code == 404
    await put_custom(client)
    custom = (await client.get(url, params={'source': 'custom'})).json()
    assert [t['text'] for t in custom['transcript']][0] == 'Здравствуйте, чем помочь?'
    assert custom['audio_url'] == api['audio_url']
    missing = await client.get(url, params={'source': 'nope'})
    assert missing.status_code == 404 and 'nope' in missing.json()['error']
    # facts follow the chosen source
    facts = await client.get(f'{url}/facts', params={'source': 'custom'})
    assert facts.status_code == 200


def captured(monkeypatch: pytest.MonkeyPatch) -> list[Record]:
    seen: list[Record] = []
    real = server.jobs.evaluate

    async def spy(record, *args, **kwargs):
        seen.append(record)
        return await real(record, *args, **kwargs)

    monkeypatch.setattr(server.jobs, 'evaluate', spy)
    return seen


async def batch(client: AsyncTestClient, ids: list[str], source: str | None) -> dict:
    r = await client.post(
        '/api/evaluations/batch',
        json={'group_id': 'DEV', 'conversation_ids': ids, 'transcript_source': source},
    )
    assert r.status_code == 200, r.text
    return await run_batch_wait(client, r.json())


async def run_batch_wait(client: AsyncTestClient, job: dict) -> dict:
    for _ in range(500):
        if job['state'] == 'finished':
            return job
        await asyncio.sleep(0.01)
        job = (await client.get(f'/api/jobs/{job["id"]}')).json()
    raise AssertionError(job)


async def test_batch_with_custom_source(client: AsyncTestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    seen = captured(monkeypatch)
    await put_custom(client)
    job = await batch(client, [CALL], 'custom')
    assert job['failed'] == {} and len(job['evaluation_ids']) == 1
    assert len(seen) == 1 and [t.text for t in seen[0].transcript][-1] == 'Секунду'
    ev = (await client.get(f'/api/evaluations/{job["evaluation_ids"][0]}')).json()['evaluation']
    assert ev['transcript_source'] == 'custom'

    # A seeded source works without any stored file; the default stays the organizer transcript.
    job = await batch(client, [CALL], 'freedomspeech')
    assert job['failed'] == {}
    assert (await client.get(f'/api/evaluations/{job["evaluation_ids"][0]}')).json()['evaluation']['transcript_source'] == 'freedomspeech'
    job = await batch(client, [CALL], None)
    assert seen[-1] == BASE
    assert (await client.get(f'/api/evaluations/{job["evaluation_ids"][0]}')).json()['evaluation']['transcript_source'] == 'api'


async def test_unknown_source_fails_per_dialog(client: AsyncTestClient) -> None:
    other = 'p4-ru-002'  # a real call that has no custom transcript
    await put_custom(client)
    job = await batch(client, [CALL, other, 'ghost'], 'custom')
    assert job['total'] == 3 and job['done'] == 3 and len(job['evaluation_ids']) == 1
    assert 'custom' in job['failed'][other] and 'не найден' in job['failed'][other]
    assert set(job['failed']) == {other, 'ghost'}

    job = await batch(client, [CALL], 'nope')
    assert job['evaluation_ids'] == [] and 'nope' in job['failed'][CALL]


async def test_asr_providers_list_marks_unconfigured(client: AsyncTestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('CQA_TEST_ASR_URL', 'https://asr.example')
    monkeypatch.delenv('CQA_TEST_ASR_MISSING', raising=False)
    real = {
        'ok': providers.AsrProvider(name='ok', kind='openai_audio', base_url_env='CQA_TEST_ASR_URL', model='m',
                                    label='Готовый', hosting='local'),
        'freedomspeech': providers.AsrProvider(name='freedomspeech', kind='freedomspeech', base_url_env='CQA_TEST_ASR_MISSING',
                                               model='fs', label='FreedomSpeech', hosting='external_api'),
        'off': providers.AsrProvider(name='off', kind='openai_audio', base_url_env='CQA_TEST_ASR_URL', model='m',
                                     label='Выключен', hosting='external_api', enabled=False),
    }
    monkeypatch.setattr(providers, 'load_asr_providers', lambda *a, **k: real)
    r = await client.get('/api/asr/providers')
    assert r.status_code == 200
    rows = {p['id']: p for p in r.json()}
    assert list(rows) == ['ok', 'freedomspeech']  # config order; a disabled provider is not offered
    assert rows['ok']['available'] is True and rows['ok']['note'] is None
    fs = rows['freedomspeech']
    assert fs['available'] is False and 'CQA_TEST_ASR_MISSING' in fs['note']
    assert fs['quality']['manual_score'] == 4.5  # benchmark row from quality.json


async def test_transcribe_unconfigured_provider_is_400(client: AsyncTestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fetch(record):
        return b'mp3'

    async def transcribe(provider, data, filename='call.mp3'):
        raise AsrError('Провайдер aigw-whisper не настроен')

    monkeypatch.setattr(audio, 'fetch_call_audio', fetch)
    monkeypatch.setattr(providers, 'transcribe', transcribe)
    r = await client.post(f'/api/conversations/{CALL}/transcribe', json={'group_id': 'DEV', 'provider': 'aigw-whisper'})
    assert r.status_code == 400
    assert 'не настроен' in r.json()['error']

    r = await client.post(f'/api/conversations/{CALL}/transcribe', json={'group_id': 'DEV', 'provider': 'ghost'})
    assert r.status_code == 400 and 'ghost' in r.json()['error']
    r = await client.post(f'/api/conversations/{CHATS[0]}/transcribe', json={'group_id': 'DEV', 'provider': 'aigw-whisper'})
    assert r.status_code == 400


async def test_transcribe_stores_the_record(client: AsyncTestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    async def fetch(record):
        calls.append('fetch')
        return b'mp3'

    async def transcribe(provider, data, filename='call.mp3'):
        calls.append(f'transcribe:{provider.name}:{filename}')
        return SimpleNamespace(segments=[])

    async def to_rec(result, base, profile):
        calls.append(f'record:{profile.name}')
        return parse_custom_text('оператор: привет\nклиент: алло', base)

    monkeypatch.setattr(audio, 'fetch_call_audio', fetch)
    monkeypatch.setattr(providers, 'transcribe', transcribe)
    monkeypatch.setattr(to_record, 'asr_to_record', to_rec)
    r = await client.post(f'/api/conversations/{CALL}/transcribe', json={'group_id': 'DEV', 'provider': 'aigw-whisper'})
    assert r.status_code == 200, r.text
    assert calls == ['fetch', f'transcribe:aigw-whisper:{CALL}.mp3', 'record:fake']
    stored = (await client.get(f'/api/datasets/DEV/conversations/{CALL}', params={'source': 'aigw-whisper'})).json()
    assert stored == r.json()
    rows = (await client.get(f'/api/conversations/{CALL}/transcripts')).json()
    assert next(x for x in rows if x['source'] == 'aigw-whisper')['available']

    async def broken(record):
        raise AsrError('сеть недоступна')

    monkeypatch.setattr(audio, 'fetch_call_audio', broken)
    r = await client.post(f'/api/conversations/{CALL}/transcribe', json={'group_id': 'DEV', 'provider': 'aigw-whisper'})
    assert r.status_code == 502 and 'сеть недоступна' in r.json()['error']
