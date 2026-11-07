import re
from pathlib import Path

import pytest

from server.models import Checklist

ROOT = Path(__file__).resolve().parent.parent
CHECKLIST_DOC = ROOT / 'docs' / 'CQA_Chat_Quality_Checklist.md'


def load(name: str) -> Checklist:
    path = ROOT / 'data' / 'checklists' / f'{name}.default.json'
    return Checklist.model_validate_json(path.read_text(encoding='utf-8'))


def norm(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


@pytest.fixture(params=['chat', 'call'])
def checklist(request: pytest.FixtureRequest) -> Checklist:
    return load(request.param)


def test_structure(checklist: Checklist) -> None:
    crit = checklist.criteria
    assert [c.id for c in crit] == [f'c0{i}' for i in range(1, 9)]
    assert [c.weight for c in crit] == [10, 15, 20, 20, 15, 15, 5, 0]
    assert [c.section_id for c in crit] == ['s1', 's1', 's2', 's2', 's3', 's3', 's3', 's4']
    expected_na = {'c02', 'c03', 'c04', 'c07'} | ({'c01'} if checklist.id == 'call' else set())  # call c01: #2978
    assert {c.id for c in crit if c.na_allowed} == expected_na
    by_id = {c.id: c for c in crit}
    assert [s.value for s in by_id['c04'].steps] == [0, 5, 10, 15, 20]
    assert [s.value for s in by_id['c06'].steps] == [0, 4, 7, 10]
    assert by_id['c08'].kind == 'gross_error'
    for c in crit:
        for s in c.steps or []:
            assert s.description.strip()


def test_channels() -> None:
    assert load('chat').channel_default == 'agent chat'
    assert load('call').channel_default == 'voice call'


def test_chat_text_is_verbatim() -> None:
    doc = norm(CHECKLIST_DOC.read_text(encoding='utf-8'))
    for c in load('chat').criteria:
        assert norm(c.description) in doc
        if c.na_condition:
            assert norm(c.na_condition) in doc


def test_call_pauses() -> None:
    c06 = next(c for c in load('call').criteria if c.id == 'c06')
    assert 'управление паузами' in c06.description
