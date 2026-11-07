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
    assert manifest['selfcheck'] == {'recomputed_total': stored, 'stored_total': stored, 'ok': True}
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
