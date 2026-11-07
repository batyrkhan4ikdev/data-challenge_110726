import os

from litestar import Controller, get, post
from litestar.params import FromPath, JSONBody

from server.models import BatchRequest, EvaluationSummary, EvaluationView, Job, RawCall
from server.routes import Svc


class EvaluationsController(Controller):
    path = '/'

    @post('/evaluations/batch', status_code=200)
    async def batch(self, svc: Svc, data: JSONBody[BatchRequest]) -> Job:
        records = {r.conversation_id: r for r in await svc.records(data.group_id)}
        return await svc.jobs.start(data, records)

    @get('/jobs/{job_id:str}')
    async def job(self, svc: Svc, job_id: FromPath[str]) -> Job:
        return svc.jobs.get(job_id)

    @get('/conversations/{cid:str}/evaluations')
    async def conversation_evaluations(self, svc: Svc, cid: FromPath[str]) -> list[EvaluationSummary]:
        return [await svc.summary(ev) for ev in await svc.store.list_for_conversation(cid)]

    @get('/evaluations/{evaluation_id:str}')
    async def evaluation(self, svc: Svc, evaluation_id: FromPath[str]) -> EvaluationView:
        ev = await svc.store.get_evaluation(evaluation_id)
        appeals = await svc.store.appeals_for(ev.id)
        return EvaluationView(
            evaluation=ev,
            checklist=await svc.recorded_checklist(ev),
            appeals=appeals,
            final=await svc.final(ev, appeals),
        )

    @get('/evaluations/{evaluation_id:str}/raw')
    async def raw(self, svc: Svc, evaluation_id: FromPath[str]) -> list[RawCall]:
        return await svc.store.get_raw(evaluation_id)

    @get('/profiles')
    async def profiles(self, svc: Svc) -> list[dict[str, str]]:
        """Model profiles; the env default (`LLM_PROFILE`, else `fake`) comes first."""
        default = os.environ.get('LLM_PROFILE') or 'fake'
        names = sorted(svc.profiles, key=lambda n: n != default)
        return [
            {'name': n, 'model': svc.profiles[n].model, 'provider': svc.profiles[n].provider} for n in names
        ]
