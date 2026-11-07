import json
from pathlib import Path

import jsonschema
import pytest

from server.config import Profile
from server.evaluator import (
    EvaluationError,
    aggregate,
    build_messages,
    build_schema,
    evaluate,
    parse_items,
)
from server.llm.client import Completion
from server.llm.fake import FakeClient
from server.models import Checklist, Record
from server.scoring import compute_score

ROOT = Path(__file__).resolve().parents[1]
CHECKLIST = Checklist.model_validate_json(
    (ROOT / 'data/checklists/chat.default.json').read_text(encoding='utf-8')
)
ALL_IDS = [c.id for c in CHECKLIST.criteria]
PROFILE = Profile(name='t', provider='fake', model='m')


def load_p1() -> Record:
    raw = json.loads((ROOT / 'tests/fixtures/dev.json').read_text(encoding='utf-8'))
    r = next(x for x in raw['data']['records'] if x['conversation_id'] == 'p1-ru-001')
    return Record(**{**r, 'transcript': [{'idx': i, **t} for i, t in enumerate(r['transcript'])]})


P1 = load_p1()


def entry(verdict, evidence=(), expected=None, na=None, explanation='Обоснование'):
    return {
        'explanation': explanation,
        'evidence_idx': list(evidence),
        'expected_range': expected,
        'na_reason': na,
        'verdict': verdict,
    }


VALID = {
    'c01': entry('yes', [9]),
    'c02': entry('na', na='данных хватало с самого начала'),
    'c03': entry('na', na='запрос не требовал идентификации'),
    'c04': entry('20', [9, 9]),
    'c05': entry('yes', [11, 9]),
    'c06': entry('10', [9]),
    'c07': entry('no', [11]),
    'c08': entry('no'),
}


def answer(**override) -> dict:
    return {**VALID, **override}


def comp(obj, finish='stop') -> Completion:
    return Completion(
        text=None if obj is None else '```json\n' + json.dumps(obj, ensure_ascii=False) + '\n```',
        finish_reason=finish,
        prompt_tokens=10,
        completion_tokens=5,
        seconds=0.1,
    )


class Scripted:
    def __init__(self, *script: list[Completion]) -> None:
        self.script = list(script)
        self.calls: list[dict] = []

    async def complete(self, messages, schema, temperature, n):
        self.calls.append({'messages': messages, 'schema': schema, 'temperature': temperature, 'n': n})
        return self.script.pop(0)


async def test_single_mode_valid_run():
    llm = Scripted([comp(answer())])
    ev, raws = await evaluate(P1, CHECKLIST, profile=PROFILE, llm=llm, group_id='G')
    assert [it.criterion_id for it in ev.items] == ALL_IDS
    assert ev.score == compute_score(CHECKLIST, {it.criterion_id: it.verdict for it in ev.items})
    assert len(llm.calls) == 1
    assert llm.calls[0]['schema']['required'] == ALL_IDS
    assert llm.calls[0]['temperature'] == 0.0 and llm.calls[0]['n'] == 1
    assert ev.items[4].evidence_idx == [9, 11]
    assert ev.items[3].evidence_idx == [9]
    assert ev.id.startswith('p1-ru-001-') and len(ev.id) == len('p1-ru-001-') + 8
    assert (ev.profile, ev.model, ev.mode, ev.k, ev.group_id) == ('t', 'm', 'single', 1, 'G')
    assert (ev.checklist_id, ev.checklist_version) == ('chat', 1)
    assert (ev.usage.prompt_tokens, ev.usage.completion_tokens, ev.usage.calls) == (10, 5, 1)
    assert raws[0].evaluation_id == ev.id and raws[0].model == 'm'


async def test_per_criterion_makes_8_calls():
    llm = Scripted(*([comp(answer())] for _ in ALL_IDS))
    ev, raws = await evaluate(P1, CHECKLIST, profile=PROFILE, mode='per_criterion', llm=llm)
    assert len(llm.calls) == 8
    assert sorted(c['schema']['required'][0] for c in llm.calls) == ALL_IDS
    assert all(len(c['schema']['required']) == 1 for c in llm.calls)
    assert [it.criterion_id for it in ev.items] == ALL_IDS
    assert ev.usage.calls == 8 and len(raws) == 8


async def test_bad_evidence_retries_only_that_criterion():
    first = answer(c05=entry('yes', [999]))
    _, errors = parse_items(json.dumps(first), P1, CHECKLIST, ALL_IDS)
    assert list(errors) == ['c05']
    llm = Scripted([comp(first)], [comp({'c05': entry('yes', [9])})])
    ev, raws = await evaluate(P1, CHECKLIST, profile=PROFILE, llm=llm)
    assert len(llm.calls) == 2
    retry = llm.calls[1]
    assert retry['schema']['required'] == ['c05']
    assert list(retry['schema']['properties']) == ['c05']
    assert len(retry['messages']) == 3
    assert errors['c05'] in retry['messages'][-1]['content']
    assert ev.items[4].evidence_idx == [9]
    assert len(raws) == len(llm.calls)
    assert raws[1].criterion_ids == ['c05']


async def test_two_invalid_replies_raise():
    bad = entry('yes', [999])
    llm = Scripted([comp(answer(c05=bad))], [comp({'c05': bad})])
    with pytest.raises(EvaluationError, match='c05'):
        await evaluate(P1, CHECKLIST, profile=PROFILE, llm=llm)
    assert len(llm.calls) == 2


async def test_missing_evidence_twice_keeps_verdict_with_warning():
    # The p1-ru-019 failure mode: a sound verdict without a citation must not discard the dialog.
    bare = entry('yes', [])
    llm = Scripted([comp(answer(c05=bare))], [comp({'c05': bare})])
    ev, _ = await evaluate(P1, CHECKLIST, profile=PROFILE, llm=llm)
    c05 = ev.items[4]
    assert (c05.verdict, c05.evidence_idx) == ('yes', [])
    assert c05.warnings and 'нет подтверждающей реплики' in c05.warnings[0]
    assert all(not it.warnings for it in ev.items if it.criterion_id != 'c05')
    assert ev.score == compute_score(CHECKLIST, {it.criterion_id: it.verdict for it in ev.items})


def test_na_on_c01_rejected():
    obj = answer(c01=entry('na', na='не применимо'))
    items, errors = parse_items(json.dumps(obj), P1, CHECKLIST, ALL_IDS)
    assert list(errors) == ['c01']
    assert 'c01' not in items and len(items) == 7


def test_parse_rules():
    def err(cid, value):
        _, errors = parse_items(json.dumps({cid: value}), P1, CHECKLIST, [cid])
        return errors.get(cid)

    assert err('c01', entry('yes')) is not None
    assert err('c01', entry('no')) is not None
    assert err('c01', entry('no', expected=[9, 11])) is None
    assert err('c01', entry('no', expected=[11, 9])) is not None
    assert err('c01', entry('no', expected=[9, 12])) is not None
    assert err('c04', entry('12', [9])) is not None
    assert err('c04', entry('15')) is not None
    assert err('c02', entry('na')) is not None
    assert err('c08', entry('yes')) is not None
    assert err('c08', entry('no')) is None
    assert err('c01', entry('yes', [-1])) is not None
    _, errors = parse_items('not json', P1, CHECKLIST, ['c01', 'c02'])
    assert set(errors) == {'c01', 'c02'}
    _, errors = parse_items('{}', P1, CHECKLIST, ['c01'])
    assert set(errors) == {'c01'}


async def test_length_finish_counts_invalid_and_retries():
    llm = Scripted([comp(answer(), finish='length')], [comp(answer())])
    ev, raws = await evaluate(P1, CHECKLIST, profile=PROFILE, llm=llm)
    assert len(llm.calls) == 2 and len(raws) == 2
    assert llm.calls[1]['schema']['required'] == ALL_IDS
    assert 'ответ обрезан или пуст' in llm.calls[1]['messages'][-1]['content']
    assert [it.criterion_id for it in ev.items] == ALL_IDS


async def test_k3_majority_vote():
    llm = Scripted(
        [comp(answer()), comp(answer(c01=entry('no', [9]))), comp(answer())]
    )
    ev, _ = await evaluate(P1, CHECKLIST, profile=PROFILE, k=3, llm=llm)
    c01 = ev.items[0]
    assert c01.verdict == 'yes'
    assert c01.votes == {'yes': 2, 'no': 1}
    assert llm.calls[0]['temperature'] == 0.7 and llm.calls[0]['n'] == 3
    assert ev.usage.prompt_tokens == 30 and ev.usage.calls == 1


async def test_k3_scale_median():
    llm = Scripted(
        [
            comp(answer(c06=entry('4', [9], explanation='четыре'))),
            comp(answer(c06=entry('10', [9], explanation='десять'))),
            comp(answer(c06=entry('7', [11], explanation='семь'))),
        ]
    )
    ev, _ = await evaluate(P1, CHECKLIST, profile=PROFILE, k=3, llm=llm)
    c06 = ev.items[5]
    assert c06.verdict == '7'
    assert c06.explanation == 'семь' and c06.evidence_idx == [11]
    assert c06.votes == {'4': 1, '10': 1, '7': 1}


def test_aggregate_tie_and_even_median():
    def items(cid, *verdicts):
        return [
            parse_items(json.dumps({cid: entry(v, [9])}), P1, CHECKLIST, [cid])[0] for v in verdicts
        ]

    assert aggregate(items('c01', 'no', 'yes'), CHECKLIST, ['c01'])['c01'].verdict == 'no'
    assert aggregate(items('c06', '10', '4', '7', '0'), CHECKLIST, ['c06'])['c06'].verdict == '4'
    mixed = items('c04', '20', '15') + [
        parse_items(json.dumps({'c04': entry('na', na='x')}), P1, CHECKLIST, ['c04'])[0]
    ]
    assert aggregate(mixed, CHECKLIST, ['c04'])['c04'].verdict == '20'


async def test_empty_transcript_no_calls():
    llm = Scripted()
    empty = P1.model_copy(update={'transcript': []})
    with pytest.raises(EvaluationError, match='пустой транскрипт'):
        await evaluate(empty, CHECKLIST, profile=PROFILE, llm=llm)
    assert llm.calls == []


def test_schema_order_and_enum():
    schema = build_schema(CHECKLIST, ALL_IDS)
    assert schema['additionalProperties'] is False
    assert schema['required'] == ALL_IDS
    for cid in ALL_IDS:
        prop = schema['properties'][cid]
        keys = ['explanation', 'evidence_idx', 'expected_range', 'na_reason', 'verdict']
        assert list(prop['properties']) == keys
        assert prop['required'] == keys
        assert prop['additionalProperties'] is False
    assert schema['properties']['c04']['properties']['verdict']['enum'] == ['0', '5', '10', '15', '20', 'na']
    assert schema['properties']['c01']['properties']['verdict']['enum'] == ['yes', 'no']


def test_prompt_contents():
    ids = ['c02', 'c04', 'c08']
    system, user = build_messages(P1, CHECKLIST, ids)
    assert system['role'] == 'system' and user['role'] == 'user'
    text = system['content'] + user['content']
    for cid in ids:
        assert cid in text
    assert 'c01' not in system['content']
    assert CHECKLIST.notes in system['content']
    assert 'Правила чек-листа' in system['content']
    assert 'N/A не допускается' in system['content']
    assert 'Ты — эксперт по контролю качества контакт-центра Freedom Broker' in system['content']
    lines = user['content'].splitlines()
    assert lines[0] == 'Канал: agent chat; язык диалога: RU; диалог: p1-ru-001'
    assert '[0] (00:00) client: ' in user['content']
    assert lines[-1] == 'Верни JSON строго по схеме для критериев: c02, c04, c08'


async def test_fake_client_output_parses():
    schema = build_schema(CHECKLIST, ALL_IDS)
    comps = await FakeClient().complete(build_messages(P1, CHECKLIST, ALL_IDS), schema, 0.7, 4)
    for c in comps:
        jsonschema.validate(json.loads(c.text), schema)
        items, errors = parse_items(c.text, P1, CHECKLIST, ALL_IDS)
        assert errors == {}
        assert list(items) == ALL_IDS


def ensemble_profiles(tmp_path, *members: str):
    from server.config import load_profiles
    path = tmp_path / 'profiles.toml'
    path.write_text(
        '[profiles.f1]\nprovider = "fake"\nmodel = "m1"\n'
        '[profiles.f2]\nprovider = "fake"\nmodel = "m2"\nhosting = "external_api"\n'
        '[profiles.dead]\nprovider = "openai"\nbase_url_env = "CQA_TEST_UNSET_URL"\nmodel = "dead"\n'
        f'[profiles.ens]\nprovider = "ensemble"\nmembers = {list(members)!r}\n'.replace("'", '"'),
        encoding='utf-8',
    )
    return load_profiles(path)


async def test_ensemble_votes_per_criterion(tmp_path):
    profiles = ensemble_profiles(tmp_path, 'f1:per_criterion', 'f1:single', 'f2:single')
    ens = profiles['ens']
    assert ens.model == 'm1, m2' and ens.hosting == 'hybrid'
    ev, raw = await evaluate(P1, CHECKLIST, profile=ens, mode='single')
    by_id = {c.id: c for c in CHECKLIST.criteria}
    for it in ev.items:
        assert sum(it.votes.values()) == 3
        if by_id[it.criterion_id].answer_type == 'scale' and 'na' not in it.votes:
            ladder = sorted(int(v) for v, n in it.votes.items() for _ in range(n))
            assert int(it.verdict) == ladder[1]  # median of three
        else:
            assert it.votes[it.verdict] == max(it.votes.values())
    assert ev.score.total == compute_score(CHECKLIST, {i.criterion_id: i.verdict for i in ev.items}).total
    assert ev.usage.calls == len(raw) == 8 + 1 + 1 and {r.evaluation_id for r in raw} == {ev.id}
    assert ev.profile == 'ens' and all(it.warnings == [] for it in ev.items)


async def test_ensemble_drops_a_dead_member_and_fails_when_all_are_dead(tmp_path):
    ens = ensemble_profiles(tmp_path, 'dead:single', 'f1:single', 'f2:single')['ens']
    ev, _ = await evaluate(P1, CHECKLIST, profile=ens, mode='single')
    assert all(sum(it.votes.values()) == 2 and 'ансамбль без dead' in it.warnings for it in ev.items)

    gone = ensemble_profiles(tmp_path, 'dead:single', 'dead:per_criterion')['ens']
    with pytest.raises(EvaluationError, match='ни один участник'):
        await evaluate(P1, CHECKLIST, profile=gone, mode='single')


def test_ensemble_config_errors(tmp_path):
    from server.config import ConfigError
    with pytest.raises(ConfigError, match='nope'):
        ensemble_profiles(tmp_path, 'nope:single', 'f1:single')
    with pytest.raises(ConfigError, match='needs a mode'):
        ensemble_profiles(tmp_path, 'f1', 'f2:single')
