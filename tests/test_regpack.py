import io
import json
import zipfile

from litestar.testing import AsyncTestClient

from server.regpack import verify_regpack
from tests.test_api import RECORDS, appeal, client, evaluate_one, fake_env  # noqa: F401


def _zip(data: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return {n: z.read(n) for n in z.namelist()}


async def test_regpack_selfcheck_after_decision(client: AsyncTestClient) -> None:
    view = await evaluate_one(client, RECORDS[0].conversation_id)
    ev = view['evaluation']
    item = next(i for i in ev['items'] if i['verdict'] != 'na')
    ap = (await appeal(client, ev['id'], item['criterion_id'])).json()
    allowed = 'no' if item['verdict'] == 'yes' else 'yes'
    r = await client.post(
        f'/api/appeals/{ap["id"]}/decision', json={'action': 'change', 'new_verdict': allowed, 'reason': 'проверка'}
    )
    if r.status_code != 200:  # scale criterion: pick any other allowed verdict
        r = await client.post(f'/api/appeals/{ap["id"]}/decision', json={'action': 'confirm', 'reason': 'проверка'})
    assert r.status_code == 200, r.text

    resp = await client.get(f'/api/conversations/{ev["conversation_id"]}/regpack', params={'group_id': 'DEV'})
    assert resp.status_code == 200 and resp.headers['content-type'] == 'application/zip'
    files = _zip(resp.content)
    assert {'README.md', 'manifest.json', 'record.json', 'evaluation.json', 'checklist.json', 'appeals.json',
            'final.json', 'calls.json'} <= set(files)
    manifest = json.loads(files['manifest.json'])
    stored = (await client.get(f'/api/evaluations/{ev["id"]}')).json()['final']['score']['total']
    judge = (await client.get(f'/api/evaluations/{ev["id"]}')).json()['evaluation']['score']['total']
    assert manifest['selfcheck'] == {
        'recomputed_total': stored, 'stored_total': stored, 'judge_total': judge, 'judge_total_recomputed': judge, 'ok': True,
    }
    assert judge != stored  # the decision moved the final total, the judge's own total is checked separately
    assert json.loads(files['appeals.json'])[0]['decision']['reason'] == 'проверка'
    assert json.loads(files['record.json'])['audio_url'] is None
    assert verify_regpack(resp.content)['ok']


async def test_verify_detects_tampering(client: AsyncTestClient) -> None:
    view = await evaluate_one(client, RECORDS[0].conversation_id)
    cid = view['evaluation']['conversation_id']
    data = (await client.get(f'/api/conversations/{cid}/regpack', params={'group_id': 'DEV'})).content
    files = _zip(data)
    ev = json.loads(files['evaluation.json'])
    ev['items'][0]['verdict'] = 'no' if ev['items'][0]['verdict'] != 'no' else 'yes'
    files['evaluation.json'] = json.dumps(ev).encode()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        for n, b in files.items():
            z.writestr(n, b)
    res = verify_regpack(buf.getvalue())
    assert not res['ok'] and any('evaluation.json' in p for p in res['problems'])


async def test_regpack_without_evaluation_is_error(client: AsyncTestClient) -> None:
    r = await client.get(f'/api/conversations/{RECORDS[0].conversation_id}/regpack', params={'group_id': 'DEV'})
    assert r.status_code == 400


async def test_regpack_includes_call_audio(client: AsyncTestClient, tmp_path, monkeypatch) -> None:
    from server import regpack
    from tests.test_api import CALL

    (tmp_path / f'{CALL}.mp3').write_bytes(b'ID3' + b'\x00' * 2000)
    monkeypatch.setattr(regpack, 'AUDIO_DIR', tmp_path)
    view = await evaluate_one(client, CALL)
    cid = view['evaluation']['conversation_id']
    info = (await client.get(f'/api/conversations/{cid}/audio-info', params={'group_id': 'DEV'})).json()
    assert info == {'size_bytes': 2003}
    resp = await client.get(f'/api/conversations/{cid}/regpack', params={'group_id': 'DEV'})
    assert resp.headers['x-regpack-audio'] == 'included' and resp.headers['x-regpack-selfcheck'] == 'ok'
    files = _zip(resp.content)
    assert files[f'audio/{CALL}.mp3'] == b'ID3' + b'\x00' * 2000
    audio = json.loads(files['manifest.json'])['audio']
    assert audio['status'] == 'included' and audio['file'] == f'audio/{CALL}.mp3' and audio['bytes'] == 2003
    assert verify_regpack(resp.content)['ok']


async def test_regpack_says_when_audio_is_missing(client: AsyncTestClient, tmp_path, monkeypatch) -> None:
    from server import regpack
    from tests.test_api import CALL

    async def unreachable(record):
        raise RuntimeError('ссылка истекла')

    monkeypatch.setattr(regpack, 'AUDIO_DIR', tmp_path)
    monkeypatch.setattr(regpack, '_remote_audio', unreachable)
    view = await evaluate_one(client, CALL)
    resp = await client.get(f'/api/conversations/{CALL}/regpack', params={'group_id': 'DEV'})
    assert resp.headers['x-regpack-audio'] == 'missing' and resp.headers['x-regpack-selfcheck'] == 'ok'
    assert not [n for n in _zip(resp.content) if n.startswith('audio/')]
    audio = json.loads(_zip(resp.content)['manifest.json'])['audio']
    assert audio == {'status': 'missing', 'reason': 'ссылка истекла'}
    assert verify_regpack(resp.content)['ok']
    assert view['evaluation']['conversation_id'] == CALL

    monkeypatch.setattr(regpack, 'MAX_AUDIO_BYTES', 10)
    (tmp_path / f'{CALL}.mp3').write_bytes(b'x' * 11)
    resp = await client.get(f'/api/conversations/{CALL}/regpack', params={'group_id': 'DEV'})
    assert resp.headers['x-regpack-audio'] == 'too_large'

