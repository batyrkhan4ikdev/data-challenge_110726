import ssl
from typing import Any

import certifi
import niquests

# The Windows system store lacks some CF/Google chains on team machines, while certifi lacks the
# private CA behind aigw. Trust both. niquests ignores a session-level `verify`, so inject per request.
_TRUST = ssl.create_default_context()
_TRUST.load_verify_locations(certifi.where())


class _TrustSession(niquests.AsyncSession):
    async def request(self, method: str, url: str, *args: Any, **kwargs: Any) -> Any:
        if kwargs.get('verify') in (None, True):
            kwargs['verify'] = _TRUST
        return await super().request(method, url, *args, **kwargs)


def new_session() -> niquests.AsyncSession:
    return _TrustSession()
