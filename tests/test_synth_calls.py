import array
import math
import random

from bench import synth_calls as sc


def test_mulaw_roundtrip_error_is_bounded():
    xs = array.array('h', range(-32000, 32000, 97))
    ys = sc.mulaw_roundtrip(xs)
    for x, y in zip(xs, ys):
        assert abs(x - y) <= max(40, abs(x) * 0.04)  # logarithmic quantiser: relative error of a few percent
    assert sc.mulaw_decode(sc.mulaw_encode(0)) == 0
    assert sc.mulaw_encode(1000) != sc.mulaw_encode(-1000)


def test_add_noise_hits_target_snr_and_is_seeded():
    sig = array.array('h', (round(8000 * math.sin(i / 7)) for i in range(40000)))
    noisy = sc.add_noise(sig, 20, random.Random(1))
    noise = [a - b for a, b in zip(noisy, sig)]
    snr = 20 * math.log10(sc.rms(sig) / sc.rms(noise))
    assert abs(snr - 20) < 0.5
    assert list(noisy) == list(sc.add_noise(sig, 20, random.Random(1)))


def test_chain_params_are_seeded_and_in_range():
    assert sc.pauses_for('x', 6) == sc.pauses_for('x', 6)
    assert sc.pauses_for('x', 6) != sc.pauses_for('y', 6)
    assert all(0.25 <= p <= 0.70 for p in sc.pauses_for('x', 50))
    assert len(sc.pauses_for('x', 1)) == 0
    snrs = {sc.snr_for(f'd{i}') for i in range(100)}
    assert snrs <= set(range(15, 26)) and len(snrs) > 5
    chain = sc.degrade_chain('x')
    assert chain['bandpass_hz'] == (300, 3400) and chain['sample_rate_hz'] == 8000
    assert chain['mp3'] == {'sample_rate_hz': 16000, 'channels': 1, 'bitrate': '48k'}


def test_turn_boundaries():
    b = sc.turn_boundaries([2.0, 1.5, 3.0], [0.5, 0.25])
    assert b == [(0.0, 2.0), (2.5, 4.0), (4.25, 7.25)]
    assert sc.turn_boundaries([1.0], []) == [(0.0, 1.0)]


def test_build_master_matches_boundaries():
    clips = [array.array('h', [1] * 2400), array.array('h', [2] * 4800)]
    turns = [{'speaker': 'operator', 'text': 'a'}, {'speaker': 'client', 'text': 'b'}]
    master, timings = sc.build_master('x', turns, clips)
    pause = sc.pauses_for('x', 2)[0]
    assert timings[0] == {'idx': 0, 'speaker': 'operator', 'start': 0.0, 'end': 0.1}
    assert abs(timings[1]['start'] - (0.1 + pause)) < 1e-6
    assert abs(len(master) / sc.TTS_RATE - timings[1]['end']) < 1e-3


def test_attribution_uses_best_label_mapping():
    turns = [{'speaker': 'operator', 'text': 'раз два три'}, {'speaker': 'client', 'text': 'четыре пять шесть'}]
    tm = [{'start': 0.0, 'end': 3.0}, {'start': 4.0, 'end': 7.0}]
    ref = sc.reference_words(turns, tm)
    assert len(ref) == 6
    swapped = [{'start': 0, 'end': 3, 'speaker': 'B', 'text': ''}, {'start': 4, 'end': 7, 'speaker': 'A', 'text': ''}]
    assert sc.attribution(ref, swapped) == 1.0  # label names do not matter
    one = [{'start': 0, 'end': 7, 'speaker': 'A', 'text': ''}]
    assert sc.attribution(ref, one) == 0.5
    assert sc.attribution(ref, [{'start': 0, 'end': 3, 'speaker': 'A', 'text': ''}]) == 0.5  # uncovered client words are wrong
    assert sc.attribution(ref, []) is None


def test_loops_and_pooled_error():
    assert sc.count_loops('да да да да да да нет') == 1
    assert sc.count_loops('да да да да нет да да да да') == 0
    assert sc.count_loops('а ' * 5 + 'б ' + 'в ' * 6) == 2
    assert sc.pooled_error([('abcd', 'abcd'), ('abcd', 'abxx')], 'char') == 2 / 8
    assert sc.pooled_error([('a b', 'a'), ('c d', 'c d')], 'word') == 1 / 4


def test_verdict_matching_and_comparison():
    assert sc.verdict_matches('Да', 'yes') is True
    assert sc.verdict_matches('Нет', 'yes') is False
    assert sc.verdict_matches('any', 'yes') is None
    assert sc.verdict_matches('high', '20') is True and sc.verdict_matches('low', '15') is False and sc.verdict_matches('high', '10', 10.0) is True
    ref = {'verdicts': {'c01': 'yes', 'c04': '20'}, 'total': 90.0}
    other = {'verdicts': {'c01': 'no', 'c04': '20'}, 'total': 80.0}
    assert sc.compare_judgements(ref, other) == (1, 2, 10.0)


def test_matrix_and_validation():
    specs = sc.build_specs()
    counts = {lang: sum(s['language'] == lang for s in specs) for lang in ('RU', 'KZ', 'EN')}
    assert counts == {'RU': 24, 'KZ': 8, 'EN': 8}
    assert len({s['id'] for s in specs}) == 40
    spec = next(s for s in specs if s['language'] == 'EN' and s['profile'] == 'clean' and not s['ivr']) if any(
        s['language'] == 'EN' and s['profile'] == 'clean' and not s['ivr'] for s in specs) else None
    ok = [{'speaker': 'operator' if i % 2 == 0 else 'client', 'text': 'Hello this is Anna from Freedom Broker how can I help you with that today' if i == 0 else 'okay that works well for me please go on and explain it' } for i in range(12)]
    if spec:
        assert sc.validate_script(spec, ok) == []
        assert 'digits' in sc.validate_script(spec, [dict(ok[0], text=ok[0]['text'] + ' 5'), *ok[1:]])
        assert 'not English' in sc.validate_script(spec, [dict(t, text='Здравствуйте, это Анна из Фридом Брокер ' * 2) for t in ok])
    ablation = sc.ablation_ids([{'id': f'syn-{lang}-{i}', 'language': lang} for lang in ('RU', 'KZ', 'EN') for i in range(8)])
    assert len(ablation) == 8


def test_pitch_ratio_targets_role_f0_within_limits():
    assert abs(sc.pitch_ratio(230.0, 115.0) - 0.5) < 1e-9
    assert abs(sc.pitch_ratio(150.0, 180.0) - 1.2) < 1e-9
    assert sc.pitch_ratio(50.0, 215.0) == 2.0 and sc.pitch_ratio(400.0, 115.0) == 0.5
    assert sc.pitch_ratio(None, 215.0) == 1.0
