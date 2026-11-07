from pathlib import Path

from litestar import Controller, post
from litestar.params import FromPath, JSONBody

from server.recourse import Recourse, RecourseRequest, RecourseService
from server.routes import Svc

_SERVICES: dict[Path, RecourseService] = {}


def _service(root: Path) -> RecourseService:
    if root not in _SERVICES:
        _SERVICES[root] = RecourseService(root)
    return _SERVICES[root]


class RecourseController(Controller):
    path = '/evaluations'

    @post('/{evaluation_id:str}/recourse', status_code=200)
    async def recourse(
        self, svc: Svc, evaluation_id: FromPath[str], data: JSONBody[RecourseRequest]
    ) -> Recourse:
        """Coaching only: what the operator should have said, re-judged on this one criterion.
        Never stored as an evaluation; totals and appeals are untouched."""
        ev = await svc.store.get_evaluation(evaluation_id)
        checklist = await svc.recorded_checklist(ev)
        profile = svc.profiles.get(ev.profile)
        if profile is None:
            raise ValueError(f'профиль {ev.profile} не настроен')
        record = await svc.record_for(ev.group_id, ev.conversation_id, ev.transcript_source)
        return await _service(svc.store.root).run(ev, checklist, record, data.criterion_id, profile)
