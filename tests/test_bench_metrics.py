import csv
import math

import pytest

from bench import metrics
from bench.prefill import COLUMNS, GoldError, load_gold
from bench.sets import checklist_for, load_records, smoke_ids


@pytest.fixture(scope="module")
def chat():
    records = load_records()
    return checklist_for(next(r for r in records.values() if r.channel == "agent chat"))


def _verdicts(chat, **overrides):
    base = {}
    for c in chat.criteria:
        base[c.id] = "yes" if c.answer_type == "yes_no" else str(max(s.value for s in c.steps))
    base["c08"] = "no"
    base.update(overrides)
    return {"d1": base}


def test_weighted_agreement(chat):
    gold = _verdicts(chat)
    assert metrics.weighted_agreement(gold, gold, chat) == 1.0
    pred = _verdicts(chat, c03="no")
    assert metrics.weighted_agreement(pred, gold, chat) == pytest.approx((100 - 20 + 1) / (100 + 1))


def test_cohen_kappa():
    assert metrics.cohen_kappa(["a", "b", "a", "b"], ["a", "b", "a", "b"]) == 1.0
    a = ["y"] * 20 + ["y"] * 5 + ["n"] * 10 + ["n"] * 15
    b = ["y"] * 20 + ["n"] * 5 + ["y"] * 10 + ["n"] * 15
    assert round(metrics.cohen_kappa(a, b), 3) == 0.4
    assert metrics.cohen_kappa(["a", "a"], ["a", "a"]) is None


def test_quadratic_weighted_kappa():
    levels = [0, 5, 10]
    assert metrics.quadratic_weighted_kappa([0, 5, 10], [0, 5, 10], levels) == 1.0
    assert metrics.quadratic_weighted_kappa([0, 10, 0, 10], [10, 0, 10, 0], levels) < 0


def test_total_mae_bias():
    pred = {"a": 80.0, "b": 50.0, "c": None, "d": 10.0}
    gold = {"a": 70.0, "b": 60.0, "c": 5.0, "d": None}
    assert metrics.total_mae(pred, gold) == 10.0
    assert metrics.total_bias(pred, gold) == 0.0
    assert metrics.total_bias({"a": 90.0}, {"a": 80.0}) == 10.0
    assert metrics.none_mismatches(pred, gold) == 2
    assert math.isnan(metrics.total_mae({"a": None}, {"a": 1.0}))


def test_na_confusion():
    pred = {"1": {"c02": "na"}, "2": {"c02": "na"}, "3": {"c02": "yes"}, "4": {"c02": "yes"}}
    gold = {"1": {"c02": "na"}, "2": {"c02": "yes"}, "3": {"c02": "na"}, "4": {"c02": "no"}}
    assert metrics.na_confusion(pred, gold, "c02") == {"tp": 1, "fp": 1, "fn": 1, "tn": 1}


def test_gross_pr():
    pred = {"1": {"c08": "no"}, "2": {"c08": "no"}}
    gold = {"1": {"c08": "yes"}, "2": {"c08": "no"}}
    r = metrics.gross_pr(pred, gold, "c08")
    assert r["precision"] is None and r["recall"] == 0.0 and r["support"] == 1
    pred = {"1": {"c08": "yes"}, "2": {"c08": "yes"}}
    r = metrics.gross_pr(pred, gold, "c08")
    assert r == {"precision": 0.5, "recall": 1.0, "support": 1}


def test_smoke_ids():
    ids = smoke_ids()
    assert ids == smoke_ids()
    assert len(ids) == len(set(ids)) == 12
    records = load_records()
    chats = [records[i] for i in ids if records[i].channel == "agent chat"]
    assert [sum(r.language == lang for r in chats) for lang in ("RU", "KZ", "EN")] == [5, 3, 2]
    assert sum(records[i].channel == "voice call" for i in ids) == 2


def test_load_gold_reports_invalid(tmp_path):
    cid = next(i for i, r in load_records().items() if r.channel == "agent chat")
    path = tmp_path / "labels.x.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        w.writerow([cid, "c01", "t", "yes|no", "yes", "1", "e", "yes", "1", ""])
        w.writerow([cid, "c02", "t", "yes|no|na", "yes", "1", "e", "maybe", "", ""])
    with pytest.raises(GoldError) as exc:
        load_gold(tmp_path)
    assert "labels.x.csv:3" in str(exc.value)
    assert len(exc.value.problems) == 1

    bad = path.read_text(encoding="utf-8-sig").replace("maybe", "")
    path.write_text(bad, encoding="utf-8-sig")
    assert load_gold(tmp_path) == {cid: {"c01": "yes"}}


def test_human_labels_override_consensus(tmp_path):
    cid = next(i for i, r in load_records().items() if r.channel == "agent chat")
    for name, verdict in (("labels.consensus.csv", "no"), ("labels.Batyrkhantzy111.csv", "yes"), ("labels.zz.csv", "")):
        with (tmp_path / name).open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(COLUMNS)
            w.writerow([cid, "c01", "t", "yes|no", "no", "1", "e", verdict, "", ""])
            w.writerow([cid, "c05", "t", "yes|no", "no", "1", "e", "no" if name == "labels.consensus.csv" else "", "", ""])
    # The human "yes" on c01 beats the LLM consensus "no"; c05 exists only in the consensus and stays.
    assert load_gold(tmp_path) == {cid: {"c01": "yes", "c05": "no"}}
