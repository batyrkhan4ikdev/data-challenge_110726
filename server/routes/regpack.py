import json
from pathlib import Path

from litestar import Controller, Response, get
from litestar.params import FromPath, FromQuery

from server.regpack import build_regpack
from server.routes import Svc

RELIABILITY = Path(__file__).resolve().parents[2] / 'data' / 'criterion_reliability.json'


class RegPackController(Controller):
    path = '/'

    @get('/conversations/{cid:str}/regpack')
    async def regpack(
        self,
        svc: Svc,
        cid: FromPath[str],
        group_id: FromQuery[str],
        evaluation_id: FromQuery[str | None] = None,
    ) -> Response[bytes]:
        data, name, ok = await build_regpack(svc, cid, group_id, evaluation_id)
        return Response(
            data,
            media_type='application/zip',
            headers={
                'Content-Disposition': f'attachment; filename="{name}"',
                'X-Regpack-Selfcheck': 'ok' if ok else 'fail',
            },
        )

    @get('/criterion-reliability')
    async def criterion_reliability(self) -> dict:
        """Измеренное согласие судьи с разметкой на DEV по критериям; пусто, если файл не сгенерирован."""
        if not RELIABILITY.is_file():
            return {'source': None, 'criteria': {}}
        return json.loads(RELIABILITY.read_text(encoding='utf-8'))
