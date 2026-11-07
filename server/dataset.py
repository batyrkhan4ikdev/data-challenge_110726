import asyncio
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import ValidationError

from server.http import new_session
from server.models import Record, Turn

_FRACTION = re.compile(r'(\.\d{6})\d+')
# Waits between dataset fetch attempts on a connection error or HTTP 5xx (4 attempts, ~35 s worst case).
RETRY_DELAYS_S: tuple[float, ...] = (5.0, 10.0, 20.0)


class DatasetError(Exception):
    pass


def _parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(_FRACTION.sub(r'\1', ts))


def _build_record(rec: Any) -> Record:
    if not isinstance(rec, dict):
        raise DatasetError('bad shape: record is not an object')
    cid = rec.get('conversation_id')
    transcript = rec.get('transcript')
    if not isinstance(transcript, list):
        raise DatasetError(f'bad shape: transcript missing or not a list in {cid}')
    turns: list[Turn] = []
    t0: datetime | None = None
    for i, raw in enumerate(transcript):
        if not isinstance(raw, dict):
            raise DatasetError(f'bad shape: turn {i} of {cid} is not an object')
        ts = raw.get('timestamp')
        offset: float | None = None
        if isinstance(ts, str) and 'T' in ts:
            try:
                dt = _parse_iso(ts)
                if t0 is None:
                    t0 = _parse_iso(str(transcript[0].get('timestamp')))
                offset = (dt - t0).total_seconds()
            except (ValueError, TypeError, AttributeError) as e:
                raise DatasetError(f'bad timestamp in turn {i} of {cid}: {e}') from None
        try:
            turns.append(
                Turn(idx=i, timestamp=ts, offset_s=offset, speaker=raw.get('speaker'), text=raw.get('text'))
            )
        except ValidationError as e:
            if any(err['loc'] and err['loc'][0] == 'speaker' for err in e.errors()):
                raise DatasetError(f'unknown speaker {raw.get("speaker")!r} in {cid}') from None
            raise DatasetError(f'bad turn {i} in {cid}') from None
    try:
        return Record(
            conversation_id=cid,
            channel=rec.get('channel'),
            language=rec.get('language'),
            transcript=turns,
            audio_url=rec.get('audio_url'),
        )
    except ValidationError:
        raise DatasetError(f'bad record {cid}') from None


def normalize_response(payload: dict, group_id: str, rejects: dict[str, str] | None = None) -> list[Record]:
    """Parse the API payload. A malformed record raises `DatasetError`, unless `rejects` is given:
    then it is recorded there as {conversation_id: reason} and skipped, so one bad record cannot sink a run.
    """
    if not isinstance(payload, dict) or payload.get('isSuccess') is not True:
        err = payload.get('error') if isinstance(payload, dict) else None
        raise DatasetError(err or 'isSuccess=false')
    data = payload.get('data')
    records = data.get('records') if isinstance(data, dict) else None
    if not isinstance(records, list):
        raise DatasetError(f'bad shape: data.records is not a list (group {group_id})')
    if rejects is None:
        return [_build_record(r) for r in records]
    out: list[Record] = []
    for n, raw in enumerate(records):
        try:
            out.append(_build_record(raw))
        except DatasetError as e:
            cid = raw.get('conversation_id') if isinstance(raw, dict) else None
            rejects[cid if isinstance(cid, str) and cid else f'<record {n}>'] = f'Запись не разобрана: {e}'
    return out


def load_fixture(path: Path = Path('tests/fixtures/dev.json')) -> list[Record]:
    return normalize_response(json.loads(Path(path).read_text(encoding='utf-8')), 'DEV')


def _with_group(url: str, group_id: str) -> str:
    parts = urlsplit(url)
    q = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != 'group_id']
    q.append(('group_id', group_id))
    return urlunsplit(parts._replace(query=urlencode(q)))


async def load_dataset(
    group_id: str, refresh: bool = False, session=None, cache_dir: Path = Path('data/cache'),
    rejects: dict[str, str] | None = None,
) -> list[Record]:
    """Fetch (or read the cache of) a group. `rejects`: see `normalize_response`."""
    cache = Path(cache_dir) / f'{group_id}.json'
    if cache.exists() and not refresh:
        try:
            return normalize_response(json.loads(cache.read_text(encoding='utf-8')), group_id, rejects)
        except ValueError as e:
            raise DatasetError(f'bad cache {cache.name}: {type(e).__name__}') from None
    base = os.environ.get('DATASET_URL')
    if not base:
        raise DatasetError('DATASET_URL не задан')
    url = _with_group(base, group_id)
    host = urlsplit(url).hostname or 'unknown host'
    sess = session or new_session()
    resp = None
    last = ''
    for attempt, delay in enumerate((*RETRY_DELAYS_S, None)):
        # The network here drops connections for ~20 s at a time; one blip must not sink a 1-hour control window.
        try:
            resp = await sess.get(url, timeout=60)
        except Exception as e:
            last = f'request to {host} failed: {type(e).__name__}'
            resp = None
        else:
            if resp.status_code < 500:
                break
            last = f'{host} returned HTTP {resp.status_code}'
        if delay is None:
            raise DatasetError(f'{last} (after {attempt + 1} attempts)')
        await asyncio.sleep(delay)
    assert resp is not None
    if resp.status_code != 200:
        raise DatasetError(f'{host} returned HTTP {resp.status_code}')
    try:
        payload = resp.json()
    except Exception:
        raise DatasetError(f'{host} returned non-JSON response') from None
    records = normalize_response(payload, group_id, rejects)
    cache.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=cache.parent, prefix=f'.{group_id}.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False)
        os.replace(tmp, cache)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return records
