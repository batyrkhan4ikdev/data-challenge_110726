import json
from datetime import UTC, datetime

from litestar.testing import AsyncTestClient

from server.models import Appeal, Checklist, Evaluation, Item, Record, Turn, Usage
from server.scoring import compute_score
from server.triage import attention
from tests.test_api import CHATS, DEFAULTS, client, evaluate_one, fake_env  # noqa: F401

CHECKLIST = Checklist.model_validate(json.loads((DEFAULTS / 'chat.default.json').read_text(encoding='utf-8')))


def make_eval(verdicts: dict[str, str], **item_kw) -> Evaluation:
    full = {c.id: 'yes' if c.answer_type == 'yes_no' else str(max(s.value for s in c.steps or [])) for c in CHECKLIST.criteria}
    full['c08'] = 'no'
    full.update(verdicts)
    return Evaluation(
        id='ev1', conversation_id='x', group_id='DEV', checklist_id=CHECKLIST.id, checklist_version=CHECKLIST.version,
        profile='fake', model='fake', mode='single', k=1, created_at=datetime.now(UTC),
        items=[Item(criterion_id=k, verdict=v, explanation='', evidence_idx=[0], **item_kw.get(k, {})) for k, v in full.items()],
        score=compute_score(CHECKLIST, full), usage=Usage(prompt_tokens=0, completion_tokens=0, calls=0, seconds=0),
    )


def record(first_operator: str) -> Record:
    return Record(
        conversation_id='x', channel='agent chat', language='RU', audio_url=None,
        transcript=[
            Turn(idx=0, timestamp='00:00', speaker='client', text='Помогите'),
            Turn(idx=1, timestamp='00:30', speaker='operator', text=first_operator),
        ],
    )


def test_clean_evaluation_has_no_attention_and_is_deterministic() -> None:
    ev = make_eval({})
    a = attention(CHECKLIST, ev, [], record('Здравствуйте!'))
    assert a.score == 0 and a.reasons == [] and a.criterion_ids == []
    assert attention(CHECKLIST, ev, [], record('Здравствуйте!')) == a


def test_reasons_and_disputed_criteria() -> None:
    ev = make_eval({'c06': '4', 'c05': 'no'}, c04={'warnings': ['no evidence']}, c07={'votes': {'yes': 2, 'no': 1}})
    open_appeal = Appeal(id='a', evaluation_id='ev1', criterion_id='c02', comment='x', created_at=datetime.now(UTC),
                         status='open', decision=None)
    rec = record('Чем могу помочь?')
    a = attention(CHECKLIST, ev, [open_appeal], rec)
    assert a.score > 0
    assert a.criterion_ids == ['c01', 'c02', 'c04', 'c05', 'c06', 'c07']
    joined = '\n'.join(a.reasons)
    for needle in ('фолбэк', 'голоса', 'апелляция по c02', 'нет приветствия', 'c06'):
        assert needle in joined, needle
    assert a == attention(CHECKLIST, ev, [open_appeal], rec)


def test_gross_error_dominates() -> None:
    a = attention(CHECKLIST, make_eval({'c08': 'yes'}), [], record('Здравствуйте'))
    assert a.reasons[0] == 'Зафиксирована грубая ошибка' and a.criterion_ids == ['c08']


async def test_conversations_expose_attention(client: AsyncTestClient) -> None:
    await evaluate_one(client, CHATS[0])
    rows = {r['conversation_id']: r for r in (await client.get('/api/datasets/DEV/conversations')).json()}
    assert rows[CHATS[0]]['attention']['score'] >= 0
    assert [r for r in rows.values() if r['latest'] is None][0]['attention'] is None


async def test_batch_confirmation_never_changes_total(client: AsyncTestClient) -> None:
    view = await evaluate_one(client, CHATS[0])
    ev_id = view['evaluation']['id']
    before = view['final']
    rows = {r['conversation_id']: r for r in (await client.get('/api/datasets/DEV/conversations')).json()}
    disputed = set(rows[CHATS[0]]['attention']['criterion_ids'])
    all_ids = [c['id'] for c in view['checklist']['criteria']]
    undisputed = [i for i in all_ids if i not in disputed]

    r = await client.post(f'/api/evaluations/{ev_id}/confirmations', json={'criterion_ids': undisputed, 'mode': 'batch', 'reviewer': 'Аня'})
    assert r.status_code == 200, r.text
    assert r.json()['auto_note'] == 'принято пакетом без раскрытия доказательств: ' + ', '.join(undisputed)
    listed = (await client.get(f'/api/evaluations/{ev_id}/confirmations')).json()
    assert [c['id'] for c in listed] == [r.json()['id']]
    assert (await client.get(f'/api/evaluations/{ev_id}')).json()['final'] == before

    if disputed:
        bad = await client.post(f'/api/evaluations/{ev_id}/confirmations', json={'criterion_ids': sorted(disputed), 'mode': 'batch', 'reviewer': 'Аня'})
        assert bad.status_code == 400
        ok = await client.post(f'/api/evaluations/{ev_id}/confirmations', json={'criterion_ids': sorted(disputed)[:1], 'mode': 'single', 'reviewer': 'Аня'})
        assert ok.status_code == 200 and ok.json()['auto_note'] is None

    stats = (await client.get('/api/confirmations/stats')).json()
    assert stats['batch'] == len(undisputed) and stats['single'] == (1 if disputed else 0)


async def test_confirmation_validation(client: AsyncTestClient) -> None:
    ev_id = (await evaluate_one(client, CHATS[0]))['evaluation']['id']
    url = f'/api/evaluations/{ev_id}/confirmations'
    assert (await client.post(url, json={'criterion_ids': ['zz'], 'mode': 'single', 'reviewer': 'a'})).status_code == 400
    assert (await client.post(url, json={'criterion_ids': [], 'mode': 'single', 'reviewer': 'a'})).status_code == 400
    assert (await client.post(url, json={'criterion_ids': ['c01'], 'mode': 'single', 'reviewer': ' '})).status_code == 400
    assert (await client.get('/api/evaluations/nope/confirmations')).status_code == 404
