"""RegPack: self-contained «дело» по оценке — ZIP, который можно перепроверить без сервера."""

import hashlib
import io
import json
import zipfile
from datetime import UTC, datetime
from typing import Any

from server.models import Appeal, Checklist, Evaluation, FinalResult
from server.routes import Services
from server.scoring import final_result

FILES = ('record.json', 'evaluation.json', 'checklist.json', 'appeals.json', 'final.json', 'calls.json')

README = """# RegPack: дело по оценке {evaluation_id}

Диалог: {conversation_id} (группа {group_id}). Чек-лист: {checklist_id} v{checklist_version}.

| Файл | Содержимое |
|---|---|
| record.json | транскрипт, по которому считалась оценка (источник: {source}); ссылка на аудио удалена |
| evaluation.json | вердикты судьи по критериям, пояснения, подтверждения, расход токенов |
| checklist.json | точная версия чек-листа, использованная при оценке |
| appeals.json | апелляции и решения проверяющих |
| final.json | итоговый результат после решений по апелляциям |
| calls.json | сырые вызовы модели (промпты и ответы) |
| manifest.json | SHA-256 файлов и самопроверка (selfcheck) |

Проверка: итог пересчитывается из checklist.json + evaluation.json + appeals.json
функцией `server.scoring.final_result` и должен совпасть с final.json.
Без сервера: `python scripts/verify_regpack.py <файл.zip>` (код выхода 1 при расхождении).
"""


def _dump(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str).encode('utf-8')


def selfcheck(checklist: dict, evaluation: dict, appeals: list[dict], stored_final: dict) -> dict:
    """Recompute from the packaged pieces: the judge's own total (no appeals) against `evaluation.json`, and the final
    total (with decisions) against `final.json`. Hashes prove the files were not edited after export, not who made them."""
    cl = Checklist.model_validate(checklist)
    ev = Evaluation.model_validate(evaluation)
    recomputed = final_result(cl, ev, [Appeal.model_validate(a) for a in appeals])
    raw = final_result(cl, ev, [])
    stored = FinalResult.model_validate(stored_final)
    rt, st = recomputed.score.total, stored.score.total
    same_verdicts = [(i.criterion_id, i.final_verdict) for i in recomputed.items] == [
        (i.criterion_id, i.final_verdict) for i in stored.items
    ]
    raw_ok = raw.score.total == ev.score.total
    return {
        'recomputed_total': rt, 'stored_total': st,
        'judge_total': ev.score.total, 'judge_total_recomputed': raw.score.total,
        'ok': rt == st and same_verdicts and raw_ok,
    }


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def build_regpack(
    svc: Services, cid: str, group_id: str, evaluation_id: str | None
) -> tuple[bytes, str, bool]:
    """ZIP bytes, suggested file name and selfcheck verdict for the conversation's evaluation (latest by default)."""
    if evaluation_id is None:
        evs = await svc.store.list_for_conversation(cid)
        if not evs:
            raise ValueError(f'у диалога {cid} нет оценок')
        ev = max(evs, key=lambda e: e.created_at)
    else:
        ev = await svc.store.get_evaluation(evaluation_id)
        if ev.conversation_id != cid:
            raise ValueError(f'оценка {ev.id} относится к другому диалогу ({ev.conversation_id})')
    record = await svc.record_for(group_id, cid, ev.transcript_source)
    checklist = await svc.recorded_checklist(ev)
    appeals = await svc.store.appeals_for(ev.id)
    final = final_result(checklist, ev, appeals)
    calls = await svc.store.get_raw(ev.id)

    parts: dict[str, Any] = {
        'record.json': record.model_copy(update={'audio_url': None}).model_dump(mode='json'),
        'evaluation.json': ev.model_dump(mode='json'),
        'checklist.json': checklist.model_dump(mode='json'),
        'appeals.json': [a.model_dump(mode='json') for a in appeals],
        'final.json': final.model_dump(mode='json'),
        'calls.json': [c.model_dump(mode='json') for c in calls],
    }
    check = selfcheck(parts['checklist.json'], parts['evaluation.json'], parts['appeals.json'], parts['final.json'])
    blobs = {name: _dump(obj) for name, obj in parts.items()}
    manifest = {
        'evaluation_id': ev.id,
        'conversation_id': cid,
        'group_id': ev.group_id,
        'checklist': {'id': ev.checklist_id, 'version': ev.checklist_version},
        'transcript_source': ev.transcript_source,
        'exported_at': datetime.now(UTC).isoformat(),
        'sha256': {name: _sha(b) for name, b in blobs.items()},
        'selfcheck': check,
    }
    readme = README.format(
        evaluation_id=ev.id,
        conversation_id=cid,
        group_id=ev.group_id,
        checklist_id=ev.checklist_id,
        checklist_version=ev.checklist_version,
        source=ev.transcript_source,
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('README.md', readme)
        z.writestr('manifest.json', _dump(manifest))
        for name, b in blobs.items():
            z.writestr(name, b)
    return buf.getvalue(), f'regpack-{cid}-{ev.id}.zip', check['ok']


def verify_regpack(data: bytes) -> dict:
    """Verify a RegPack from the ZIP alone: file hashes and the recomputed total. Returns {ok, problems, selfcheck}."""
    problems: list[str] = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = set(z.namelist())
        missing = [n for n in (*FILES, 'manifest.json') if n not in names]
        if missing:
            return {'ok': False, 'problems': [f'нет файлов: {", ".join(missing)}'], 'selfcheck': None}
        raw = {n: z.read(n) for n in (*FILES, 'manifest.json')}
    manifest = json.loads(raw['manifest.json'])
    for name in FILES:
        if manifest.get('sha256', {}).get(name) != _sha(raw[name]):
            problems.append(f'{name}: хеш не совпадает с manifest.json')
    docs = {n: json.loads(raw[n]) for n in FILES}
    check = selfcheck(docs['checklist.json'], docs['evaluation.json'], docs['appeals.json'], docs['final.json'])
    if not check['ok']:
        problems.append(f'итог не сходится: пересчитано {check["recomputed_total"]}, в деле {check["stored_total"]}')
    return {'ok': not problems, 'problems': problems, 'selfcheck': check}
