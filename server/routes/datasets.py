from litestar import Controller, get
from litestar.params import FromPath, FromQuery

from server.analytics import group_analytics
from server.models import ConversationSummary, GroupAnalytics, Record
from server.routes import Svc
from server.store import NotFound


class DatasetsController(Controller):
    path = '/datasets'

    @get('/{group_id:str}/conversations')
    async def conversations(
        self, svc: Svc, group_id: FromPath[str], refresh: FromQuery[bool] = False
    ) -> list[ConversationSummary]:
        out = []
        for r in await svc.records(group_id, refresh):
            latest = await svc.store.latest_for_conversation(r.conversation_id, group_id)
            out.append(
                ConversationSummary(
                    conversation_id=r.conversation_id,
                    channel=r.channel,
                    language=r.language,
                    turns=len(r.transcript),
                    latest=await svc.summary(latest) if latest else None,
                )
            )
        return out

    @get('/{group_id:str}/analytics')
    async def analytics(self, svc: Svc, group_id: FromPath[str]) -> GroupAnalytics:
        return await group_analytics(svc, group_id)

    @get('/{group_id:str}/conversations/{cid:str}')
    async def conversation(self, svc: Svc, group_id: FromPath[str], cid: FromPath[str]) -> Record:
        for r in await svc.records(group_id):
            if r.conversation_id == cid:
                return r
        raise NotFound(f'диалог {cid} не найден в группе {group_id}')
