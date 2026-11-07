from pathlib import Path

import pytest
from litestar.testing import AsyncTestClient

from server.app import create_app

ROOT = Path(__file__).resolve().parent.parent
ORIGIN = 'http://127.0.0.1:8807'


@pytest.fixture(autouse=True)
def fake_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('LLM_PROFILE', 'fake')
    monkeypatch.delenv('FALLBACK_PROFILE', raising=False)


@pytest.mark.parametrize('method', ['GET', 'POST', 'PUT'])
async def test_allowed_preflight(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, method: str) -> None:
    monkeypatch.setenv('CQA_ALLOWED_ORIGINS', f' https://example.crm.dynamics.com, {ORIGIN}, ')
    async with AsyncTestClient(create_app(tmp_path, seed_dir=ROOT / 'data/checklists')) as client:
        response = await client.options('/api/checklists', headers={
            'Origin': ORIGIN,
            'Access-Control-Request-Method': method,
            'Access-Control-Request-Headers': 'content-type',
        })
        assert response.status_code == 204
        assert response.headers['access-control-allow-origin'] == ORIGIN
        assert method in response.headers['access-control-allow-methods']
        assert 'content-type' in response.headers['access-control-allow-headers'].lower()
        response = await client.get('/api/checklists', headers={'Origin': ORIGIN})
        assert response.status_code == 200
        assert response.headers['access-control-allow-origin'] == ORIGIN


async def test_foreign_preflight_not_allowed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('CQA_ALLOWED_ORIGINS', ORIGIN)
    async with AsyncTestClient(create_app(tmp_path, seed_dir=ROOT / 'data/checklists')) as client:
        response = await client.options('/api/checklists', headers={
            'Origin': 'http://127.0.0.1:8808',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'content-type',
        })
        assert 'access-control-allow-origin' not in response.headers


@pytest.mark.parametrize('origins', ['', ' ,  , ', None])
async def test_empty_origins_disables_cors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, origins: str | None) -> None:
    if origins is None:
        monkeypatch.delenv('CQA_ALLOWED_ORIGINS', raising=False)
    else:
        monkeypatch.setenv('CQA_ALLOWED_ORIGINS', origins)
    app = create_app(tmp_path, seed_dir=ROOT / 'data/checklists')
    assert app.cors_config is None
    async with AsyncTestClient(app) as client:
        for method in ['GET', 'OPTIONS']:
            response = await client.request(method, '/api/checklists', headers={
                'Origin': ORIGIN,
                'Access-Control-Request-Method': 'GET',
            })
            assert not any(name.startswith('access-control-') for name in response.headers)
