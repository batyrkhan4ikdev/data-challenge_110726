from typing import Any

import certifi
import niquests


class _CertifiSession(niquests.AsyncSession):
    """Verifies against the certifi bundle: the Windows system trust store fails on team machines,
    and niquests ignores a session-level `verify` attribute, so it is injected per request."""

    async def request(self, method: str, url: str, *args: Any, **kwargs: Any) -> Any:
        if kwargs.get('verify') in (None, True):
            kwargs['verify'] = certifi.where()
        return await super().request(method, url, *args, **kwargs)


def new_session() -> niquests.AsyncSession:
    return _CertifiSession()
