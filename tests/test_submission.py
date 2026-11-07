import copy
from datetime import UTC, datetime
from pathlib import Path

from server import submission
from server.config import Profile
from server.models import Checklist, Evaluation, Item, Usage
from server.scoring import compute_score

ROOT = Path(__file__).resolve().parents[1]
CHAT = Checklist.model_validate_json((ROOT / 'data/checklists/chat.default.json').read_text(encoding='utf-8'))
# Case (b) from test_scoring: total 69.38, identification N/A.
B = {'c01': 'yes', 'c02': 'no', 'c03': 'na', 'c04': '15', 'c05': 'yes', 'c06': '7', 'c07': 'yes', 'c08': 'no'}
PROFILES = {
    'h200-gemma': Profile(name='h200-gemma', provider='openai', model='gemma-4:31b'),
    'aigw-sonnet': Profile(name='aigw-sonnet', provider='openai', model='anthropic/claude-sonnet-5-5',
                           hosting='external_api'),
}


def evaluation(cid: str, verdicts: dict[str, str], profile: str = 'h200-gemma') -> Evaluation:
    return Evaluation(
        id=f'e-{cid}', conversation_id=cid, group_id='DEV', checklist_id='chat', checklist_version=1,
        profile=profile, model=PROFILES[profile].model, mode='per_criterion', k=1,
        created_at=datetime(2026, 11, 7, tzinfo=UTC),
        items=[Item(criterion_id=k, verdict=v, explanation=f'why {k}', evidence_idx=[0, 4] if k == 'c04' else [])
               for k, v in verdicts.items()],
        score=compute_score(CHAT, verdicts),
        usage=Usage(prompt_tokens=0, completion_tokens=0, calls=8, seconds=0.0),
    )


def test_build_maps_values_turns_and_errors():
    doc = submission.build('Team', ['p1', 'p2'], {'p1': evaluation('p1', B)}, {'p2': 'timeout'}, PROFILES)
    ok, err = doc['results']
    values = {c['criterion_id']: c['value'] for c in ok['criteria']}
    assert values == {'contact': True, 'discovery': False, 'identification': None, 'consultation': 15,
                      'empathy': True, 'dialogue': 7, 'closure': True, 'critical': False}
    consultation = next(c for c in ok['criteria'] if c['criterion_id'] == 'consultation')
    assert consultation['evidence_turns'] == [1, 5]  # 1-based over the raw transcript array
    assert ok['score'] == {'final_score': 69.38, 'critical_flag': False}
    assert err == {'conversation_id': 'p2', 'status': 'error', 'criteria': [], 'score': None, 'error': 'timeout'}
    assert doc['model'] == {'mode': 'local', 'name': 'gemma-4:31b'}
    assert submission.validate(doc, ['p1', 'p2']) == []


def test_fallback_dialog_makes_model_hybrid():
    evs = {'p1': evaluation('p1', B), 'p2': evaluation('p2', B, 'aigw-sonnet')}
    doc = submission.build('Team', ['p1', 'p2'], evs, {}, PROFILES)
    assert doc['model'] == {'mode': 'hybrid', 'name': 'anthropic/claude-sonnet-5-5, gemma-4:31b'}


def test_validate_rejects_appendix_violations():
    good = submission.build('Team', ['p1'], {'p1': evaluation('p1', B)}, {}, PROFILES)

    def broken(mutate):
        doc = copy.deepcopy(good)
        mutate(doc)
        return submission.validate(doc, ['p1'])

    def crit(doc, code):
        return next(c for c in doc['results'][0]['criteria'] if c['criterion_id'] == code)

    assert any('dialogue value True' in p for p in broken(lambda d: crit(d, 'dialogue').update(value=True)))
    assert any('contact value None' in p for p in broken(lambda d: crit(d, 'contact').update(value=None)))
    assert any('consultation value 12' in p for p in broken(lambda d: crit(d, 'consultation').update(value=12)))
    assert any('evidence_turns' in p for p in broken(lambda d: crit(d, 'empathy').update(evidence_turns=[0])))
    assert any('critical_flag' in p for p in broken(lambda d: d['results'][0]['score'].update(critical_flag=True)))
    assert any('exactly once' in p for p in broken(lambda d: d['results'][0]['criteria'].pop()))
    assert any('duplicate' in p for p in broken(lambda d: d['results'].append(copy.deepcopy(d['results'][0]))))
    assert any('missing conversation_ids' in p for p in submission.validate(good, ['p1', 'p9']))
    assert any('team_name' in p for p in broken(lambda d: d.update(team_name=' ')))
