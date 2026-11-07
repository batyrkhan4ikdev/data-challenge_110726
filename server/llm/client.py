from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Protocol

import niquests
from pydantic import BaseModel

from server.config import Profile
from server.http import new_session

TIMEOUT_S = 180
RETRY_STATUSES = {429}
ATTEMPTS = 3  # the venue network drops connections; one retry was not enough in practice
PROMPT_JSON = (
    'Ответь ТОЛЬКО одним JSON-объектом без markdown и без текста вокруг, строго по этой JSON Schema '
    '(все поля обязательны, порядок полей как в схеме):\n{schema}'
)


class LLMError(Exception):
    pass


class Completion(BaseModel):
    text: str | None
    finish_reason: str | None
    prompt_tokens: int
    completion_tokens: int
    seconds: float


class LLMClient(Protocol):
    async def complete(
        self, messages: list[dict], schema: dict, temperature: float, n: int
    ) -> list[Completion]: ...


def _split(total: int, parts: int) -> list[int]:
    if parts <= 0:
        return []
    base, rem = divmod(total, parts)
    return [base + rem] + [base] * (parts - 1)


class OpenAIClient:
    def __init__(self, profile: Profile, session: Any = None) -> None:
        self.profile = profile
        self._session = session
        self._sem = asyncio.Semaphore(profile.max_concurrency)

    def _get_session(self) -> Any:
        if self._session is None:
            self._session = new_session()
        return self._session

    def _body(self, messages: list[dict], schema: dict, temperature: float, n: int) -> dict:
        p = self.profile
        body: dict = {
            'model': p.model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': p.max_tokens,
        }
        if p.structured == 'json_schema':
            body['response_format'] = {
                'type': 'json_schema',
                'json_schema': {'name': 'cqa', 'schema': schema, 'strict': True},
            }
        elif p.structured == 'json_object':
            body['response_format'] = {'type': 'json_object'}
        else:
            # Gateways that drop response_format (aigw for Claude/GPT): the schema goes into the prompt instead.
            body['messages'] = [*messages, {'role': 'user', 'content': PROMPT_JSON.format(schema=json.dumps(schema, ensure_ascii=False))}]
        if n != 1 or p.supports_n:
            body['n'] = n
        body.update(p.extra_body)
        return body

    async def _post(self, body: dict) -> tuple[dict, float]:
        url = f'{self.profile.base_url()}/chat/completions'
        headers = {'User-Agent': 'Mozilla/5.0 (cqa)', 'Content-Type': 'application/json'}
        key = self.profile.api_key()
        if key:
            headers['Authorization'] = f'Bearer {key}'
        async with self._sem:
            start = time.perf_counter()
            last = ''
            for attempt in range(ATTEMPTS):
                try:
                    resp = await self._get_session().post(
                        url, json=body, headers=headers, timeout=TIMEOUT_S
                    )
                except Exception as exc:
                    last = f'connection error: {exc!r}'
                else:
                    status = resp.status_code
                    if status == 200:
                        return resp.json(), time.perf_counter() - start
                    last = f'HTTP {status}: {(resp.text or "")[:300]}'
                    if not (status in RETRY_STATUSES or status >= 500):
                        raise LLMError(last)
                if attempt < ATTEMPTS - 1:
                    await asyncio.sleep(1.0 * (attempt + 1))
            raise LLMError(last)

    @staticmethod
    def _parse(data: dict, seconds: float) -> list[Completion]:
        choices = data.get('choices') or []
        usage = data.get('usage') or {}
        pt = _split(int(usage.get('prompt_tokens') or 0), len(choices))
        ct = _split(int(usage.get('completion_tokens') or 0), len(choices))
        return [
            Completion(
                text=(c.get('message') or {}).get('content'),
                finish_reason=c.get('finish_reason'),
                prompt_tokens=pt[i],
                completion_tokens=ct[i],
                seconds=seconds,
            )
            for i, c in enumerate(choices)
        ]

    async def complete(
        self, messages: list[dict], schema: dict, temperature: float, n: int
    ) -> list[Completion]:
        if self.profile.supports_n:
            data, secs = await self._post(self._body(messages, schema, temperature, n))
            return self._parse(data, secs)
        results = await asyncio.gather(
            *(self._post(self._body(messages, schema, temperature, 1)) for _ in range(n))
        )
        return [c for data, secs in results for c in self._parse(data, secs)]


def make_client(profile: Profile) -> LLMClient:
    if profile.provider == 'fake':
        from server.llm.fake import FakeClient

        return FakeClient()
    return OpenAIClient(profile, session=None)
