from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from server.models import (
    Appeal,
    Checklist,
    Criterion,
    Decision,
    Evaluation,
    Item,
    Section,
    Usage,
)
from server.scoring import allowed_verdicts, compute_score, final_result

ROOT = Path(__file__).resolve().parents[1]
CHAT = Checklist.model_validate_json(
    (ROOT / 'data/checklists/chat.default.json').read_text(encoding='utf-8')
)

A = {'c01': 'yes', 'c02': 'yes', 'c03': 'yes', 'c04': '20', 'c05': 'yes', 'c06': '10', 'c07': 'yes', 'c08': 'no'}
B = {'c01': 'yes', 'c02': 'no', 'c03': 'na', 'c04': '15', 'c05': 'yes', 'c06': '7', 'c07': 'yes', 'c08': 'no'}
C = {'c01': 'yes', 'c02': 'yes', 'c03': 'na', 'c04': '5', 'c05': 'no', 'c06': '7', 'c07': 'no', 'c08': 'no'}
T0 = datetime(2026, 11, 7, tzinfo=UTC)


def crit(cid: str) -> Criterion:
    return next(c for c in CHAT.criteria if c.id == cid)


def test_allowed_verdicts():
    assert allowed_verdicts(crit('c04')) == ['0', '5', '10', '15', '20', 'na']
    assert allowed_verdicts(crit('c01')) == ['yes', 'no']
    assert allowed_verdicts(crit('c08')) == ['yes', 'no']


def test_all_yes():
    s = compute_score(CHAT, A)
    assert s.total == 100.0
    assert s.gross_error is False


def test_na_redistribution():
    s = compute_score(CHAT, B)
    assert s.total == 69.38
    assert s.applicable_weight == 80
    items = {i.criterion_id: i for i in s.items}
    assert items['c06'].points == 10.5
    assert items['c03'].applicable is False and items['c03'].points is None
    assert items['c08'].max_points == 0 and items['c08'].points is None


def test_half_up_rounding_and_sections():
    s = compute_score(CHAT, C)
    assert s.total == 50.63
    assert {x.section_id: x.total for x in s.sections} == {'s1': 100.0, 's2': 25.0, 's3': 30.0, 's4': None}


def test_gross_error_flag():
    s = compute_score(CHAT, {**A, 'c08': 'yes'})
    assert s.gross_error is True
    assert s.total == 100.0


def test_all_na_total_none():
    cl = Checklist(
        id='x', name='x', channel_default=None, version=1,
        sections=[Section(id='s1', title='S')],
        criteria=[
            Criterion(id=i, section_id='s1', title=i, description='', answer_type='yes_no',
                      weight=10, steps=None, na_allowed=True, na_condition='n')
            for i in ('a', 'b')
        ],
        notes='', source='',
    )
    s = compute_score(cl, {'a': 'na', 'b': 'na'})
    assert s.total is None
    assert s.sections[0].total is None
    assert all(i.effective_points is None for i in s.items)


@pytest.mark.parametrize('verdicts', [
    {**A, 'c01': 'na'},
    {**A, 'c04': '12'},
    {k: v for k, v in A.items() if k != 'c05'},
    {**A, 'c99': 'yes'},
])
def test_invalid_verdicts(verdicts):
    with pytest.raises(ValueError):
        compute_score(CHAT, verdicts)


def appeal(aid, cid, decision):
    return Appeal(id=aid, evaluation_id='e1', criterion_id=cid, comment='c', created_at=T0,
                  status='resolved' if decision else 'open', decision=decision)


def test_final_result():
    ev = Evaluation(
        id='e1', conversation_id='p1', group_id='DEV', checklist_id='chat', checklist_version=1,
        profile='t', model='m', mode='single', k=1, created_at=T0,
        items=[Item(criterion_id=k, verdict=v, explanation='', evidence_idx=[]) for k, v in B.items()],
        score=compute_score(CHAT, B),
        usage=Usage(prompt_tokens=0, completion_tokens=0, calls=1, seconds=0.0),
    )
    older = Decision(action='change', new_verdict='4', reason='r', decided_at=T0)
    newer = Decision(action='change', new_verdict='10', reason='r', decided_at=T0 + timedelta(hours=1))
    confirm = Decision(action='confirm', new_verdict=None, reason='ok', decided_at=T0)
    fr = final_result(CHAT, ev, [
        appeal('a1', 'c06', newer),
        appeal('a2', 'c06', older),
        appeal('a3', 'c01', None),
        appeal('a4', 'c02', confirm),
    ])
    assert fr.score.total == 75.0
    assert ev.score.total == 69.38
    items = {i.criterion_id: i for i in fr.items}
    assert items['c06'].final_verdict == '10' and items['c06'].decision == newer
    assert items['c06'].original_verdict == '7'
    assert items['c01'].decision is None and items['c01'].final_verdict == 'yes'
    assert items['c02'].decision == confirm and items['c02'].final_verdict == 'no'
