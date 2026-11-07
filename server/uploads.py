"""Conversations added by hand in the UI: an uploaded call recording or a pasted chat.

They live in their own group `UPLOADS`, next to the organizer's dataset groups, so the whole cycle (evaluate, result,
appeal, re-evaluate, analytics) works on them unchanged. Records and audio stay under the store root (`data/store`,
gitignored): call audio is personal data.
"""

import asyncio
import logging
import re
import shutil
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
FFMPEG_TIMEOUT_S = 120
log = logging.getLogger(__name__)
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
        # pipe only: a crafted playlist-like upload must not make ffmpeg open local files or URLs
        ffmpeg, '-hide_banner', '-loglevel', 'error', '-protocol_whitelist', 'pipe', '-i', 'pipe:0',
        '-ac', '1', '-ar', '16000', '-b:a', '48k', '-f', 'mp3', 'pipe:1',
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(data), FFMPEG_TIMEOUT_S)
    except TimeoutError:
        proc.kill()
        raise ValueError('Аудиофайл слишком долго конвертируется: сохраните его как MP3 и загрузите снова') from None
    if proc.returncode != 0 or not out:
        log.info('ffmpeg rejected an upload: %s', err.decode(errors='replace').strip()[:300])
        raise ValueError('Не удалось прочитать аудиофайл: формат не распознан или файл повреждён')
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
        if not _ID.fullmatch(cid):
            raise NotFound(f'диалог {cid} не найден в группе {UPLOADS}')
        return self._records / f'{cid}.json'

    async def new_id(self, kind: str) -> str:
        """`up-call-001`, `up-chat-002`, ...: one counter for both kinds that only grows. A deleted upload's id is
        never reused: its evaluations and transcript sources stay in the store and would attach to the new dialog."""
        async with self._lock:
            counter = self.root / 'last_id'

            def take() -> int:
                last = int(counter.read_text(encoding='utf-8')) if counter.exists() else 0
                seen = [int(p.stem.rsplit('-', 1)[1]) for d in (self._records, self._audio)
                        for p in d.glob('up-*-*.*') if _ID.fullmatch(p.stem)]
                n = max([last, *seen]) + 1
                atomic_write(counter, str(n))
                return n

            return f'up-{kind}-{await asyncio.to_thread(take):03d}'

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

    async def save_audio(self, cid: str, data: bytes, ext: str) -> None:
        def write() -> None:
            self._audio.mkdir(parents=True, exist_ok=True)
            tmp = self._audio / f'{cid}{ext}.tmp'
            tmp.write_bytes(data)
            tmp.replace(self._audio / f'{cid}{ext}')

        await asyncio.to_thread(write)

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

