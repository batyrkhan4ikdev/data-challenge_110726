"""Issue #49: synthetic counterfactual generator is deterministic and only edits operator turns."""

import pytest

from bench import synthetic as syn
from bench.prefill import load_gold

pytestmark = pytest.mark.skipif(not syn.CACHE.exists(), reason="DEV cache missing")


@pytest.fixture(scope="module")
def built():
    parents = syn.load_parents()
    gold = load_gold()
    cases, records = syn.generate(parents, gold)
    return parents, gold, cases, records


def test_deterministic(built):
    parents, gold, cases, records = built
    cases2, records2 = syn.generate(parents, gold)
    assert cases == cases2
    assert {k: v.model_dump() for k, v in records.items()} == {k: v.model_dump() for k, v in records2.items()}


def test_every_transform_and_language_covered(built):
    _, _, cases, _ = built
    seen = {(c["transform"], c["language"]) for c in cases}
    assert {(t.name, lang) for t in syn.TRANSFORMS for lang in syn.LANGS} <= seen


def test_expected_labels_as_designed(built):
    parents, gold, cases, _ = built
    for c in cases:
        tf = syn.BY_NAME[c["transform"]]
        assert (c["target"], c["expected"]) == (tf.target, tf.expected)
        assert gold[c["parent_id"]][tf.target] == tf.parent_gold  # parent verdict is the opposite
        assert c["target"] not in c["untouched"] and len(c["untouched"]) == 7
        assert parents[c["parent_id"]].channel == "agent chat"


def test_only_operator_turns_touched(built):
    parents, _, cases, records = built
    for c in cases:
        parent, rec = parents[c["parent_id"]], records[c["case_id"]]
        assert [t.idx for t in rec.transcript] == list(range(len(rec.transcript)))
        allowed_removed_system = c["transform"] == "c03_drop_identification"
        # client turns: identical, in order
        pc = [t.text for t in parent.transcript if t.speaker == "client"]
        rc = [t.text for t in rec.transcript if t.speaker == "client"]
        assert pc == rc, c["case_id"]
        # bot turns identical
        assert [t.text for t in parent.transcript if t.speaker == "bot"] == [t.text for t in rec.transcript if t.speaker == "bot"]
        ps = [t.text for t in parent.transcript if t.speaker == "system"]
        rs = [t.text for t in rec.transcript if t.speaker == "system"]
        assert ps == rs or (allowed_removed_system and len(ps) == len(rs) + 1)


def test_transform_effects(built):
    parents, _, cases, records = built
    for c in cases:
        parent, rec = parents[c["parent_id"]], records[c["case_id"]]
        lang = c["language"]
        pops = [t.text for t in parent.transcript if t.speaker == "operator"]
        rops = [t.text for t in rec.transcript if t.speaker == "operator"]
        tf = c["transform"]
        if tf == "c01_drop_greeting":
            assert syn.GREET_WORD[lang].search(pops[0]) and not syn.GREET_WORD[lang].search(rops[0])
            assert len(rops) == len(pops) and rops[1:] == pops[1:]
        elif tf == "c07_strip_farewell":
            assert syn.FAREWELL[lang].search(pops[-1])
            assert not any(syn.FAREWELL[lang].search(x) for x in rops)
        elif tf == "c07_drop_closing_turn":
            assert rops == pops[:-1]
        elif tf == "c03_drop_identification":
            assert any(syn.IDENT_REQUEST[lang].search(x) for x in pops)
            assert not any(syn.IDENT_REQUEST[lang].search(x) for x in rops)
        else:
            assert len(rops) == len(pops) + 1 and rops[0] == pops[0] and rops[2:] == pops[1:]
            assert rops[1] in (syn.OFFSITE[lang], syn.INSULT[lang])
