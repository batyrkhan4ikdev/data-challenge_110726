from pathlib import Path

from litestar.testing import AsyncTestClient

from server.app import create_app
from server.dataset import load_fixture
from server.facts import dialog_facts
from server.models import Record, Turn
from tests.test_api import DEFAULTS, RECORDS, fake_env, fixture_loader  # noqa: F401


def chat(*rows: tuple[str, str, str]) -> Record:
    return Record(
        conversation_id='c',
        channel='agent chat',
        language='RU',
        audio_url=None,
        transcript=[Turn(idx=i, timestamp=ts, speaker=sp, text=tx) for i, (ts, sp, tx) in enumerate(rows)],  # type: ignore[arg-type]
    )


def test_chat_facts() -> None:
    f = dialog_facts(
        chat(
            ('00:00', 'client', 'Привет, я [Имя скрыто]'),
            ('00:10', 'system', 'Customer identity verified.'),
            ('00:30', 'system', 'Эскалация на оператора.'),
            ('02:10', 'operator', 'Здравствуйте, [Имя скрыто]'),
            ('03:00', 'client', 'Вопрос'),
            ('06:30', 'operator', 'Ответ'),
        )
    )
    assert f.escalation_idx == 2
    assert f.first_response_s == 100 and f.first_response_idx == 3
    assert f.sla_ok is True and f.sla_s == 180
    assert f.max_wait_s == 210 and f.max_wait_idx == 5
    assert f.duration_s == 390
    assert [(m.token, m.count, m.first_idx) for m in f.masked] == [('[Имя скрыто]', 2, 0)]
    assert f.identity_verified_idx == 1
    assert [e.text for e in f.events] == ['Customer identity verified.', 'Эскалация на оператора.']
    assert f.turns == {'client': 2, 'system': 2, 'operator': 2}


def test_call_facts() -> None:
    rec = Record(
        conversation_id='k',
        channel='voice call',
        language='RU',
        audio_url=None,
        transcript=[
            Turn(idx=0, timestamp='2026-01-01T10:00:00Z', offset_s=0.0, speaker='client', text='а'),
            Turn(idx=1, timestamp='2026-01-01T10:04:00Z', offset_s=240.0, speaker='system', text='Агент присоединился к разговору с клиентом.'),
            Turn(idx=2, timestamp='2026-01-01T10:04:20Z', offset_s=260.0, speaker='operator', text='б'),
        ],
    )
    f = dialog_facts(rec)
    assert f.escalation_idx == 1 and f.first_response_s == 20 and f.sla_ok is True
    assert f.duration_s == 260


def test_no_operator() -> None:
    f = dialog_facts(chat(('00:00', 'client', 'a'), ('00:20', 'bot', 'b')))
    assert f.first_response_s is None and f.sla_ok is None and f.max_wait_s is None


def test_sla_violation_from_first_client() -> None:
    f = dialog_facts(chat(('00:00', 'client', 'a'), ('05:00', 'operator', 'b')))
    assert f.first_response_s == 300 and f.sla_ok is False


def test_real_dev_record() -> None:
    rec = next(r for r in load_fixture(Path(__file__).parent / 'fixtures' / 'dev.json') if r.conversation_id == 'p1-ru-020')
    assert dialog_facts(rec).first_response_s == 134


async def test_facts_endpoint(tmp_path: Path) -> None:
    async with AsyncTestClient(create_app(tmp_path, fixture_loader, DEFAULTS)) as c:
        r = await c.get('/api/datasets/DEV/conversations/p1-ru-020/facts')
        assert r.status_code == 200
        assert r.json()['first_response_s'] == 134 and r.json()['sla_ok'] is True
        assert (await c.get('/api/datasets/DEV/conversations/nope/facts')).status_code == 404


def test_bot_lane_handoff_and_reask() -> None:
    f = dialog_facts(
        chat(
            ('00:00', 'client', 'Не могу вывести деньги с брокерского счета'),
            ('00:05', 'bot', 'Передаю вас оператору'),
            ('00:20', 'system', 'Эскалация на оператора.'),
            ('00:40', 'operator', 'Здравствуйте! Чем могу помочь?'),
        )
    )
    lane = f.bot_lane
    assert lane is not None
    assert lane.bot_turns == 1
    assert [(t.idx, t.text) for t in lane.client_before_handoff] == [(0, 'Не могу вывести деньги с брокерского счета')]
    assert lane.handoff_idx == 2 and lane.handoff_offset_s == 20
    assert lane.reasked is True and lane.reasked_idx == 3


def test_bot_lane_no_reask_and_absent() -> None:
    f = dialog_facts(
        chat(
            ('00:00', 'client', 'Не могу вывести деньги с брокерского счета'),
            ('00:10', 'operator', 'Проверяю ваш перевод'),
        )
    )
    assert f.bot_lane is not None
    assert f.bot_lane.reasked is False and f.bot_lane.handoff_idx == 1
    assert dialog_facts(chat(('00:00', 'operator', 'Добрый день'))).bot_lane is None
