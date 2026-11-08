"""RegPack: self-contained «дело» по оценке — ZIP, который можно перепроверить без сервера."""

import asyncio
import hashlib
import io
import json
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from server.models import Appeal, Checklist, Evaluation, FinalResult, Record
from server.routes import Services
from server.scoring import final_result
from server.store import NotFound
from server.uploads import UPLOADS

FILES = ('record.json', 'evaluation.json', 'checklist.json', 'appeals.json', 'final.json', 'calls.json')
AUDIO_DIR = Path(__file__).resolve().parent.parent / 'data' / 'audio'
MAX_AUDIO_BYTES = 50 * 1024 * 1024
REMOTE_TIMEOUT_S = 60.0
_SAFE_ID = re.compile(r'[\w.-]+')

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
| audio/ | запись звонка (если удалось получить; иначе причина в manifest.json → audio) |
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


async def _remote_audio(record: Record) -> bytes:
    from server.asr.audio import fetch_call_audio

    return await fetch_call_audio(record)


async def local_audio_size(svc: Services, cid: str, group_id: str) -> int | None:
    """Bytes of the recording held by this server (upload store or `data/audio/<cid>.mp3`); None when it is not local."""
    try:
        if group_id == UPLOADS:
            return len((await svc.uploads.audio(cid))[0])
        if _SAFE_ID.fullmatch(cid) and (path := AUDIO_DIR / f'{cid}.mp3').is_file():
            return path.stat().st_size
    except NotFound:
        pass
    return None


async def call_audio(svc: Services, record: Record, group_id: str) -> tuple[bytes | None, str, dict[str, Any]]:
    """(bytes or None, file name, manifest `audio` entry) for a conversation's recording.

    Order: the upload store, `data/audio/<cid>.mp3`, then the signed `audio_url` of the organizer (bounded wait).
    Chats have no audio (`not_applicable`); anything that cannot be packaged says why instead of silently vanishing."""
    if record.channel != 'voice call':
        return None, '', {'status': 'not_applicable', 'reason': 'диалог не является звонком'}
    cid = record.conversation_id
    data: bytes | None = None
    name = f'{cid}.mp3'
    reason = ''
    try:
        if group_id == UPLOADS:
            data, _, name = await svc.uploads.audio(cid)
        elif _SAFE_ID.fullmatch(cid) and (path := AUDIO_DIR / f'{cid}.mp3').is_file():
            data = await asyncio.to_thread(path.read_bytes)
        elif record.audio_url:
            data = await asyncio.wait_for(_remote_audio(record), REMOTE_TIMEOUT_S)
        else:
            reason = 'у звонка нет audio_url и нет локального файла'
    except NotFound as e:
        reason = str(e)
    except TimeoutError:
        reason = f'аудио не получено за {REMOTE_TIMEOUT_S:.0f} с'
    except Exception as e:  # AsrError and network failures: the pack is still useful without the recording
        reason = str(e) or type(e).__name__
    if data is None:
        return None, '', {'status': 'missing', 'reason': reason}
    if len(data) > MAX_AUDIO_BYTES:
        return None, '', {'status': 'too_large', 'bytes': len(data), 'limit': MAX_AUDIO_BYTES,
                          'reason': f'запись больше {MAX_AUDIO_BYTES // (1024 * 1024)} МБ'}
    return data, name, {'status': 'included', 'bytes': len(data)}


async def build_regpack(
    svc: Services, cid: str, group_id: str, evaluation_id: str | None
) -> tuple[bytes, str, bool, str]:
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
    audio, audio_name, audio_info = await call_audio(svc, record, group_id)

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
    hashes = {name: _sha(b) for name, b in blobs.items()}
    if audio is not None:
        audio_file = f'audio/{audio_name}'
        audio_info = {**audio_info, 'file': audio_file}
        hashes[audio_file] = _sha(audio)
    manifest = {
        'evaluation_id': ev.id,
        'conversation_id': cid,
        'group_id': ev.group_id,
        'checklist': {'id': ev.checklist_id, 'version': ev.checklist_version},
        'transcript_source': ev.transcript_source,
        'exported_at': datetime.now(UTC).isoformat(),
        'sha256': hashes,
        'audio': audio_info,
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
        if audio is not None:
            z.writestr(audio_file, audio, compress_type=zipfile.ZIP_STORED)  # MP3 does not compress
    return buf.getvalue(), f'regpack-{cid}-{ev.id}.zip', check['ok'], audio_info['status']


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
        audio_file = (manifest.get('audio') or {}).get('file')
        if audio_file:
            if audio_file not in names:
                problems.append(f'{audio_file}: файл записи указан в manifest.json, но его нет в архиве')
            elif manifest.get('sha256', {}).get(audio_file) != _sha(z.read(audio_file)):
                problems.append(f'{audio_file}: хеш не совпадает с manifest.json')
    for name in FILES:
        if manifest.get('sha256', {}).get(name) != _sha(raw[name]):
            problems.append(f'{name}: хеш не совпадает с manifest.json')
    docs = {n: json.loads(raw[n]) for n in FILES}
    check = selfcheck(docs['checklist.json'], docs['evaluation.json'], docs['appeals.json'], docs['final.json'])
    if not check['ok']:
        problems.append(f'итог не сходится: пересчитано {check["recomputed_total"]}, в деле {check["stored_total"]}')
    return {'ok': not problems, 'problems': problems, 'selfcheck': check}
