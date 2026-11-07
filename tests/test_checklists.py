from pathlib import Path

import pytest

from server.checklists import ChecklistError, ChecklistStore, validate
from server.models import Checklist, Criterion, ScaleStep, Section
from server.store import NotFound

ROOT = Path(__file__).resolve().parent.parent
DEFAULTS = ROOT / 'data' / 'checklists'


def load(name: str) -> Checklist:
    return Checklist.model_validate_json((DEFAULTS / f'{name}.default.json').read_text(encoding='utf-8'))


def edit(cid: str, **changes) -> Checklist:
    """The chat default with criterion `cid` updated."""
    c = load('chat')
    criteria = [cr.model_copy(update=changes) if cr.id == cid else cr for cr in c.criteria]
    return c.model_copy(update={'criteria': criteria})


def steps(*values: int) -> list[ScaleStep]:
    return [ScaleStep(value=v, description=f'ступень {v}') for v in values]


def yes_no(cid: str, weight: float, section: str | None = None) -> Criterion:
    return Criterion(
        id=cid, section_id=section, title=cid, description='', answer_type='yes_no',
        weight=weight, steps=None, na_allowed=False, na_condition=None,
    )


@pytest.mark.parametrize('name', ['chat', 'call'])
def test_defaults_are_valid(name: str) -> None:
    assert validate(load(name)) == []


def _duplicate_id() -> Checklist:
    c = load('chat')
    criteria = list(c.criteria)
    criteria[1] = criteria[1].model_copy(update={'id': 'c01'})
    return c.model_copy(update={'criteria': criteria})


def _zero_sum() -> Checklist:
    return Checklist(
        id='z', name='Нули', channel_default=None, version=1, sections=[],
        criteria=[yes_no('a', 0), yes_no('b', 0)], notes='', source='',
    )


def _empty_section_title() -> Checklist:
    c = load('chat')
    sections = [Section(id='s1', title=' ')] + c.sections[1:]
    return c.model_copy(update={'sections': sections})


INVALID = {
    'duplicate criterion id': _duplicate_id,
    'scale without steps': lambda: edit('c04', steps=None),
    'scale with one step': lambda: edit('c04', steps=steps(20)),
    'duplicate step values': lambda: edit('c04', steps=steps(0, 5, 5, 20)),
    'yes_no with steps': lambda: edit('c01', steps=steps(0, 1)),
    'negative weight': lambda: edit('c01', weight=-1),
    'gross_error with weight': lambda: edit('c08', weight=5),
    'gross_error as scale': lambda: edit('c08', answer_type='scale', steps=steps(0, 1)),
    'unknown section': lambda: edit('c01', section_id='s9'),
    'zero scored weight sum': _zero_sum,
    'empty checklist id': lambda: load('chat').model_copy(update={'id': ''}),
    'empty checklist name': lambda: load('chat').model_copy(update={'name': '  '}),
    'empty criterion id': lambda: edit('c01', id=''),
    'empty criterion title': lambda: edit('c01', title=''),
    'empty section title': _empty_section_title,
    'scale with zero weight': lambda: edit('c04', weight=0),
}


@pytest.mark.parametrize('case', INVALID)
def test_invalid_gives_one_error(case: str) -> None:
    errors = validate(INVALID[case]())
    assert len(errors) == 1, errors


def test_several_gross_errors_allowed() -> None:
    c = load('chat')
    extra = c.criteria[-1].model_copy(update={'id': 'c09', 'title': 'Ещё одна грубая ошибка'})
    assert validate(c.model_copy(update={'criteria': [*c.criteria, extra]})) == []


@pytest.fixture
async def store(tmp_path: Path) -> ChecklistStore:
    s = ChecklistStore(tmp_path / 'checklists')
    await s.seed_defaults(DEFAULTS)
    return s


async def test_save_creates_new_versions(store: ChecklistStore) -> None:
    v1 = await store.get('chat')
    assert v1.version == 1
    v2 = await store.save(v1.model_copy(update={'name': 'Версия 2'}))
    v3 = await store.save(v2.model_copy(update={'name': 'Версия 3'}))
    assert (v2.version, v3.version) == (2, 3)
    assert (await store.get('chat', 2)).name == 'Версия 2'
    assert (await store.get('chat')).name == 'Версия 3'
    assert (await store.get('chat', 1)).name == v1.name
    assert sorted(p.name for p in (store.root / 'chat').glob('v*.json')) == ['v1.json', 'v2.json', 'v3.json']


async def test_save_rejects_invalid(store: ChecklistStore) -> None:
    with pytest.raises(ChecklistError) as info:
        await store.save(edit('c01', weight=-1))
    assert info.value.details and len(info.value.details) == 1
    assert (await store.get('chat')).version == 1


async def test_create_existing_id_raises(store: ChecklistStore) -> None:
    with pytest.raises(ChecklistError):
        await store.create(load('chat'))


async def test_create_starts_at_v1(store: ChecklistStore) -> None:
    c = load('chat').model_copy(update={'id': 'chat2', 'version': 7})
    assert (await store.create(c)).version == 1
    assert [s.id for s in await store.list()] == ['call', 'chat', 'chat2']


async def test_unknown_ids(store: ChecklistStore) -> None:
    with pytest.raises(NotFound):
        await store.get('nope')
    with pytest.raises(NotFound):
        await store.get('chat', 9)
    with pytest.raises(NotFound):
        await store.save(load('chat').model_copy(update={'id': 'nope'}))


async def test_seed_keeps_existing(store: ChecklistStore) -> None:
    await store.save((await store.get('chat')).model_copy(update={'name': 'Моя'}))
    await store.seed_defaults(DEFAULTS)
    assert (await store.get('chat')).name == 'Моя'


async def test_default_for(store: ChecklistStore) -> None:
    assert (await store.default_for('voice call')).id == 'call'
    assert (await store.default_for('agent chat')).id == 'chat'
    saved = await store.save((await store.get('call')).model_copy(update={'name': 'Звонки v2'}))
    got = await store.default_for('voice call')
    assert (got.id, got.version) == ('call', saved.version)


async def test_default_for_falls_back_to_chat(tmp_path: Path) -> None:
    s = ChecklistStore(tmp_path / 'checklists')
    await s.create(load('chat').model_copy(update={'channel_default': None}))
    assert (await s.default_for('voice call')).id == 'chat'


async def test_seed_drift_catches_ui_edits_and_newer_copies(store: ChecklistStore) -> None:
    channels = ['agent chat', 'voice call']
    assert await store.seed_drift(DEFAULTS, channels) == []
    # A weight edit in the editor makes v2 the chat default: drift.
    await store.save(edit('c07', weight=10))
    [(current, seed)] = await store.seed_drift(DEFAULTS, channels)
    assert (current.id, current.version, seed.id) == ('chat', 2, 'chat')
    # Saving the seed content back restores parity, even though the version is now 3.
    await store.save(seed)
    assert await store.seed_drift(DEFAULTS, channels) == []
    # A newer checklist that claims the chat channel wins `default_for`, so it is drift too.
    await store.create(load('chat').model_copy(update={'id': 'chat-copy', 'name': 'Копия'}))
    [(current, _)] = await store.seed_drift(DEFAULTS, ['agent chat'])
    assert current.id == 'chat-copy'
