from litestar import Controller, get, post, put
from litestar.params import FromPath, FromQuery, JSONBody

from server.models import Checklist, ChecklistSummary
from server.routes import Svc


class ChecklistsController(Controller):
    path = '/checklists'

    @get('/')
    async def list_checklists(self, svc: Svc) -> list[ChecklistSummary]:
        return await svc.checklists.list()

    @post('/', status_code=200)
    async def create_checklist(self, svc: Svc, data: JSONBody[Checklist]) -> Checklist:
        return await svc.checklists.create(data)

    @get('/{checklist_id:str}')
    async def get_checklist(
        self, svc: Svc, checklist_id: FromPath[str], version: FromQuery[int | None] = None
    ) -> Checklist:
        return await svc.checklists.get(checklist_id, version)

    @put('/{checklist_id:str}')
    async def update_checklist(self, svc: Svc, checklist_id: FromPath[str], data: JSONBody[Checklist]) -> Checklist:
        if data.id != checklist_id:
            raise ValueError(f'id в теле ({data.id}) не совпадает с id в пути ({checklist_id})')
        return await svc.checklists.save(data)
