import asyncio
import json

import jsonschema
import pytest

from server.config import Profile
from server.llm import client as client_mod
from server.llm.client import LLMError, OpenAIClient, make_client
from server.llm.fake import FakeClient


class Resp:
    def __init__(self, status: int, payload: dict | None = None, text: str = ''):
        self.status_code = status
        self._payload = payload
        self.text = text or json.dumps(payload)

    def json(self) -> dict:
        return self._payload


class Session:
    def __init__(self, responses: list[Resp]):
        self.responses = list(responses)
        self.calls: list[dict] = []

    async def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append({'url': url, 'json': json, 'headers': headers, 'timeout': timeout})
        return self.responses.pop(0)


def ok(contents: list, prompt: int = 10, completion: int = 7) -> Resp:
    return Resp(200, {
        'choices': [
            {'message': {'content': c}, 'finish_reason': 'stop'} for c in contents
        ],
        'usage': {'prompt_tokens': prompt, 'completion_tokens': completion},
    })


@pytest.fixture
def profile(monkeypatch):
    monkeypatch.setenv('TEST_BASE', 'http://llm.test/v1/')
    return Profile(
        name='t', provider='openai', base_url_env='TEST_BASE', model='m',
        supports_n=True, extra_body={'reasoning_effort': 'low'},
    )


MSGS = [{'role': 'user', 'content': 'x'}]


async def test_supports_n_single_request(profile):
    s = Session([ok(['{}', '{}', '{}'], prompt=10, completion=7)])
    res = await OpenAIClient(profile, s).complete(MSGS, {}, 0.5, 3)
    assert len(res) == 3
    assert sum(c.prompt_tokens for c in res) == 10
    assert sum(c.completion_tokens for c in res) == 7
    assert len(s.calls) == 1
    assert s.calls[0]['url'] == 'http://llm.test/v1/chat/completions'
    assert s.calls[0]['json']['n'] == 3
    assert s.calls[0]['json']['reasoning_effort'] == 'low'


async def test_no_n_support_fires_n_requests(profile):
    p = profile.model_copy(update={'supports_n': False})
    s = Session([ok(['{}']) for _ in range(3)])
    res = await OpenAIClient(p, s).complete(MSGS, {}, 0.5, 3)
    assert len(res) == 3
    assert len(s.calls) == 3


async def test_retry_on_500(profile, monkeypatch):
    sleeps = []

    async def fake_sleep(d):
        sleeps.append(d)

    monkeypatch.setattr(asyncio, 'sleep', fake_sleep)
    s = Session([Resp(500, text='boom'), ok(['{}'])])
    res = await OpenAIClient(profile, s).complete(MSGS, {}, 0.0, 1)
    assert len(res) == 1
    assert len(s.calls) == 2
    assert sleeps == [1.0]


async def test_400_raises(profile):
    s = Session([Resp(400, text='bad request')])
    with pytest.raises(LLMError, match='400'):
        await OpenAIClient(profile, s).complete(MSGS, {}, 0.0, 1)
    assert len(s.calls) == 1


async def test_none_content(profile):
    s = Session([ok([None])])
    res = await OpenAIClient(profile, s).complete(MSGS, {}, 0.0, 1)
    assert res[0].text is None


def test_make_client_fake():
    p = Profile(name='f', provider='fake')
    assert isinstance(make_client(p), FakeClient)
    assert client_mod.LLMError is LLMError


def _crit(enum):
    return {
        'type': 'object',
        'properties': {
            'verdict': {'type': 'string', 'enum': enum},
            'explanation': {'type': 'string'},
            'evidence_idx': {'type': 'array', 'items': {'type': 'integer'}},
            'expected_range': {
                'type': ['array', 'null'], 'items': {'type': 'integer'},
            },
            'na_reason': {'type': ['string', 'null']},
        },
        'required': ['verdict', 'explanation', 'evidence_idx', 'expected_range', 'na_reason'],
    }


SCHEMA = {
    'type': 'object',
    'properties': {'c1': _crit(['yes', 'no', 'na']), 'c2': _crit(['0', '5'])},
    'required': ['c1', 'c2'],
}
USER = '[0] (00:00) client: hi\n[1] (00:02) operator: hello'


async def test_fake_client_valid_and_deterministic():
    msgs = [{'role': 'system', 'content': 's'}, {'role': 'user', 'content': USER}]
    a = await FakeClient().complete(msgs, SCHEMA, 0.0, 4)
    b = await FakeClient().complete(msgs, SCHEMA, 0.0, 4)
    assert [c.text for c in a] == [c.text for c in b]
    for c in a:
        obj = json.loads(c.text)
        jsonschema.validate(obj, SCHEMA)
        assert obj['c1']['evidence_idx'] == [1]
        assert c.finish_reason == 'stop'
