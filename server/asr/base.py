from pydantic import BaseModel


class AsrSegment(BaseModel):
    start: float | None  # seconds from audio start
    end: float | None
    speaker: str | None  # raw provider label ('speaker-0', 'A', None)
    text: str


class AsrResult(BaseModel):
    provider: str  # name from config/asr.toml
    model: str
    language: str | None
    duration_s: float | None
    seconds: float  # wall time of the ASR call
    diarized: bool  # provider returned speaker labels
    segments: list[AsrSegment]
    text: str


class AsrError(Exception):
    """ASR failed or the provider is not configured ("… не настроен")."""
