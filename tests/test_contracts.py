import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from server.config import load_profiles
from server.models import ALL_MODELS, Checklist, Evaluation, EvaluationView, Score

EXAMPLES = Path(__file__).resolve().parent.parent / 'contracts' / 'examples'
MODELS = {m.__name__: m for m in ALL_MODELS}


def load(name: str):
    return json.loads((EXAMPLES / name).read_text(encoding='utf-8'))


@pytest.mark.parametrize('path', sorted(EXAMPLES.glob('*.json')), ids=lambda p: p.name)
def test_examples_validate(path: Path) -> None:
    parts = path.stem.split('.')
    model = MODELS[parts[0]]
    target = list[model] if 'list' in parts[1:] else model
    TypeAdapter(target).validate_python(load(path.name))


def pct(points: Decimal, weight: Decimal) -> float | None:
    if weight == 0:
        return None
    return float((points / weight * 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def assert_consistent(score: Score, checklist: Checklist) -> None:
    section_of = {c.id: c.section_id for c in checklist.criteria}
    applicable = [i for i in score.items if i.applicable]
    pts = sum((Decimal(str(i.points)) for i in applicable), Decimal(0))
    weight = sum((Decimal(str(i.max_points)) for i in applicable), Decimal(0))
    assert score.total == pct(pts, weight)
    assert score.applicable_weight == float(weight)
    for s in score.sections:
        own = [i for i in applicable if section_of[i.criterion_id] == s.section_id]
        s_pts = sum((Decimal(str(i.points)) for i in own), Decimal(0))
        s_w = sum((Decimal(str(i.max_points)) for i in own), Decimal(0))
        assert s.total == pct(s_pts, s_w), s.section_id


def test_example_scores_consistent() -> None:
    view = EvaluationView.model_validate(load('EvaluationView.json'))
    evaluation = Evaluation.model_validate(load('Evaluation.json'))
    assert_consistent(evaluation.score, view.checklist)
    assert_consistent(view.final.score, view.checklist)
    assert evaluation.score.total == 81.88
    assert view.final.score.total == 87.5


def test_profiles_load() -> None:
    profiles = load_profiles()
    assert {'fake', 'h200-gemma', 'h200-gptoss', 'h200-kz'} <= profiles.keys()
    assert profiles['h200-gptoss'].extra_body == {'reasoning_effort': 'low'}


