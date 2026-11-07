import os
from pathlib import Path
from typing import Any

from litestar import Litestar, Request, Response, Router
from litestar.config.cors import CORSConfig
from litestar.datastructures import State
from litestar.di import Provide
from litestar.exceptions import HTTPException, ValidationException
from litestar.static_files import create_static_files_router
from pydantic import ValidationError

from server.checklists import ChecklistError, ChecklistStore
from server.config import load_profiles
from server.dataset import DatasetError, load_dataset
from server.jobs import JobRunner, fallback_names
from server.models import ApiError
from server.routes import DatasetLoader, Services, provide_services
from server.routes.appeals import AppealsController
from server.routes.checklists import ChecklistsController
from server.routes.datasets import DatasetsController
from server.routes.evaluations import EvaluationsController
from server.routes.transcripts import TranscriptsController
from server.store import NotFound, Store
from server.transcripts import TranscriptStore

WEB = Path(__file__).resolve().parent.parent / 'web'
INVALID_CHECKLIST = 'Чек-лист невалиден'
INVALID_REQUEST = 'Некорректный запрос'


def _error(status: int, message: str, details: list[str] | None = None) -> Response[Any]:
    return Response(ApiError(error=message, details=details).model_dump(), status_code=status)


def _invalid(request: Request) -> str:
    return INVALID_CHECKLIST if request.url.path.startswith('/api/checklists') else INVALID_REQUEST


def _on_dataset(_: Request, exc: DatasetError) -> Response[Any]:
    return _error(502, f'Датасет недоступен: {exc}')


def _on_checklist(_: Request, exc: ChecklistError) -> Response[Any]:
    return _error(400, str(exc), exc.details)


def _on_not_found(_: Request, exc: NotFound) -> Response[Any]:
    return _error(404, str(exc.args[0]) if exc.args else 'не найдено')


def _on_pydantic(request: Request, exc: ValidationError) -> Response[Any]:
    details = [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()]
    return _error(400, _invalid(request), details)


def _on_value(_: Request, exc: ValueError) -> Response[Any]:
    return _error(400, str(exc))


def _on_request_validation(request: Request, exc: ValidationException) -> Response[Any]:
    details = []
    for e in exc.extra if isinstance(exc.extra, list) else []:
        if isinstance(e, dict):
            key, message = e.get('key'), e.get('message')
            details.append(f'{key}: {message}' if key else str(message))
        else:
            details.append(str(e))
    return _error(400, _invalid(request), details or [exc.detail])


def _on_http(_: Request, exc: HTTPException) -> Response[Any]:
    return _error(exc.status_code, exc.detail)


def create_app(
    store_root: Path = Path('data/store'),
    dataset_loader: DatasetLoader | None = None,
    seed_dir: Path = Path('data/checklists'),
    fallbacks: list[str] | None = None,
    calls_dir: Path = Path('data/calls'),
    quality_path: Path = Path('data/asr/quality.json'),
) -> Litestar:
    """The API under `/api`, `web/dist` at `/static` and `web/` (html mode) at `/`.

    `fallbacks` defaults to env `FALLBACK_PROFILE`, so live UI evaluations survive a dead model endpoint too.
    """
    store = Store(store_root)
    checklists = ChecklistStore(Path(store_root) / 'checklists')
    transcripts = TranscriptStore(Path(store_root) / 'transcripts', calls_dir, quality_path)
    profiles = load_profiles()
    if fallbacks is None:
        fallbacks = fallback_names(os.environ.get('FALLBACK_PROFILE'), profiles)
    services = Services(
        store=store,
        checklists=checklists,
        jobs=JobRunner(store, checklists, profiles, fallbacks, transcripts),
        profiles=profiles,
        dataset_loader=dataset_loader or load_dataset,
        transcripts=transcripts,
    )

    async def seed() -> None:
        await checklists.seed_defaults(seed_dir)

    api = Router(
        path='/api',
        route_handlers=[
            DatasetsController,
            ChecklistsController,
            EvaluationsController,
            AppealsController,
            TranscriptsController,
        ],
    )
    allowed_origins = [origin.strip() for origin in os.environ.get('CQA_ALLOWED_ORIGINS', '').split(',') if origin.strip()]
    return Litestar(
        cors_config=CORSConfig(
            allow_origins=allowed_origins,
            allow_methods=['GET', 'POST', 'PUT'],
            allow_headers=['Content-Type'],
        ) if allowed_origins else None,
        route_handlers=[
            api,
            create_static_files_router(path='/static', directories=[WEB / 'dist'], name='static'),
            create_static_files_router(path='/', directories=[WEB], html_mode=True, name='web'),
        ],
        dependencies={'svc': Provide(provide_services, sync_to_thread=False)},
        exception_handlers={
            DatasetError: _on_dataset,
            ChecklistError: _on_checklist,
            NotFound: _on_not_found,
            ValidationError: _on_pydantic,
            ValueError: _on_value,
            ValidationException: _on_request_validation,
            HTTPException: _on_http,
        },
        state=State({'services': services}),
        on_startup=[seed],
    )


app = create_app()
