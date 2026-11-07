from litestar import Controller, get
from litestar.params import FromPath, FromQuery

from server.analytics import group_analytics
from server.facts import dialog_facts
from server.triage import evaluation_attention
from server.models import ConversationSummary, DialogFacts, GroupAnalytics, Record
from server.routes import Svc
from server.transcripts import API


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
                    attention=await evaluation_attention(svc, latest, r) if latest else None,
                )
            )
        return out

    @get('/{group_id:str}/analytics')
    async def analytics(
        self, svc: Svc, group_id: FromPath[str], baseline: FromQuery[str | None] = None
    ) -> GroupAnalytics:
        return await group_analytics(svc, group_id, baseline)

    @get('/{group_id:str}/conversations/{cid:str}')
    async def conversation(
        self, svc: Svc, group_id: FromPath[str], cid: FromPath[str], source: FromQuery[str] = API
    ) -> Record:
        return await svc.record_for(group_id, cid, source)

    @get('/{group_id:str}/conversations/{cid:str}/facts')
    async def facts(
        self, svc: Svc, group_id: FromPath[str], cid: FromPath[str], source: FromQuery[str] = API
    ) -> DialogFacts:
        return dialog_facts(await svc.record_for(group_id, cid, source))
