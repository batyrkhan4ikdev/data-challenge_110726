from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from server.llm.client import Completion

_OPERATOR_RE = re.compile(r'^\[(\d+)\] .*operator:', re.MULTILINE)
_DEFAULTS: dict[str, Any] = {
    'string': '',
    'integer': 0,
    'number': 0,
    'boolean': False,
    'array': [],
    'object': {},
}


def _nullable(spec: dict) -> bool:
    t = spec.get('type')
    return t == 'null' or (isinstance(t, list) and 'null' in t)


def _default(spec: dict) -> Any:
    if _nullable(spec):
        return None
    t = spec.get('type')
    if isinstance(t, list):
        t = next((x for x in t if x != 'null'), None)
    return _DEFAULTS.get(t)


def _criterion(spec: dict, cid: str, user: str, i: int, k: int) -> dict:
    props = spec.get('properties', {})
    enum = props.get('verdict', {}).get('enum') or ['na']
    digest = hashlib.sha256((user + cid + str(i)).encode()).digest()
    verdict = enum[digest[0] % len(enum)]
    out: dict[str, Any] = {}
    for name, p in props.items():
        if name == 'verdict':
            out[name] = verdict
        elif name == 'explanation':
            out[name] = 'Тестовое обоснование'
        elif name == 'evidence_idx':
            out[name] = [k]
        elif name == 'expected_range':
            out[name] = [k, k] if verdict == 'no' else None
        elif name == 'na_reason':
            out[name] = 'Не применимо (тест)' if verdict == 'na' else None
        else:
            out[name] = _default(p)
    return out


class FakeClient:
    async def complete(
        self, messages: list[dict], schema: dict, temperature: float, n: int
    ) -> list[Completion]:
        user = next((m['content'] for m in reversed(messages) if m.get('role') == 'user'), '')
        match = _OPERATOR_RE.search(user)
        k = int(match.group(1)) if match else 0
        result = []
        for i in range(n):
            obj = {
                cid: _criterion(spec, cid, user, i, k)
                for cid, spec in schema.get('properties', {}).items()
            }
            result.append(
                Completion(
                    text=json.dumps(obj, ensure_ascii=False),
                    finish_reason='stop',
                    prompt_tokens=0,
                    completion_tokens=0,
                    seconds=0.0,
                )
            )
        return result
