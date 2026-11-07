import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from litestar.testing import AsyncTestClient

from server.analytics import ks_pvalue, ks_statistic, psi, psi_verdict, total_bin
from server.app import create_app
from server.dataset import load_fixture
from server.models import Checklist, Evaluation, Item, Usage
from server.scoring import compute_score
from server.store import Store

ROOT = Path(__file__).resolve().parent.parent
DEFAULTS = ROOT / 'data' / 'checklists'
RECORDS = load_fixture(ROOT / 'tests' / 'fixtures' / 'dev.json')
CHATS = [r.conversation_id for r in RECORDS if r.channel == 'agent chat']
BASELINE = ROOT / 'bench' / 'baselines' / '20261107-195213'


def test_psi_known_values() -> None:
    assert psi({'a': 5, 'b': 5}, {'a': 5, 'b': 5}) == pytest.approx(0.0)
    # (0.8-0.5)ln(1.6) + (0.2-0.5)ln(0.4)
    assert psi({'a': 50, 'b': 50}, {'a': 80, 'b': 20}) == pytest.approx(0.41589, abs=1e-4)
    assert psi({}, {'a': 1}) is None
    assert [psi_verdict(x) for x in (0.05, 0.1, 0.25, 0.26)] == ['stable', 'watch', 'watch', 'drift']
    assert [total_bin(x) for x in (0, 9.99, 10, 99.9, 100)] == [0, 0, 1, 9, 9]


def test_ks_known_values() -> None:
    assert ks_statistic([1, 2, 3], [1, 2, 3]) == 0.0
    assert ks_statistic(list(range(10)), list(range(20, 30))) == 1.0
    assert ks_statistic([1, 2, 3, 4], [3, 4, 5, 6]) == pytest.approx(0.5)
    assert ks_statistic([], [1]) is None
    # D=1, n=m=10: lambda = sqrt(5); p = 2*sum((-1)^(k-1) exp(-10 k^2))
    assert ks_pvalue(1.0, 10, 10) == pytest.approx(2 * (math.exp(-10) - math.exp(-40)), rel=1e-9)
    assert ks_pvalue(0.0, 10, 10) == 1.0
    # classic table value: lambda = 1.358 -> p ~ 0.05
    n = 100
    assert ks_pvalue(1.358 / math.sqrt(n / 2), n, n) == pytest.approx(0.05, abs=1e-3)


async def _seed(store: Store, group: str, n: int, verdicts: dict[str, str], start: datetime) -> None:
    chat = Checklist.model_validate_json((DEFAULTS / 'chat.default.json').read_text(encoding='utf-8'))
    for i, cid in enumerate(CHATS[:n]):
        await store.save_evaluation(
            Evaluation(
                id=f'{group}-{i}', conversation_id=cid, group_id=group, checklist_id=chat.id,
                checklist_version=chat.version, profile='t', model='m', mode='single', k=1,
                created_at=start + timedelta(minutes=i),
                items=[Item(criterion_id=k, verdict=v, explanation='', evidence_idx=[]) for k, v in verdicts.items()],
                score=compute_score(chat, verdicts),
                usage=Usage(prompt_tokens=0, completion_tokens=0, calls=1, seconds=0.0),
            ),
            [],
        )


async def test_analytics_drift_between_groups_and_halves(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def loader(group_id: str, refresh: bool):
        return RECORDS

    good = {'c01': 'yes', 'c02': 'yes', 'c03': 'yes', 'c04': '20', 'c05': 'yes', 'c06': '10', 'c07': 'yes', 'c08': 'no'}
    bad = {'c01': 'no', 'c02': 'no', 'c03': 'no', 'c04': '5', 'c05': 'no', 'c06': '4', 'c07': 'no', 'c08': 'no'}
    t0 = datetime(2026, 11, 7, tzinfo=UTC)
    store = Store(tmp_path)
    await _seed(store, 'BASE', 6, good, t0)
    await _seed(store, 'DEV', 6, bad, t0)
    async with AsyncTestClient(create_app(tmp_path, loader, DEFAULTS)) as client:
        r = await client.get('/api/datasets/DEV/analytics', params={'baseline': 'BASE'})
        assert r.status_code == 200, r.text
        d = r.json()['drift']
        assert d['mode'] == 'groups' and d['baseline_label'] == 'BASE' and d['window_label'] == 'DEV'
        assert d['enough_data'] is False and d['min_n'] == 30  # n=6 per side is too small to conclude
        assert d['total']['verdict'] == 'drift' and d['total']['ks'] == 1.0
        assert d['total']['n_baseline'] == 6 and d['total']['n_window'] == 6
        assert {c['criterion_id'] for c in d['criteria']} == {f'c0{i}' for i in range(1, 8)}
        assert all(c['metric']['verdict'] == 'drift' for c in d['criteria'])

        # no baseline: halves of the group's own evaluations by time; identical halves -> stable
        d = (await client.get('/api/datasets/DEV/analytics')).json()['drift']
        assert d['mode'] == 'halves' and d['total']['n_baseline'] == 3 and d['total']['n_window'] == 3
        assert d['total']['psi'] == pytest.approx(0.0) and d['total']['verdict'] == 'stable' and d['total']['ks'] == 0.0


def _flip_to_drop(path: Path, out: Path, drop: float) -> None:
    """Candidate = baseline with verdicts broken on enough gold-agreeing cells to lose >= `drop` WA."""
    from bench.paired import dialog_cells, load_run, paired_diff
    from bench.prefill import load_gold

    gold = load_gold()
    rows = [json.loads(line) for line in (path / 'h200-gemma-per_criterion-k1.jsonl').read_text(encoding='utf-8').splitlines()]
    base_cells = dialog_cells(load_run(path), gold)
    target = sum(c.total for c in base_cells.values()) * drop
    lost = 0.0
    from bench.sets import checklist_for, load_records

    records = load_records()
    for row in rows:
        cid = row['conversation_id']
        if cid not in gold or lost >= target:
            continue
        for c in checklist_for(records[cid]).criteria:
            if c.kind == 'scored' and row['verdicts'].get(c.id) == gold[cid].get(c.id) and lost < target:
                row['verdicts'][c.id] = 'broken'
                lost += c.weight
    out.mkdir()
    (out / 'cand.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
    assert paired_diff(base_cells, dialog_cells(load_run(out), gold), iterations=50)['diff'] <= -drop


def test_regress_gate_fails_on_three_point_drop(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from scripts.regress_gate import main

    cand = tmp_path / 'cand'
    _flip_to_drop(BASELINE, cand, 0.035)
    assert main(['--baseline', str(BASELINE), '--candidate', str(cand)]) == 1
    assert 'FAIL' in capsys.readouterr().out
    assert main(['--baseline', str(BASELINE), '--candidate', str(cand), '--max-drop', '0.05']) == 0
    assert main(['--baseline', str(BASELINE), '--candidate', str(BASELINE)]) == 0


def test_arbitration_queue_math_and_order() -> None:
    from bench.arbitration_queue import build_queue, entropy, human_cells, scale_distance

    assert entropy(['a'] * 4) == 0 and entropy(['a', 'a', 'b', 'b']) == pytest.approx(1.0)
    assert scale_distance(['10', '15', '15', '20'], [0, 5, 10, 15, 20]) == pytest.approx(0.5)
    assert scale_distance(['yes', 'no'], None) == 1.0 and scale_distance(['na', '5'], [0, 5]) == 1.0
    queue = build_queue()
    assert queue == build_queue()  # deterministic
    assert [r['priority'] for r in queue] == sorted((r['priority'] for r in queue), reverse=True)
    skipped = human_cells()
    assert skipped and not any((r['conversation_id'], r['criterion_id']) in skipped for r in queue)
