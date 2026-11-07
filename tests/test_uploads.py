"""Uploaded calls and pasted chats: the `UPLOADS` group goes through the same cycle as a dataset group."""

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
from litestar.testing import AsyncTestClient

from server.app import create_app
from server.asr import providers, to_record
from server.asr.base import AsrError
from server.transcripts import parse_custom_text
from tests.test_api import DEFAULTS, fixture_loader

WHISPERX = SimpleNamespace(name='h200-whisperx', label='WhisperX', hosting='local')
KAZAKH = 'Сәлеметсіз бе, қалай көмектесе аламын'
CHAT = 'оператор: Здравствуйте, чем помочь?\nклиент: Хочу узнать баланс\nоператор: Секунду, проверю'


@pytest.fixture(autouse=True)
def fake_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('LLM_PROFILE', 'fake')
    monkeypatch.delenv('EVAL_MODE', raising=False)
    monkeypatch.delenv('EVAL_K', raising=False)
    monkeypatch.delenv('FALLBACK_PROFILE', raising=False)
    monkeypatch.setattr(providers, 'load_asr_providers', lambda *a, **k: {'h200-whisperx': WHISPERX})


@pytest.fixture
async def client(tmp_path: Path):
    app = create_app(tmp_path / 'store', fixture_loader, DEFAULTS, calls_dir=tmp_path / 'calls', quality_path=tmp_path / 'q.json')
    async with AsyncTestClient(app) as c:
        yield c


def stub_asr(monkeypatch: pytest.MonkeyPatch, detected: str | None, text: str, seen: list) -> None:
    async def transcribe(provider, data, filename='call.mp3', language=None):
        seen.append((data, filename, language))
        if text == 'fail':
            raise AsrError('hub timeout')
        return SimpleNamespace(language=detected, text=text, segments=[])

    async def to_rec(result, base, profile):
        rec = parse_custom_text(f'оператор: {result.text}\nклиент: да', base)
        return rec

    monkeypatch.setattr(providers, 'transcribe', transcribe)
    monkeypatch.setattr(to_record, 'asr_to_record', to_rec)


async def upload(client: AsyncTestClient, language: str = 'auto', name: str = 'call.mp3', body: bytes = b'ID3mp3'):
    return await client.post('/api/uploads/call', files={'file': (name, body, 'audio/mpeg')}, data={'language': language})


async def test_uploaded_kazakh_call_is_detected_evaluated_and_playable(client, monkeypatch) -> None:
    seen: list = []
    stub_asr(monkeypatch, 'kk', KAZAKH, seen)
    r = await upload(client)
    assert r.status_code == 200, r.text
    rec = r.json()
    # `auto` sends no hint, and the provider's detection decides the label (record 1234 was mislabelled RU).
    assert rec['conversation_id'] == 'up-call-001' and rec['language'] == 'KZ' and rec['channel'] == 'voice call'
    assert seen == [(b'ID3mp3', 'up-call-001.mp3', None)]

    listed = (await client.get('/api/datasets/UPLOADS/conversations')).json()
    assert [c['conversation_id'] for c in listed] == ['up-call-001']
    audio = await client.get(rec['audio_url'])
    assert audio.status_code == 200 and audio.content == b'ID3mp3' and audio.headers['content-type'] == 'audio/mpeg'

    job = (await client.post('/api/evaluations/batch', json={'group_id': 'UPLOADS', 'conversation_ids': ['up-call-001']})).json()
    for _ in range(100):
        job = (await client.get(f'/api/jobs/{job["id"]}')).json()
        if job['state'] == 'finished':
            break
        await asyncio.sleep(0.05)
    assert job['failed'] == {} and len(job['evaluation_ids']) == 1, job
    assert (await client.get('/api/datasets/UPLOADS/conversations')).json()[0]['latest'] is not None


async def test_chosen_language_is_the_hint_and_retranscribe_reads_the_stored_file(client, monkeypatch) -> None:
    seen: list = []
    stub_asr(monkeypatch, 'ru', 'Здравствуйте', seen)
    monkeypatch.setattr('server.uploads.shutil.which', lambda name: None)  # keep the WAV as is
    rec = (await upload(client, language='KZ', name='a.wav', body=b'RIFFwav')).json()
    assert rec['language'] == 'KZ' and seen[-1][2] == 'kk'

    r = await client.post(f'/api/conversations/{rec["conversation_id"]}/transcribe', json={'group_id': 'UPLOADS', 'provider': 'h200-whisperx'})
    assert r.status_code == 200, r.text
    assert seen[-1][:2] == (b'RIFFwav', f'{rec["conversation_id"]}.wav')


async def test_failed_asr_leaves_nothing_behind_and_ids_do_not_collide(client, monkeypatch) -> None:
    seen: list = []
    stub_asr(monkeypatch, None, 'fail', seen)
    r = await upload(client)
    assert r.status_code == 502 and 'hub timeout' in r.json()['error']
    assert (await client.get('/api/datasets/UPLOADS/conversations')).json() == []

    chat = (await client.post('/api/uploads/chat', json={'text': CHAT, 'language': 'RU'})).json()
    # the failed call burnt id 001: ids only grow, so nothing stale can attach to a later dialog
    assert chat['conversation_id'] == 'up-chat-002' and chat['channel'] == 'agent chat' and len(chat['transcript']) == 3
    assert (await upload(client, name='notes.txt')).status_code == 400

    assert (await client.delete('/api/uploads/up-chat-002')).status_code == 204
    assert (await client.get('/api/datasets/UPLOADS/conversations')).json() == []
    assert (await client.delete('/api/uploads/up-chat-002')).status_code == 404
    assert (await client.get('/api/uploads/..%2F..%2Fsecret/audio')).status_code == 404


async def test_deleted_upload_id_is_not_reused(client, monkeypatch) -> None:
    """The deleted dialog's evaluations stay in the store; a reused id would show them on the next upload."""
    a = (await client.post('/api/uploads/chat', json={'text': CHAT, 'language': 'RU'})).json()['conversation_id']
    assert (await client.delete(f'/api/uploads/{a}')).status_code == 204
    b = (await client.post('/api/uploads/chat', json={'text': CHAT, 'language': 'RU'})).json()['conversation_id']
    assert (a, b) == ('up-chat-001', 'up-chat-002')
