"""Conversations added by hand in the UI: an uploaded call recording or a pasted chat.

They live in their own group `UPLOADS`, next to the organizer's dataset groups, so the whole cycle (evaluate, result,
appeal, re-evaluate, analytics) works on them unchanged. Records and audio stay under the store root (`data/store`,
gitignored): call audio is personal data.
"""

import asyncio
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

from server.models import Record
from server.store import NotFound, atomic_write

UPLOADS = 'UPLOADS'
AUDIO_TYPES = {
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.ogg': 'audio/ogg',
    '.m4a': 'audio/mp4',
    '.webm': 'audio/webm',
    '.flac': 'audio/flac',
}
MAX_AUDIO_BYTES = 50 * 1024 * 1024
_ID = re.compile(r'^up-(call|chat)-\d{3,}$')


def audio_ext(filename: str | None) -> str:
    """The audio extension of an uploaded file name; `ValueError` for anything that is not a supported audio type."""
    ext = Path(filename or '').suffix.lower()
    if ext not in AUDIO_TYPES:
        raise ValueError(f'Неподдерживаемый формат аудио {ext or "(без расширения)"}: нужен {", ".join(AUDIO_TYPES)}')
    return ext


async def to_mp3(data: bytes, ext: str) -> tuple[bytes, str]:
    """Non-MP3 audio -> 16 kHz mono MP3 via ffmpeg, so the ASR client can cut long calls at frame boundaries.
    Returned unchanged when it already is MP3 or ffmpeg is not installed."""
    ffmpeg = shutil.which('ffmpeg')
    if ext == '.mp3' or not ffmpeg:
        return data, ext
    proc = await asyncio.create_subprocess_exec(
        ffmpeg, '-hide_banner', '-loglevel', 'error', '-i', 'pipe:0', '-ac', '1', '-ar', '16000', '-b:a', '48k',
        '-f', 'mp3', 'pipe:1',
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate(data)
    if proc.returncode != 0 or not out:
        raise ValueError(f'Не удалось прочитать аудиофайл: {err.decode(errors="replace").strip()[:200] or "ffmpeg"}')
    return out, '.mp3'


class UploadStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self._lock = asyncio.Lock()

    @property
    def _records(self) -> Path:
        return self.root / 'records'

    @property
    def _audio(self) -> Path:
        return self.root / 'audio'

    def _record_path(self, cid: str) -> Path:
        if not _ID.match(cid):
            raise NotFound(f'диалог {cid} не найден в группе {UPLOADS}')
        return self._records / f'{cid}.json'

    async def new_id(self, kind: str) -> str:
        """`up-call-001`, `up-chat-002`, ...: one counter for both kinds, never reused while the files exist."""
        async with self._lock:
            taken = await asyncio.to_thread(
                lambda: [int(p.stem.rsplit('-', 1)[1]) for p in self._records.glob('up-*-*.json') if _ID.match(p.stem)]
                + [int(p.stem.rsplit('-', 1)[1]) for p in self._audio.glob('up-*-*.*') if _ID.match(p.stem)]
            )
            cid = f'up-{kind}-{max(taken, default=0) + 1:03d}'
            # Reserve the id right away so a second upload in flight does not take it.
            await asyncio.to_thread(atomic_write, self._audio / f'{cid}.reserved', datetime.now(UTC).isoformat())
            return cid

    async def records(self) -> list[Record]:
        def read() -> list[Record]:
            out = []
            for p in sorted(self._records.glob('up-*.json')):
                out.append(Record.model_validate_json(p.read_text(encoding='utf-8')))
            return out

        return await asyncio.to_thread(read)

    async def save(self, record: Record) -> None:
        path = self._record_path(record.conversation_id)
        await asyncio.to_thread(atomic_write, path, record.model_dump_json(indent=2))
        await asyncio.to_thread(lambda: (self._audio / f'{record.conversation_id}.reserved').unlink(missing_ok=True))

    async def save_audio(self, cid: str, data: bytes, ext: str) -> None:
        def write() -> None:
            self._audio.mkdir(parents=True, exist_ok=True)
            tmp = self._audio / f'{cid}{ext}.tmp'
            tmp.write_bytes(data)
            tmp.replace(self._audio / f'{cid}{ext}')

        await asyncio.to_thread(write)

    async def delete_reserved(self, cid: str) -> None:
        """Frees an id taken by `new_id` when the upload failed before anything was saved."""
        await asyncio.to_thread(lambda: (self._audio / f'{cid}.reserved').unlink(missing_ok=True))

    def _audio_file(self, cid: str) -> Path | None:
        self._record_path(cid)  # validates the id
        for ext in AUDIO_TYPES:
            p = self._audio / f'{cid}{ext}'
            if p.exists():
                return p
        return None

    async def audio(self, cid: str) -> tuple[bytes, str, str]:
        """(bytes, media type, file name) of an upload's recording; `NotFound` when it has none."""
        path = await asyncio.to_thread(self._audio_file, cid)
        if path is None:
            raise NotFound(f'у диалога {cid} нет аудиозаписи')
        return await asyncio.to_thread(path.read_bytes), AUDIO_TYPES[path.suffix], path.name

    async def delete(self, cid: str) -> None:
        """Removes the record and the recording. Evaluations made on it stay in the store, like any history."""
        record = self._record_path(cid)

        def remove() -> bool:
            found = record.exists()
            record.unlink(missing_ok=True)
            for p in self._audio.glob(f'{cid}.*'):
                found = True
                p.unlink(missing_ok=True)
            return found

        if not await asyncio.to_thread(remove):
            raise NotFound(f'диалог {cid} не найден в группе {UPLOADS}')


def language_from_asr(detected: str | None, text: str) -> str:
    """Dataset language label for an ASR result: what the model detected, then the Kazakh-letter check."""
    from server.asr.providers import KAZAKH_SHARE_MIN, kazakh_share

    code = (detected or '').lower()
    if code in {'kk', 'kaz', 'kazakh'} or kazakh_share(text) >= KAZAKH_SHARE_MIN:
        return 'KZ'
    if code in {'en', 'eng', 'english'}:
        return 'EN'
    return 'RU'

