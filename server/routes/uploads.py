"""`/api/uploads`: add a call recording or a chat by hand, into the `UPLOADS` group."""

from dataclasses import dataclass
from typing import Annotated, Literal

from litestar import Controller, Response, delete, get, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.exceptions import HTTPException
from litestar.params import Body, FromPath, JSONBody

from server.jobs import resolve_settings
from server.models import BatchRequest, Record, UploadChatRequest
from server.routes import Svc
from server.routes.transcripts import ASR_UNAVAILABLE, _unconfigured
from server.transcripts import parse_custom_text
from server.uploads import MAX_AUDIO_BYTES, UPLOADS, audio_ext, language_from_asr, to_mp3

DEFAULT_PROVIDER = 'h200-whisperx'  # the only provider that both handles Kazakh and labels speakers
_HINT = {'KZ': 'kk', 'RU': 'ru', 'EN': 'en'}


@dataclass
class UploadCallForm:
    file: UploadFile
    language: Literal['auto', 'RU', 'KZ', 'EN'] = 'auto'
    provider: str = DEFAULT_PROVIDER


class UploadsController(Controller):
    path = '/uploads'

    @post('/call', status_code=200, request_max_body_size=MAX_AUDIO_BYTES + 1024 * 1024)
    async def upload_call(
        self, svc: Svc, data: Annotated[UploadCallForm, Body(media_type=RequestEncodingType.MULTI_PART)]
    ) -> Record:
        """Recording -> ASR (speaker roles, masking) -> a new call in `UPLOADS`, ready to evaluate.

        `auto` lets the provider detect the language (and re-run Kazakh audio as `kk`); a chosen language is trusted
        and passed as the hint."""
        try:
            from server.asr import providers, to_record
            from server.asr.base import AsrError
        except ImportError:
            raise HTTPException(status_code=503, detail=ASR_UNAVAILABLE) from None
        ext = audio_ext(data.file.filename)
        audio = await data.file.read()
        if not audio:
            raise HTTPException(status_code=400, detail='Файл пустой')
        if len(audio) > MAX_AUDIO_BYTES:
            raise HTTPException(status_code=413, detail=f'Файл больше {MAX_AUDIO_BYTES // (1024 * 1024)} МБ')
        audio, ext = await to_mp3(audio, ext)
        configured = providers.load_asr_providers()
        provider = configured.get(data.provider)
        if provider is None:
            names = ', '.join(configured) or 'нет'
            raise HTTPException(status_code=400, detail=f'Неизвестный провайдер {data.provider!r}; доступны: {names}')

        cid = await svc.uploads.new_id('call')
        base = Record(
            conversation_id=cid,
            channel='voice call',
            language=data.language if data.language != 'auto' else 'RU',
            transcript=[],
            audio_url=f'/api/uploads/{cid}/audio',
        )
        judge, _, _ = resolve_settings(BatchRequest(group_id=UPLOADS, conversation_ids=[cid]), svc.profiles)
        try:
            hint = _HINT.get(data.language)
            result = await providers.transcribe(provider, audio, f'{cid}{ext}', language=hint)
            if data.language == 'auto':
                base = base.model_copy(update={'language': language_from_asr(result.language, result.text)})
            record = await to_record.asr_to_record(result, base, judge)
        except AsrError as e:
            message = str(e) or type(e).__name__
            if _unconfigured(message):
                raise HTTPException(status_code=400, detail=f'Провайдер «{provider.label}» не настроен: {message}') from None
            raise HTTPException(status_code=502, detail=f'Распознавание не удалось: {message}') from None
        await svc.uploads.save_audio(cid, audio, ext)
        await svc.uploads.save(record)
        # Also a transcript source of its own, so «Распознать заново» with another provider can be compared to it.
        await svc.transcripts.save(data.provider, record)
        return record

    @post('/chat', status_code=200)
    async def upload_chat(self, svc: Svc, data: JSONBody[UploadChatRequest]) -> Record:
        """Pasted chat (`оператор:` / `клиент:` / `бот:` lines) -> a new chat in `UPLOADS`."""
        cid = await svc.uploads.new_id('chat')
        base = Record(conversation_id=cid, channel='agent chat', language=data.language, transcript=[], audio_url=None)
        record = parse_custom_text(data.text, base)  # ValueError -> 400; a skipped id is harmless
        await svc.uploads.save(record)
        return record

    @get('/{cid:str}/audio')
    async def audio(self, svc: Svc, cid: FromPath[str]) -> Response[bytes]:
        body, media_type, name = await svc.uploads.audio(cid)
        return Response(body, media_type=media_type, headers={'Content-Disposition': f'inline; filename="{name}"'})

    @delete('/{cid:str}', status_code=204)
    async def remove(self, svc: Svc, cid: FromPath[str]) -> None:
        await svc.uploads.delete(cid)
