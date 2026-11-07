from litestar import Controller, get, post, put
from litestar.exceptions import HTTPException
from litestar.params import FromPath, JSONBody

from server.jobs import resolve_settings
from server.models import (
    AsrProviderInfo,
    BatchRequest,
    CustomTranscriptRequest,
    Record,
    TranscribeRequest,
    TranscriptSourceInfo,
)
from server.routes import Svc
from server.transcripts import CUSTOM, parse_custom_text
from server.uploads import UPLOADS

CALLS_ONLY = 'Распознавание и свой транскрипт доступны только для звонков'
ASR_UNAVAILABLE = 'Модуль распознавания речи недоступен'


def _unconfigured(message: str) -> bool:
    low = message.lower()
    return 'не настро' in low or 'not configured' in low


class TranscriptsController(Controller):
    path = '/'

    @get('/asr/providers')
    async def asr_providers(self, svc: Svc) -> list[AsrProviderInfo]:
        """Providers offered in the call card, in `config/asr.toml` order; an unconfigured one says what env it needs."""
        try:
            from server.asr.providers import load_asr_providers
        except ImportError:
            return []
        quality = svc.transcripts.quality()
        out = []
        for p in load_asr_providers().values():
            if not p.enabled:
                continue
            missing = p.missing_env()
            out.append(AsrProviderInfo(
                id=p.name, label=p.label, hosting=p.hosting, available=not missing,
                note=f'не настроен: задайте {", ".join(missing)}' if missing else None,
                quality=quality.get(p.name),
            ))
        return out

    @get('/conversations/{cid:str}/transcripts')
    async def sources(self, svc: Svc, cid: FromPath[str]) -> list[TranscriptSourceInfo]:
        return await svc.transcripts.sources(cid)

    @post('/conversations/{cid:str}/transcribe', status_code=200)
    async def transcribe(self, svc: Svc, cid: FromPath[str], data: JSONBody[TranscribeRequest]) -> Record:
        """Audio -> ASR -> speaker roles and masking -> stored as source `<provider>`."""
        try:
            from server.asr import audio, providers, to_record
            from server.asr.base import AsrError
        except ImportError:
            raise HTTPException(status_code=503, detail=ASR_UNAVAILABLE) from None
        configured = providers.load_asr_providers()
        provider = configured.get(data.provider)
        if provider is None:
            names = ', '.join(configured) or 'нет'
            raise HTTPException(status_code=400, detail=f'Неизвестный провайдер {data.provider!r}; доступны: {names}')
        base = await svc.group_record(data.group_id, cid)
        if base.channel != 'voice call':
            raise HTTPException(status_code=400, detail=CALLS_ONLY)
        # The judge model that assigns roles and masks PII: env `LLM_PROFILE`, like a batch without an explicit profile.
        judge, _, _ = resolve_settings(BatchRequest(group_id=data.group_id, conversation_ids=[cid]), svc.profiles)
        try:
            if data.group_id == UPLOADS:
                raw_audio, _, filename = await svc.uploads.audio(cid)
            else:
                raw_audio, filename = await audio.fetch_call_audio(base), f'{cid}.mp3'
            # Only a KZ label forces a language. Forcing `ru` on a mislabelled Kazakh call (record `1234`)
            # would make the output look Russian and silence the Kazakh re-run, so RU/EN auto-detect instead.
            hint = 'kk' if (base.language or '').upper() == 'KZ' else None
            result = await providers.transcribe(provider, raw_audio, filename, language=hint)
            record = await to_record.asr_to_record(result, base, judge)
        except AsrError as e:
            message = str(e) or type(e).__name__
            if _unconfigured(message):
                raise HTTPException(
                    status_code=400, detail=f'Провайдер «{provider.label}» не настроен: {message}'
                ) from None
            raise HTTPException(status_code=502, detail=f'Распознавание не удалось: {message}') from None
        await svc.transcripts.save(data.provider, record)
        return record

    @put('/conversations/{cid:str}/transcripts/custom')
    async def custom(self, svc: Svc, cid: FromPath[str], data: JSONBody[CustomTranscriptRequest]) -> Record:
        base = await svc.group_record(data.group_id, cid)
        if base.channel != 'voice call':
            raise HTTPException(status_code=400, detail=CALLS_ONLY)
        record = parse_custom_text(data.text, base)  # ValueError -> 400 ApiError
        await svc.transcripts.save(CUSTOM, record)
        return record
