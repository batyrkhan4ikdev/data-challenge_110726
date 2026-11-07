from datetime import UTC, datetime
from uuid import uuid4

from litestar import Controller, get, post
from litestar.params import FromPath, FromQuery, JSONBody

from server.models import (
    Appeal,
    AppealCreate,
    AppealQueueItem,
    Criterion,
    Decision,
    DecisionCreate,
    DecisionResult,
    Evaluation,
)
from server.routes import Services, Svc
from server.scoring import allowed_verdicts

STATUSES = ('open', 'resolved')


async def _criterion(svc: Services, ev: Evaluation, criterion_id: str) -> Criterion:
    checklist = await svc.recorded_checklist(ev)
    for c in checklist.criteria:
        if c.id == criterion_id:
            return c
    raise ValueError(
        f'критерий {criterion_id} отсутствует в чек-листе {checklist.id} версии {checklist.version}'
    )


class AppealsController(Controller):
    path = '/appeals'

    @post('/', status_code=200)
    async def create_appeal(self, svc: Svc, data: JSONBody[AppealCreate]) -> Appeal:
        if not data.comment.strip():
            raise ValueError('Комментарий к апелляции обязателен')
        ev = await svc.store.get_evaluation(data.evaluation_id)
        await _criterion(svc, ev, data.criterion_id)
        appeal = Appeal(
            id=f'ap-{uuid4().hex[:12]}',
            evaluation_id=ev.id,
            criterion_id=data.criterion_id,
            comment=data.comment.strip(),
            created_at=datetime.now(UTC),
            status='open',
            decision=None,
        )
        await svc.store.save_appeal(appeal)
        return appeal

    @get('/')
    async def list_appeals(self, svc: Svc, status: FromQuery[str | None] = None) -> list[AppealQueueItem]:
        if status is not None and status not in STATUSES:
            raise ValueError(f'неизвестный статус {status!r}; допустимые значения: {", ".join(STATUSES)}')
        out = []
        for a in await svc.store.list_appeals(status):
            ev = await svc.store.get_evaluation(a.evaluation_id)
            item = next(i for i in ev.items if i.criterion_id == a.criterion_id)
            out.append(
                AppealQueueItem(
                    appeal=a,
                    evaluation_id=ev.id,
                    conversation_id=ev.conversation_id,
                    item=item,
                    criterion=await _criterion(svc, ev, a.criterion_id),
                )
            )
        return out

    @post('/{appeal_id:str}/decision', status_code=200)
    async def decide(self, svc: Svc, appeal_id: FromPath[str], data: JSONBody[DecisionCreate]) -> DecisionResult:
        appeal = await svc.store.get_appeal(appeal_id)
        if appeal.status == 'resolved':
            raise ValueError('Апелляция уже рассмотрена')
        if not data.reason.strip():
            raise ValueError('Причина решения обязательна')
        ev = await svc.store.get_evaluation(appeal.evaluation_id)
        new_verdict = None
        if data.action == 'change':
            allowed = allowed_verdicts(await _criterion(svc, ev, appeal.criterion_id))
            values = ', '.join(allowed)
            if not data.new_verdict:
                raise ValueError(f'Для изменения укажите новый вердикт. Допустимые значения: {values}')
            if data.new_verdict not in allowed:
                raise ValueError(
                    f'Недопустимый вердикт «{data.new_verdict}» для {appeal.criterion_id}. '
                    f'Допустимые значения: {values}'
                )
            new_verdict = data.new_verdict
        resolved = appeal.model_copy(
            update={
                'status': 'resolved',
                'decision': Decision(
                    action=data.action,
                    new_verdict=new_verdict,
                    reason=data.reason.strip(),
                    decided_at=datetime.now(UTC),
                ),
            }
        )
        await svc.store.save_appeal(resolved)
        return DecisionResult(appeal=resolved, final=await svc.final(ev))
