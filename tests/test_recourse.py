import json

import pytest
from litestar.testing import AsyncTestClient

import server.evaluator.run as run_mod
import server.recourse as rec_mod
from server.llm.client import Completion
from server.llm.fake import FakeClient
from server.models import Record, Turn
from server.recourse import Edit, apply_edits, validate_edits
from tests.test_api import CHATS, RECORDS, client, evaluate_one, fake_env  # noqa: F401

MARK = '[сумма] будет списана после подтверждения'


class Stub:
    """Proposal calls (schema has `edits`) return a scripted edit; judge calls are the fake judge,
    except a dialog containing MARK gets the best verdict everywhere."""

    def __init__(self, edits: list[dict]) -> None:
        self.edits = edits
        self.judge_schemas: list[list[str]] = []
        self.fake = FakeClient()
        self.worst = False

    async def complete(self, messages, schema, temperature, n):
        user = next(m['content'] for m in reversed(messages) if m['role'] == 'user')
        if 'edits' in schema['properties']:
            text = json.dumps({'edits': self.edits, 'rationale': 'Оператор должен был назвать сумму.'}, ensure_ascii=False)
            return [Completion(text=text, finish_reason='stop', prompt_tokens=0, completion_tokens=0, seconds=0.0)]
        self.judge_schemas.append(list(schema['properties']))
        out = await self.fake.complete(messages, schema, temperature, n)
        if MARK in user or self.worst:
            res = []
            for comp in out:
                obj = json.loads(comp.text)
                for cid, spec in schema['properties'].items():
                    enum = spec['properties']['verdict']['enum']
                    nums = [int(v) for v in enum if v.lstrip('-').isdigit()]
                    best = 'yes' if 'yes' in enum else str(max(nums))
                    worst = 'no' if 'no' in enum else str(min(nums))
                    obj[cid]['verdict'] = worst if self.worst and MARK not in user else best
                    obj[cid]['expected_range'] = None
                    obj[cid]['na_reason'] = None
                res.append(comp.model_copy(update={'text': json.dumps(obj, ensure_ascii=False)}))
            return res
        return out


def lost(view: dict) -> list[dict]:
    return [
        i for i in view['evaluation']['score']['items']
        if i['points'] is not None and i['points'] < i['max_points'] and i['criterion_id'] != 'c08'
    ]


async def find_case(client: AsyncTestClient) -> tuple[dict, str, Record]:
    for cid in CHATS:
        view = await evaluate_one(client, cid)
        if lost(view):
            return view, lost(view)[0]['criterion_id'], next(r for r in RECORDS if r.conversation_id == cid)
    raise AssertionError('no chat with a lost criterion')


def operator_idx(record: Record) -> int:
    return next(t.idx for t in record.transcript if t.speaker == 'operator')


def patch(monkeypatch, stub: Stub) -> None:
    monkeypatch.setattr(rec_mod, 'make_client', lambda p: stub)
    monkeypatch.setattr(run_mod, 'make_client', lambda p: stub)


async def test_recourse_verifies_and_changes_only_operator(client: AsyncTestClient, monkeypatch) -> None:
    view, crit, record = await find_case(client)
    ev_id = view['evaluation']['id']
    stub = Stub([{'idx': operator_idx(record), 'insert_after': None, 'new_text': MARK}])
    patch(monkeypatch, stub)

    r = await client.post(f'/api/evaluations/{ev_id}/recourse', json={'criterion_id': crit})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body['verified'] is True
    assert body['after']['points'] > body['before']['points']
    assert body['edits'][0]['new_text'] == MARK
    assert stub.judge_schemas == [[crit]]  # re-judged on exactly one criterion

    again = (await client.get(f'/api/evaluations/{ev_id}')).json()
    assert again['evaluation']['score'] == view['evaluation']['score']
    assert again['final'] == view['final'] and again['appeals'] == []
    cid = record.conversation_id
    assert len((await client.get(f'/api/conversations/{cid}/evaluations')).json()) == 1

    calls = len(stub.judge_schemas)
    stub.edits = []
    assert (await client.post(f'/api/evaluations/{ev_id}/recourse', json={'criterion_id': crit})).json() == body
    assert len(stub.judge_schemas) == calls  # cached


def test_edits_touch_operator_turns_only() -> None:
    rec = Record(
        conversation_id='x', channel='agent chat', language='RU', audio_url=None,
        transcript=[
            Turn(idx=0, timestamp='t', speaker='client', text='привет'),
            Turn(idx=1, timestamp='t', speaker='operator', text='старый'),
            Turn(idx=2, timestamp='t', speaker='bot', text='бот'),
            Turn(idx=3, timestamp='t', speaker='client', text='ок'),
        ],
    )
    edits, _ = validate_edits(rec, {'edits': [
        {'idx': 1, 'insert_after': None, 'new_text': 'новый'},
        {'idx': None, 'insert_after': 3, 'new_text': 'вставка'},
    ], 'rationale': ''})
    out = apply_edits(rec, edits)
    assert [t.speaker for t in out.transcript] == ['client', 'operator', 'bot', 'client', 'operator']
    assert [t.idx for t in out.transcript] == [0, 1, 2, 3, 4]
    assert [t.text for t in out.transcript] == ['привет', 'новый', 'бот', 'ок', 'вставка']
    for bad in (
        {'idx': 0, 'insert_after': None, 'new_text': 'x'},
        {'idx': 2, 'insert_after': None, 'new_text': 'x'},
        {'idx': None, 'insert_after': 9, 'new_text': 'x'},
        {'idx': 1, 'insert_after': 1, 'new_text': 'x'},
    ):
        with pytest.raises(ValueError):
            validate_edits(rec, {'edits': [bad], 'rationale': ''})
    with pytest.raises(ValueError):
        validate_edits(rec, {'edits': [Edit(idx=1, new_text='a').model_dump()] * 3, 'rationale': ''})


async def test_recourse_rejects_gross_and_unlost(client: AsyncTestClient, monkeypatch) -> None:
    view, crit, record = await find_case(client)
    ev_id = view['evaluation']['id']
    stub = Stub([])
    patch(monkeypatch, stub)

    gross = [c['id'] for c in view['checklist']['criteria'] if c['kind'] == 'gross_error' or c['id'] == 'c08']
    assert gross
    for g in gross:
        r = await client.post(f'/api/evaluations/{ev_id}/recourse', json={'criterion_id': g})
        assert r.status_code == 400 and 'грубая' in r.json()['error']

    full = next((i for i in view['evaluation']['score']['items'] if i['points'] and i['points'] == i['max_points']), None)
    if full:
        r = await client.post(f'/api/evaluations/{ev_id}/recourse', json={'criterion_id': full['criterion_id']})
        assert r.status_code == 400
    assert (await client.post(f'/api/evaluations/{ev_id}/recourse', json={'criterion_id': 'zz'})).status_code == 404
    assert stub.judge_schemas == []


async def test_recourse_not_verified_when_judge_unmoved(client: AsyncTestClient, monkeypatch) -> None:
    view, crit, record = await find_case(client)
    stub = Stub([{'idx': operator_idx(record), 'insert_after': None, 'new_text': 'просто другая фраза'}])
    stub.worst = True
    patch(monkeypatch, stub)
    r = await client.post(f'/api/evaluations/{view["evaluation"]["id"]}/recourse', json={'criterion_id': crit})
    assert r.status_code == 200 and r.json()['verified'] is False
