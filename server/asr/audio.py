"""Fetch the MP3 of a call.

`Record.audio_url` is an HTML player page; the real MP3 is the `<source src>` inside it: a signed Dynamics URL that
expires after about an hour, so fetch right before use. The network here drops connections for ~20 s at a time.
"""

from __future__ import annotations

import asyncio
import html
import re

from server.asr.base import AsrError
from server.http import new_session
from server.models import Record

ATTEMPTS = 6
RETRY_PAUSE_S = 5.0
TIMEOUT_S = 120
HEADERS = {'User-Agent': 'Mozilla/5.0 (cqa)'}
_SOURCE = re.compile(r'<source\b[^>]*?\bsrc\s*=\s*(?:"([^"]+)"|\'([^\']+)\')', re.IGNORECASE)
_MP3_MAGIC = (b'ID3', b'\xff\xfb', b'\xff\xf3', b'\xff\xf2', b'\xff\xe3')


def _is_audio(content: bytes, content_type: str) -> bool:
    return content_type.lower().startswith('audio/') or content.startswith(_MP3_MAGIC)


def extract_source_url(page: str) -> str | None:
    m = _SOURCE.search(page)
    if not m:
        return None
    return html.unescape(m.group(1) or m.group(2))


async def fetch_call_audio(record: Record) -> bytes:
    """HTML player page -> `<source src>` -> MP3 bytes, with retries. `AsrError` on failure."""
    if not record.audio_url:
        raise AsrError(f'У звонка {record.conversation_id} нет audio_url')
    session = new_session()
    last = ''
    for attempt in range(ATTEMPTS):
        try:
            page = await session.get(record.audio_url, headers=HEADERS, timeout=TIMEOUT_S)
            if page.status_code in (401, 403, 404, 410):
                raise AsrError(
                    f'Ссылка на аудио звонка {record.conversation_id} недоступна (HTTP {page.status_code}): '
                    'подписанная ссылка истекла, обновите набор данных'
                )
            if page.status_code != 200:
                last = f'плеер вернул HTTP {page.status_code}'
            else:
                content = page.content or b''
                if _is_audio(content, page.headers.get('content-type') or ''):
                    return content
                src = extract_source_url(page.text or '')
                if not src:
                    raise AsrError(f'В странице плеера звонка {record.conversation_id} нет <source src>')
                mp3 = await session.get(src, headers=HEADERS, timeout=TIMEOUT_S)
                if mp3.status_code == 200 and mp3.content:
                    return mp3.content
                last = f'mp3 вернул HTTP {mp3.status_code}'
        except AsrError:
            raise
        except Exception as exc:
            last = f'сбой соединения: {type(exc).__name__}'
        if attempt < ATTEMPTS - 1:
            await asyncio.sleep(RETRY_PAUSE_S)
    raise AsrError(f'Не удалось скачать аудио звонка {record.conversation_id}: {last} (попыток: {ATTEMPTS})')


# MPEG-1 / MPEG-2(.5) Layer III: samples per frame and sample rates
_SAMPLE_RATES = {3: (44100, 48000, 32000), 2: (22050, 24000, 16000), 0: (11025, 12000, 8000)}
_BITRATES_V1 = (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320)
_BITRATES_V2 = (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160)


def mp3_duration_s(audio: bytes) -> float | None:
    """Duration of an MP3 from its first frame header: the Xing/Info frame count (VBR) or the bitrate (CBR).
    An estimate for providers that do not report a duration; None when the header is not recognised."""
    start = 0
    if audio.startswith(b'ID3') and len(audio) > 10:
        start = 10 + ((audio[6] & 0x7F) << 21 | (audio[7] & 0x7F) << 14 | (audio[8] & 0x7F) << 7 | (audio[9] & 0x7F))
    for pos in range(start, min(len(audio) - 4, start + 4096)):
        if audio[pos] != 0xFF or (audio[pos + 1] & 0xE0) != 0xE0:
            continue
        version = (audio[pos + 1] >> 3) & 3  # 3 = MPEG1, 2 = MPEG2, 0 = MPEG2.5
        layer = (audio[pos + 1] >> 1) & 3
        bitrate_idx = audio[pos + 2] >> 4
        rate_idx = (audio[pos + 2] >> 2) & 3
        if version == 1 or layer != 1 or bitrate_idx in (0, 15) or rate_idx == 3:
            continue
        rate = _SAMPLE_RATES[version][rate_idx]
        samples = 1152 if version == 3 else 576
        mono = (audio[pos + 3] >> 6) == 3
        side = (17 if mono else 32) if version == 3 else (9 if mono else 17)
        window = audio[pos + 4 : pos + 4 + side + 12]
        for tag in (b'Xing', b'Info'):
            at = window.find(tag)
            if at >= 0 and len(window) >= at + 12 and window[at + 7] & 1:
                frames = int.from_bytes(window[at + 8 : at + 12], 'big')
                return frames * samples / rate
        bitrate = (_BITRATES_V1 if version == 3 else _BITRATES_V2)[bitrate_idx] * 1000
        return (len(audio) - pos) * 8 / bitrate
    return None


def _frames(audio: bytes) -> tuple[list[tuple[int, int]], float]:
    """(start, length) of every MPEG audio frame after the ID3 tag, and the seconds per frame. The Xing/Info frame is skipped."""
    pos = 0
    if audio.startswith(b'ID3') and len(audio) > 10:
        pos = 10 + ((audio[6] & 0x7F) << 21 | (audio[7] & 0x7F) << 14 | (audio[8] & 0x7F) << 7 | (audio[9] & 0x7F))
    frames: list[tuple[int, int]] = []
    frame_s = 0.0
    while pos + 4 <= len(audio):
        if audio[pos] != 0xFF or (audio[pos + 1] & 0xE0) != 0xE0:
            pos += 1
            continue
        version = (audio[pos + 1] >> 3) & 3
        layer = (audio[pos + 1] >> 1) & 3
        bitrate_idx = audio[pos + 2] >> 4
        rate_idx = (audio[pos + 2] >> 2) & 3
        if version == 1 or layer != 1 or bitrate_idx in (0, 15) or rate_idx == 3:
            pos += 1
            continue
        rate = _SAMPLE_RATES[version][rate_idx]
        bitrate = (_BITRATES_V1 if version == 3 else _BITRATES_V2)[bitrate_idx] * 1000
        samples = 1152 if version == 3 else 576
        length = samples // 8 * bitrate // rate + ((audio[pos + 2] >> 1) & 1)
        frame_s = samples / rate
        if not frames and (b'Xing' in audio[pos : pos + 60] or b'Info' in audio[pos : pos + 60]):
            pos += length
            continue
        frames.append((pos, length))
        pos += length
    return frames, frame_s


def split_mp3(audio: bytes, max_s: float) -> list[tuple[float, bytes]]:
    """Cut an MP3 into equal pieces of at most `max_s` seconds at frame boundaries: [(offset in seconds, bytes)].
    Returned as is when it already fits or the frames cannot be parsed."""
    frames, frame_s = _frames(audio)
    if not frames or len(frames) * frame_s <= max_s:
        return [(0.0, audio)]
    parts = int(len(frames) * frame_s // max_s) + 1
    per = -(-len(frames) // parts)
    out = []
    for i in range(0, len(frames), per):
        chunk = frames[i : i + per]
        body = b''.join(audio[s : s + n] for s, n in chunk)
        out.append((i * frame_s, _xing_frame(audio, chunk[0], len(chunk), len(body)) + body))
    return out


def _xing_frame(audio: bytes, first: tuple[int, int], frames: int, size: int) -> bytes:
    """A VBR header frame: without it a decoder guesses the duration of a cut piece from the bitrate of its first frame
    (a silent 8 kbit/s one makes a 5 minute piece look like 30 minutes)."""
    start, length = first
    header = bytearray(audio[start : start + 4])
    header[1] |= 1  # no CRC
    mono = (header[3] >> 6) == 3
    version = (header[1] >> 3) & 3
    side = (17 if mono else 32) if version == 3 else (9 if mono else 17)
    tag = b'Xing' + (3).to_bytes(4, 'big') + frames.to_bytes(4, 'big') + size.to_bytes(4, 'big')
    frame = bytes(header) + bytes(side) + tag
    if len(frame) > length:  # the frame is too small to hold it: use the largest frame size, a 128 kbit/s one
        header[2] = (header[2] & 0x0F) | ((9 if version == 3 else 12) << 4)
        length = (1152 if version == 3 else 576) // 8 * (_BITRATES_V1 if version == 3 else _BITRATES_V2)[header[2] >> 4] * 1000 // _SAMPLE_RATES[version][(header[2] >> 2) & 3]
        frame = bytes(header) + bytes(side) + tag
    return frame + bytes(length - len(frame))
