"""`scripts/run_batch.py --submit`: the command the control run uses, end to end on the fake profile."""

import importlib.util
import json
from pathlib import Path

import pytest

from tests.test_api import DEFAULTS, RECORDS

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def run_batch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    spec = importlib.util.spec_from_file_location('run_batch_under_test', ROOT / 'scripts' / 'run_batch.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    chats = [r for r in RECORDS if r.channel == 'agent chat'][:3]

    async def load(group_id, refresh=False, rejects=None, **_):
        return chats

    monkeypatch.setattr(mod, 'load_dataset', load)
    monkeypatch.setattr(mod, 'STORE', tmp_path / 'store')
    monkeypatch.setattr(mod, 'SEED', DEFAULTS)
    monkeypatch.setattr(mod, 'OUT', tmp_path / 'out')
    monkeypatch.setattr(mod, 'RESULTS', tmp_path / 'results')
    for k in ('EVAL_MODE', 'EVAL_K', 'FALLBACK_PROFILE'):
        monkeypatch.delenv(k, raising=False)
    return mod, chats, tmp_path


async def test_submit_writes_a_valid_results_file(run_batch) -> None:
    mod, chats, tmp = run_batch
    code = await mod.main(['CTRL', '--profile', 'fake', '--submit', 'prod', '--team-name', 'fantastik 4'])
    assert code == 0
    path = tmp / 'results' / 'prod' / 'results.json'
    doc = json.loads(path.read_text(encoding='utf-8'))
    assert [r['conversation_id'] for r in doc['results']] == [r.conversation_id for r in chats]
    assert mod.submission.validate(doc, [r.conversation_id for r in chats]) == []
    # no temp file is left next to it
    assert [p.name for p in path.parent.iterdir()] == ['results.json']
