import json
from pathlib import Path
from typing import Any

from litestar import Litestar, Response, Router, get, post, put
from litestar.static_files import create_static_files_router
from pydantic import BaseModel, ValidationError

from server.models import AppealCreate, BatchRequest, Checklist, DecisionCreate

EXAMPLES = Path(__file__).resolve().parent.parent / 'contracts' / 'examples'
WEB = Path(__file__).resolve().parent.parent / 'web'


def example(name: str) -> Any:
    return json.loads((EXAMPLES / f'{name}.json').read_text(encoding='utf-8'))


def validated(model: type[BaseModel], body: Any, name: str, status: int = 200) -> Response[Any]:
    try:
        model.model_validate(body)
    except ValidationError as e:
        details = [f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()]
        return Response({'error': 'некорректный запрос', 'details': details}, status_code=400)
    return Response(example(name), status_code=status)


@get('/datasets/{group_id:str}/conversations')
async def conversations(group_id: str, refresh: bool = False) -> Response[Any]:
    if group_id == 'FAIL':
        return Response(example('ApiError.dataset'), status_code=502)
    return Response(example('ConversationSummary.list'))


@get('/datasets/{group_id:str}/conversations/{cid:str}')
async def conversation(group_id: str, cid: str) -> Any:
    return example('Record.call' if cid.startswith('p4-') else 'Record.chat')


@get('/checklists')
async def checklists() -> Any:
    return example('ChecklistSummary.list')


@post('/checklists')
async def create_checklist(data: Any = None) -> Response[Any]:
    return validated(Checklist, data, 'Checklist')


@get('/checklists/{id:str}')
async def checklist(id: str, version: int | None = None) -> Any:
    return example('Checklist')


@put('/checklists/{id:str}')
async def update_checklist(id: str, data: Any = None) -> Response[Any]:
    return validated(Checklist, data, 'Checklist')


@post('/evaluations/batch')
async def batch(data: Any = None) -> Response[Any]:
    return validated(BatchRequest, data, 'Job.running')


@get('/jobs/{id:str}')
async def job(id: str) -> Any:
    return example('Job.finished')


@get('/conversations/{cid:str}/evaluations')
async def evaluations(cid: str) -> Any:
    return example('EvaluationSummary.list')


@get('/evaluations/{id:str}')
async def evaluation(id: str) -> Any:
    return example('EvaluationView')


@get('/evaluations/{id:str}/raw')
async def raw(id: str) -> Any:
    return example('RawCall.list')


@post('/appeals')
async def create_appeal(data: Any = None) -> Response[Any]:
    return validated(AppealCreate, data, 'Appeal')


@get('/appeals')
async def appeals(status: str | None = None) -> Any:
    return example('AppealQueueItem.list')


@post('/appeals/{id:str}/decision')
async def decide(id: str, data: Any = None) -> Response[Any]:
    return validated(DecisionCreate, data, 'DecisionResult')


api = [
    conversations, conversation, checklists, create_checklist, checklist, update_checklist, batch,
    job, evaluations, evaluation, raw, create_appeal, appeals, decide,
]
handlers: list[Any] = [Router(path='/api', route_handlers=api)]
if WEB.is_dir():
    handlers.append(create_static_files_router(path='/', directories=[WEB], html_mode=True))

app = Litestar(route_handlers=handlers)
