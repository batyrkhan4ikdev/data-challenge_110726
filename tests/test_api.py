import asyncio
from pathlib import Path

import pytest
from litestar.testing import AsyncTestClient

from server.app import create_app
from server.dataset import DatasetError, load_fixture
from server.models import Record

ROOT = Path(__file__).resolve().parent.parent
DEFAULTS = ROOT / 'data' / 'checklists'
RECORDS = load_fixture(ROOT / 'tests' / 'fixtures' / 'dev.json')
CHATS = [r.conversation_id for r in RECORDS if r.channel == 'agent chat']
CALL = 'p4-ru-003'


async def fixture_loader(group_id: str, refresh: bool) -> list[Record]:
    return RECORDS


async def failing_loader(group_id: str, refresh: bool) -> list[Record]:
    raise DatasetError('HTTP 502')


@pytest.fixture(autouse=True)
def fake_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('LLM_PROFILE', 'fake')
    monkeypatch.delenv('EVAL_MODE', raising=False)
    monkeypatch.delenv('EVAL_K', raising=False)
    monkeypatch.delenv('FALLBACK_PROFILE', raising=False)  # .env may set a real chain; tests never leave the machine


@pytest.fixture
async def client(tmp_path: Path):
    async with AsyncTestClient(create_app(tmp_path, fixture_loader, DEFAULTS)) as c:
        yield c


async def test_failed_dialog_falls_back_in_order(tmp_path: Path) -> None:
    from server.checklists import ChecklistStore
    from server.config import Profile
    from server.jobs import JobRunner
    from server.models import BatchRequest
    from server.store import Store

    store = Store(tmp_path)
    checklists = ChecklistStore(tmp_path / 'checklists')
    await checklists.seed_defaults(DEFAULTS)
    # 'dead' has no base URL configured, so every call fails like an unreachable endpoint.
    profiles = {
        'dead': Profile(name='dead', provider='openai', base_url_env='CQA_TEST_UNSET_URL'),
        'dead2': Profile(name='dead2', provider='openai', base_url_env='CQA_TEST_UNSET_URL'),
        'fake': Profile(name='fake', provider='fake'),
    }
    rec = RECORDS[0]
    req = BatchRequest(group_id='DEV', conversation_ids=[rec.conversation_id], checklist_id=None, profile='dead')
    records = {rec.conversation_id: rec}

    runner = JobRunner(store, checklists, profiles, ['dead2', 'fake'])
    job = await runner.wait((await runner.start(req, records)).id)
    assert job.failed == {} and len(job.evaluation_ids) == 1
    assert (await store.get_evaluation(job.evaluation_ids[0])).profile == 'fake'

    # Every link fails: one error that names each profile tried, in order.
    alone = JobRunner(store, checklists, profiles, ['dead2'])
    job = await alone.wait((await alone.start(req, records)).id)
    reason = job.failed[rec.conversation_id]
    assert reason.index('dead:') < reason.index('dead2:') and job.evaluation_ids == []

    with pytest.raises(ValueError, match='nope'):
        JobRunner(store, checklists, profiles, ['nope'])

    # A store failure must land the dialog in `failed` and still let the job finish.
    async def broken_save(ev, raw):
        raise OSError('disk full')

    store.save_evaluation = broken_save
    job = await runner.wait((await runner.start(req, records)).id)
    assert job.state == 'finished' and job.done == 1 and job.evaluation_ids == []
    assert 'disk full' in job.failed[rec.conversation_id]


async def run_batch(client: AsyncTestClient, ids: list[str], checklist_id: str | None = None) -> dict:
    r = await client.post(
        '/api/evaluations/batch',
        json={'group_id': 'DEV', 'conversation_ids': ids, 'checklist_id': checklist_id},
    )
    assert r.status_code == 200, r.text
    job = r.json()
    for _ in range(500):
        if job['state'] == 'finished':
            return job
        await asyncio.sleep(0.01)
        job = (await client.get(f'/api/jobs/{job["id"]}')).json()
    raise AssertionError(f'job did not finish: {job}')


async def evaluate_one(client: AsyncTestClient, cid: str, checklist_id: str | None = None) -> dict:
    job = await run_batch(client, [cid], checklist_id)
    assert job['failed'] == {} and len(job['evaluation_ids']) == 1, job
    return (await client.get(f'/api/evaluations/{job["evaluation_ids"][0]}')).json()


async def appeal(client: AsyncTestClient, evaluation_id: str, criterion_id: str, comment: str = 'Не согласен'):
    return await client.post(
        '/api/appeals',
        json={'evaluation_id': evaluation_id, 'criterion_id': criterion_id, 'comment': comment},
    )


async def test_conversations_list(client: AsyncTestClient) -> None:
    rows = (await client.get('/api/datasets/DEV/conversations')).json()
    assert len(rows) == 65
    assert all(r['latest'] is None for r in rows)
    view = await evaluate_one(client, CHATS[0])
    rows = (await client.get('/api/datasets/DEV/conversations', params={'refresh': 'true'})).json()
    row = next(r for r in rows if r['conversation_id'] == CHATS[0])
    assert row['turns'] == len(next(r for r in RECORDS if r.conversation_id == CHATS[0]).transcript)
    assert row['latest']['id'] == view['evaluation']['id']
    assert row['latest']['final_total'] == view['final']['score']['total']
    assert row['turns'] == len(view['evaluation']['items']) or row['turns'] > 0


async def test_conversation_record(client: AsyncTestClient) -> None:
    r = await client.get(f'/api/datasets/DEV/conversations/{CALL}')
    assert r.status_code == 200
    assert r.json()['channel'] == 'voice call'
    assert (await client.get('/api/datasets/DEV/conversations/nope')).status_code == 404


async def test_batch_two_ids(client: AsyncTestClient) -> None:
    job = await run_batch(client, CHATS[:2])
    assert (job['total'], job['done'], job['failed']) == (2, 2, {})
    assert len(job['evaluation_ids']) == 2
    view = (await client.get(f'/api/evaluations/{job["evaluation_ids"][0]}')).json()
    ev = view['evaluation']
    assert 'total' in ev['score']
    assert (view['checklist']['id'], view['checklist']['version']) == (ev['checklist_id'], ev['checklist_version'])
    assert [c['id'] for c in view['checklist']['criteria']] == [i['criterion_id'] for i in ev['items']]
    assert view['final']['score']['total'] == ev['score']['total']


async def test_batch_unknown_id_fails_alone(client: AsyncTestClient) -> None:
    job = await run_batch(client, [CHATS[0], 'nope'])
    assert job['done'] == 2 and list(job['failed']) == ['nope'] and len(job['evaluation_ids']) == 1


async def test_batch_unknown_checklist_404(client: AsyncTestClient) -> None:
    r = await client.post(
        '/api/evaluations/batch', json={'group_id': 'DEV', 'conversation_ids': CHATS[:1], 'checklist_id': 'nope'}
    )
    assert r.status_code == 404 and r.json()['error']


async def test_batch_bad_profile_400(client: AsyncTestClient) -> None:
    r = await client.post(
        '/api/evaluations/batch', json={'group_id': 'DEV', 'conversation_ids': CHATS[:1], 'profile': 'nope'}
    )
    assert r.status_code == 400


async def test_call_uses_call_checklist(client: AsyncTestClient) -> None:
    view = await evaluate_one(client, CALL)
    assert view['evaluation']['checklist_id'] == 'call'
    assert view['checklist']['id'] == 'call'


async def test_explicit_checklist(client: AsyncTestClient) -> None:
    view = await evaluate_one(client, CALL, 'chat')
    assert view['evaluation']['checklist_id'] == 'chat'


async def test_put_bumps_version_and_keeps_old_view(client: AsyncTestClient) -> None:
    old = await evaluate_one(client, CHATS[0])
    chat = (await client.get('/api/checklists/chat')).json()
    old_title = chat['criteria'][0]['title']
    chat['criteria'][0]['title'] = 'Новое приветствие'
    r = await client.put('/api/checklists/chat', json=chat)
    assert r.status_code == 200 and r.json()['version'] == 2
    assert (await client.get('/api/checklists/chat', params={'version': 1})).json()['criteria'][0]['title'] == old_title

    new = await evaluate_one(client, CHATS[0])
    assert new['evaluation']['checklist_version'] == 2
    assert new['checklist']['criteria'][0]['title'] == 'Новое приветствие'

    again = (await client.get(f'/api/evaluations/{old["evaluation"]["id"]}')).json()
    assert again['checklist']['version'] == 1
    assert again['checklist']['criteria'][0]['title'] == old_title

    history = (await client.get(f'/api/conversations/{CHATS[0]}/evaluations')).json()
    assert [h['id'] for h in history] == [new['evaluation']['id'], old['evaluation']['id']]
    assert [h['checklist_version'] for h in history] == [2, 1]


async def test_added_criterion_is_scored_and_weighted(client: AsyncTestClient) -> None:
    """The organizers' live-demo ask (#2991): add a criterion, re-evaluate, see it scored and counted in the total."""
    chat = (await client.get('/api/checklists/chat')).json()
    gross = chat['criteria'][-1]
    chat['criteria'] = chat['criteria'][:-1] + [{
        'id': 'c09', 'section_id': chat['criteria'][6]['section_id'], 'title': 'Предупреждение об ожидании',
        'description': 'Да — предупредил клиента об ожидании.', 'answer_type': 'yes_no', 'weight': 5,
        'steps': None, 'na_allowed': False, 'na_condition': None, 'kind': 'scored',
    }, gross]
    r = await client.put('/api/checklists/chat', json=chat)
    assert r.status_code == 200 and r.json()['version'] == 2

    view = await evaluate_one(client, CHATS[0])
    ev = view['evaluation']
    assert ev['checklist_version'] == 2
    item = next(i for i in ev['items'] if i['criterion_id'] == 'c09')
    assert item['verdict'] in ('yes', 'no')
    scored = {s['criterion_id']: s for s in ev['score']['items']}
    assert scored['c09']['applicable'] is True
    weights = {c['id']: c['weight'] for c in chat['criteria'] if c['kind'] == 'scored'}
    applicable = [c for c, s in scored.items() if c in weights and s['applicable']]
    # c09's weight joins the redistribution base: 105 raw points, still a 0..100 total.
    assert ev['score']['applicable_weight'] == sum(weights[c] for c in applicable)
    assert scored['c09']['max_points'] == 5
    assert ev['score']['total'] == pytest.approx(sum(scored[c]['effective_points'] for c in applicable), abs=0.01)


async def test_put_invalid_weight(client: AsyncTestClient) -> None:
    chat = (await client.get('/api/checklists/chat')).json()
    chat['criteria'][0]['weight'] = -5
    r = await client.put('/api/checklists/chat', json=chat)
    assert r.status_code == 400
    body = r.json()
    assert body['error'] == 'Чек-лист невалиден' and len(body['details']) == 1 and 'c01' in body['details'][0]

    chat['criteria'][0]['weight'] = 'много'
    r = await client.put('/api/checklists/chat', json=chat)
    assert r.status_code == 400 and r.json()['details']
    assert (await client.get('/api/checklists/chat')).json()['version'] == 1


async def test_put_id_mismatch_and_unknown(client: AsyncTestClient) -> None:
    chat = (await client.get('/api/checklists/chat')).json()
    assert (await client.put('/api/checklists/call', json=chat)).status_code == 400
    chat['id'] = 'nope'
    assert (await client.put('/api/checklists/nope', json=chat)).status_code == 404


async def test_create_checklist(client: AsyncTestClient) -> None:
    chat = (await client.get('/api/checklists/chat')).json()
    r = await client.post('/api/checklists', json=chat)
    assert r.status_code == 400
    chat.update(id='strict', name='Строгий', version=5)
    r = await client.post('/api/checklists', json=chat)
    assert r.status_code == 200 and r.json()['version'] == 1
    ids = [c['id'] for c in (await client.get('/api/checklists')).json()]
    assert ids == ['call', 'chat', 'strict']
    assert (await client.get('/api/checklists/nope')).status_code == 404


async def test_appeal_empty_comment(client: AsyncTestClient) -> None:
    view = await evaluate_one(client, CHATS[0])
    r = await appeal(client, view['evaluation']['id'], 'c01', '   ')
    assert r.status_code == 400 and r.json()['error']


async def test_appeal_unknown_criterion_and_evaluation(client: AsyncTestClient) -> None:
    view = await evaluate_one(client, CHATS[0])
    assert (await appeal(client, view['evaluation']['id'], 'c99')).status_code == 400
    assert (await appeal(client, 'nope', 'c01')).status_code == 404


async def test_decision_change_updates_final(client: AsyncTestClient) -> None:
    view = await evaluate_one(client, CHATS[0])
    ev = view['evaluation']
    c01 = next(i for i in ev['items'] if i['criterion_id'] == 'c01')
    ap = (await appeal(client, ev['id'], 'c01')).json()
    assert ap['status'] == 'open'
    flipped = 'no' if c01['verdict'] == 'yes' else 'yes'
    r = await client.post(
        f'/api/appeals/{ap["id"]}/decision', json={'action': 'change', 'new_verdict': flipped, 'reason': 'Ошибка'}
    )
    assert r.status_code == 200, r.text
    result = r.json()
    assert result['appeal']['status'] == 'resolved'
    assert result['final']['score']['total'] != ev['score']['total']

    again = (await client.get(f'/api/evaluations/{ev["id"]}')).json()
    assert again['evaluation']['score']['total'] == ev['score']['total']
    assert again['final']['score']['total'] == result['final']['score']['total']
    final_c01 = next(i for i in again['final']['items'] if i['criterion_id'] == 'c01')
    assert (final_c01['original_verdict'], final_c01['final_verdict']) == (c01['verdict'], flipped)

    rows = (await client.get('/api/datasets/DEV/conversations')).json()
    row = next(r for r in rows if r['conversation_id'] == CHATS[0])
    assert row['latest']['final_total'] == result['final']['score']['total']

    r = await client.post(f'/api/appeals/{ap["id"]}/decision', json={'action': 'confirm', 'reason': 'Ещё раз'})
    assert r.status_code == 400


async def test_decision_invalid_verdicts(client: AsyncTestClient) -> None:
    view = await evaluate_one(client, CHATS[0])
    ap = (await appeal(client, view['evaluation']['id'], 'c01')).json()
    url = f'/api/appeals/{ap["id"]}/decision'
    r = await client.post(url, json={'action': 'change', 'new_verdict': 'na', 'reason': 'Неприменимо'})
    assert r.status_code == 400
    assert 'yes' in r.json()['error'] and 'no' in r.json()['error']
    r = await client.post(url, json={'action': 'change', 'reason': 'Без вердикта'})
    assert r.status_code == 400
    r = await client.post(url, json={'action': 'confirm', 'reason': '  '})
    assert r.status_code == 400
    assert (await client.post('/api/appeals/nope/decision', json={'action': 'confirm', 'reason': 'x'})).status_code == 404

    queue = (await client.get('/api/appeals', params={'status': 'open'})).json()
    assert [q['appeal']['id'] for q in queue] == [ap['id']]


async def test_confirm_ignores_new_verdict(client: AsyncTestClient) -> None:
    view = await evaluate_one(client, CHATS[0])
    ev = view['evaluation']
    ap = (await appeal(client, ev['id'], 'c01')).json()
    r = await client.post(
        f'/api/appeals/{ap["id"]}/decision', json={'action': 'confirm', 'new_verdict': 'no', 'reason': 'Верно'}
    )
    assert r.status_code == 200
    body = r.json()
    assert body['appeal']['decision']['new_verdict'] is None
    assert body['final']['score']['total'] == ev['score']['total']


async def test_appeal_on_na_and_queue(client: AsyncTestClient) -> None:
    job = await run_batch(client, CHATS[:10])
    found = None
    for eid in job['evaluation_ids']:
        ev = (await client.get(f'/api/evaluations/{eid}')).json()['evaluation']
        na = next((i for i in ev['items'] if i['verdict'] == 'na'), None)
        if na:
            found = (ev, na)
            break
    assert found, 'no N/A verdict among the evaluated dialogs'
    ev, na = found
    r = await appeal(client, ev['id'], na['criterion_id'])
    assert r.status_code == 200
    ap = r.json()

    queue = (await client.get('/api/appeals', params={'status': 'open'})).json()
    assert len(queue) == 1
    q = queue[0]
    assert q['appeal']['id'] == ap['id']
    assert (q['evaluation_id'], q['conversation_id']) == (ev['id'], ev['conversation_id'])
    assert q['item'] == na and q['criterion']['id'] == na['criterion_id']
    assert (await client.get('/api/appeals', params={'status': 'resolved'})).json() == []
    assert (await client.get('/api/appeals', params={'status': 'bogus'})).status_code == 400


async def test_raw_calls(client: AsyncTestClient) -> None:
    view = await evaluate_one(client, CHATS[0])
    raw = (await client.get(f'/api/evaluations/{view["evaluation"]["id"]}/raw')).json()
    assert raw and raw[0]['evaluation_id'] == view['evaluation']['id'] and raw[0]['messages']
    assert (await client.get('/api/evaluations/nope/raw')).status_code == 404


async def test_profiles(client: AsyncTestClient) -> None:
    profiles = (await client.get('/api/profiles')).json()
    assert profiles[0] == {'name': 'fake', 'model': 'fake', 'provider': 'fake'}


async def test_unknown_ids_404(client: AsyncTestClient) -> None:
    for url in ['/api/evaluations/nope', '/api/jobs/nope', '/api/checklists/chat?version=9']:
        r = await client.get(url)
        assert r.status_code == 404 and r.json()['error'], url
    assert (await client.get('/api/conversations/nope/evaluations')).json() == []


async def test_bad_body_400(client: AsyncTestClient) -> None:
    r = await client.post('/api/evaluations/batch', json={'conversation_ids': 'x'})
    assert r.status_code == 400 and r.json()['details']


async def test_dataset_failure_502(tmp_path: Path) -> None:
    async with AsyncTestClient(create_app(tmp_path, failing_loader, DEFAULTS)) as c:
        r = await c.get('/api/datasets/CTRL/conversations')
    assert r.status_code == 502
    assert 'HTTP 502' in r.json()['error']


async def test_group_analytics(tmp_path: Path):
    from datetime import UTC, datetime

    from server.models import Checklist, Evaluation, Item, Usage
    from server.scoring import compute_score
    from server.store import Store

    chat = Checklist.model_validate_json((DEFAULTS / 'chat.default.json').read_text(encoding='utf-8'))
    a = {'c01': 'yes', 'c02': 'yes', 'c03': 'yes', 'c04': '20', 'c05': 'yes', 'c06': '10', 'c07': 'yes', 'c08': 'no'}
    b = {'c01': 'yes', 'c02': 'no', 'c03': 'na', 'c04': '15', 'c05': 'yes', 'c06': '7', 'c07': 'yes', 'c08': 'no'}
    c = {**b, 'c08': 'yes'}
    store = Store(tmp_path)
    for n, (cid, verdicts) in enumerate(zip(CHATS[:3], [a, b, c])):
        await store.save_evaluation(
            Evaluation(
                id=f'e{n}', conversation_id=cid, group_id='DEV', checklist_id=chat.id,
                checklist_version=chat.version, profile='t', model='m', mode='single', k=1,
                created_at=datetime(2026, 11, 7, tzinfo=UTC),
                items=[Item(criterion_id=k, verdict=v, explanation='', evidence_idx=[]) for k, v in verdicts.items()],
                score=compute_score(chat, verdicts),
                usage=Usage(prompt_tokens=0, completion_tokens=0, calls=1, seconds=0.0),
            ),
            [],
        )
    async with AsyncTestClient(create_app(tmp_path, fixture_loader, DEFAULTS)) as client:
        r = await client.get('/api/datasets/DEV/analytics')
    assert r.status_code == 200, r.text
    d = r.json()
    assert d['dialogs'] == len(RECORDS) and d['evaluated'] == 3
    assert d['mean_total'] == 79.59  # (100 + 69.38 + 69.38) / 3
    assert d['gross_error_count'] == 1 and d['gross_error_ids'] == [CHATS[2]]
    assert sum(x['count'] for x in d['histogram']) == 3
    assert {x['label']: x['count'] for x in d['histogram']}['85–100'] == 1
    assert sum(x['count'] for x in d['by_channel']) == 3
    c02 = next(x for x in d['criteria'] if x['criterion_id'] == 'c02')
    assert (c02['yes'], c02['no'], c02['na'], c02['applicable'], c02['mean_pct']) == (1, 2, 0, 3, 33.33)
    c03 = next(x for x in d['criteria'] if x['criterion_id'] == 'c03')
    assert (c03['na'], c03['applicable']) == (2, 1)
    assert all(x['criterion_id'] != 'c08' for x in d['criteria'])


async def test_slow_refresh_does_not_block_reads(tmp_path: Path) -> None:
    """«Обновить» refetches from the organizers' API; other pages of the group must keep answering from the cache."""
    gate = asyncio.Event()

    async def slow(group_id: str, refresh: bool) -> list[Record]:
        if refresh:
            await gate.wait()
        return RECORDS

    svc = create_app(tmp_path, slow, DEFAULTS).state.services
    await svc.records('DEV')
    refreshing = asyncio.create_task(svc.records('DEV', refresh=True))
    await asyncio.sleep(0)
    assert await asyncio.wait_for(svc.records('DEV'), 1) == RECORDS and not refreshing.done()
    gate.set()
    assert await refreshing == RECORDS
