import json
from urllib.parse import parse_qs, urlsplit

import pytest

from server.dataset import DatasetError, load_dataset, load_fixture, normalize_response


@pytest.fixture(scope='module')
def records():
    return load_fixture()


def test_fixture_shape(records):
    assert len(records) == 65
    for r in records:
        assert [t.idx for t in r.transcript] == list(range(len(r.transcript)))
    calls = [r for r in records if r.channel == 'voice call']
    assert len(calls) == 5
    assert all(r.audio_url for r in calls)


def test_timestamps_verbatim():
    raw = json.loads(open('tests/fixtures/dev.json', encoding='utf-8').read())['data']['records']
    recs = load_fixture()
    for rr, r in zip(raw, recs):
        assert [t['timestamp'] for t in rr['transcript']] == [t.timestamp for t in r.transcript]


def test_offsets(records):
    by = {r.conversation_id: r for r in records}
    assert all(t.offset_s is None for t in by['p1-ru-001'].transcript)
    tr = by['p4-ru-003'].transcript
    assert tr[0].offset_s == 0.0
    assert round(tr[2].offset_s, 3) == 9.227


def test_error_payload():
    with pytest.raises(DatasetError, match='boom'):
        normalize_response({'isSuccess': False, 'error': 'boom'}, 'X')


def test_missing_transcript():
    payload = {'isSuccess': True, 'data': {'records': [{'conversation_id': 'abc-1', 'channel': 'agent chat', 'language': 'RU'}]}}
    with pytest.raises(DatasetError, match='abc-1'):
        normalize_response(payload, 'X')


def test_unknown_speaker():
    payload = {
        'isSuccess': True,
        'data': {
            'records': [
                {
                    'conversation_id': 'abc-2',
                    'channel': 'agent chat',
                    'language': 'RU',
                    'transcript': [{'timestamp': '00:00', 'speaker': 'alien', 'text': 'x'}],
                }
            ]
        },
    }
    with pytest.raises(DatasetError, match="alien.*abc-2"):
        normalize_response(payload, 'X')


def test_rejects_collects_bad_records_without_failing_the_group():
    good = {'conversation_id': 'ok-1', 'channel': 'agent chat', 'language': 'RU',
            'transcript': [{'timestamp': '00:00', 'speaker': 'client', 'text': 'x'}]}
    bad_speaker = {**good, 'conversation_id': 'bad-1', 'transcript': [{'timestamp': '00:00', 'speaker': 'alien', 'text': 'x'}]}
    no_transcript = {'conversation_id': 'bad-2', 'channel': 'agent chat', 'language': 'RU'}
    payload = {'isSuccess': True, 'data': {'records': [good, bad_speaker, 'junk', no_transcript]}}
    rejects: dict[str, str] = {}
    records = normalize_response(payload, 'X', rejects)
    assert [r.conversation_id for r in records] == ['ok-1']
    assert list(rejects) == ['bad-1', '<record 2>', 'bad-2']
    assert 'alien' in rejects['bad-1']
    # Without a collector the strict contract holds.
    with pytest.raises(DatasetError, match='alien'):
        normalize_response(payload, 'X')


class _Resp:
    def __init__(self, status_code, payload=None, text=''):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError('not json')
        return self._payload


class _Session:
    def __init__(self, resp):
        self.resp = resp
        self.urls = []

    async def get(self, url, timeout=None):
        self.urls.append(url)
        return self.resp


async def test_load_dataset_cache_and_refresh(monkeypatch, tmp_path):
    monkeypatch.setenv('DATASET_URL', 'https://example.test/x?sig=SECRET&group_id=DEV')
    payload = json.loads(open('tests/fixtures/dev.json', encoding='utf-8').read())
    sess = _Session(_Resp(200, payload))
    recs = await load_dataset('CTRL', session=sess, cache_dir=tmp_path)
    assert len(recs) == 65
    q = parse_qs(urlsplit(sess.urls[0]).query)
    assert q['group_id'] == ['CTRL'] and q['sig'] == ['SECRET']
    cache = tmp_path / 'CTRL.json'
    assert cache.exists()

    again = await load_dataset('CTRL', session=sess, cache_dir=tmp_path)
    assert len(again) == 65 and len(sess.urls) == 1

    before = cache.read_bytes()
    bad = _Session(_Resp(200, None, text='<html>nope</html>'))
    with pytest.raises(DatasetError) as ei:
        await load_dataset('CTRL', refresh=True, session=bad, cache_dir=tmp_path)
    assert 'SECRET' not in str(ei.value)
    assert cache.read_bytes() == before


async def test_failure_statuses_keep_cache(monkeypatch, tmp_path):
    monkeypatch.setenv('DATASET_URL', 'https://example.test/x?sig=SECRET')
    (tmp_path / 'G.json').write_bytes(b'{"keep": 1}')
    for resp in (_Resp(500, {}), _Resp(200, {'isSuccess': False, 'error': 'boom'})):
        with pytest.raises(DatasetError) as ei:
            await load_dataset('G', refresh=True, session=_Session(resp), cache_dir=tmp_path)
        assert 'SECRET' not in str(ei.value)
        assert (tmp_path / 'G.json').read_bytes() == b'{"keep": 1}'


async def test_missing_url(monkeypatch, tmp_path):
    monkeypatch.delenv('DATASET_URL', raising=False)
    with pytest.raises(DatasetError, match='DATASET_URL'):
        await load_dataset('G', cache_dir=tmp_path)
