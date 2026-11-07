from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

Channel = Literal['agent chat', 'voice call']
Speaker = Literal['client', 'operator', 'bot', 'system']
Mode = Literal['single', 'per_criterion']


class Turn(BaseModel):
    idx: int
    timestamp: str
    offset_s: float | None = None
    speaker: Speaker
    text: str


class Record(BaseModel):
    conversation_id: str
    channel: Channel
    language: Literal['RU', 'KZ', 'EN']
    transcript: list[Turn]
    audio_url: str | None


class MaskedToken(BaseModel):
    token: str
    count: int
    first_idx: int


class DialogEvent(BaseModel):
    idx: int
    text: str
    offset_s: float | None = None


class DialogFacts(BaseModel):
    duration_s: float | None = None
    escalation_idx: int | None = None
    first_response_s: float | None = None
    first_response_idx: int | None = None
    sla_s: int = 180
    sla_ok: bool | None = None
    max_wait_s: float | None = None
    max_wait_idx: int | None = None
    turns: dict[str, int]
    masked: list[MaskedToken]
    events: list[DialogEvent]
    identity_verified_idx: int | None = None


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    calls: int
    seconds: float


class EvaluationSummary(BaseModel):
    id: str
    checklist_id: str
    checklist_version: int
    total: float | None
    final_total: float | None
    gross_error: bool
    created_at: datetime


class ConversationSummary(BaseModel):
    conversation_id: str
    channel: Channel
    language: Literal['RU', 'KZ', 'EN']
    turns: int
    latest: EvaluationSummary | None


class ScaleStep(BaseModel):
    value: int
    description: str


class Section(BaseModel):
    id: str
    title: str


class Criterion(BaseModel):
    id: str
    section_id: str | None
    title: str
    description: str
    answer_type: Literal['yes_no', 'scale']
    weight: float
    steps: list[ScaleStep] | None
    na_allowed: bool
    na_condition: str | None
    kind: Literal['scored', 'gross_error'] = 'scored'


class Checklist(BaseModel):
    id: str
    name: str
    channel_default: Channel | None
    version: int
    sections: list[Section]
    criteria: list[Criterion]
    notes: str
    source: str


class ChecklistSummary(BaseModel):
    id: str
    name: str
    channel_default: Channel | None
    version: int


class Item(BaseModel):
    criterion_id: str
    verdict: str
    explanation: str
    evidence_idx: list[int]
    expected_range: tuple[int, int] | None = None
    na_reason: str | None = None
    votes: dict[str, int] = {}
    warnings: list[str] = []  # accepted despite a soft rule violation (e.g. missing evidence after the retry)


class ScoreItem(BaseModel):
    criterion_id: str
    verdict: str
    applicable: bool
    points: float | None
    max_points: float
    effective_points: float | None


class SectionScore(BaseModel):
    section_id: str
    title: str
    total: float | None


class Score(BaseModel):
    total: float | None
    sections: list[SectionScore]
    gross_error: bool
    applicable_weight: float
    items: list[ScoreItem]


class Evaluation(BaseModel):
    id: str
    conversation_id: str
    group_id: str
    checklist_id: str
    checklist_version: int
    profile: str
    model: str
    mode: Mode
    k: int
    created_at: datetime
    items: list[Item]
    score: Score
    usage: Usage
    transcript_source: str = 'api'


class RawCall(BaseModel):
    evaluation_id: str
    criterion_ids: list[str]
    messages: list[dict[str, Any]]
    response_text: str
    model: str
    started_at: datetime
    seconds: float


class Decision(BaseModel):
    action: Literal['confirm', 'change']
    new_verdict: str | None
    reason: str
    decided_at: datetime


class Appeal(BaseModel):
    id: str
    evaluation_id: str
    criterion_id: str
    comment: str
    created_at: datetime
    status: Literal['open', 'resolved']
    decision: Decision | None


class FinalItem(BaseModel):
    criterion_id: str
    original_verdict: str
    decision: Decision | None
    final_verdict: str


class FinalResult(BaseModel):
    items: list[FinalItem]
    score: Score


class EvaluationView(BaseModel):
    evaluation: Evaluation
    checklist: Checklist
    appeals: list[Appeal]
    final: FinalResult


class Job(BaseModel):
    id: str
    state: Literal['running', 'finished']
    total: int
    done: int
    failed: dict[str, str]
    evaluation_ids: list[str]


class ApiError(BaseModel):
    error: str
    details: list[str] | None


class BatchRequest(BaseModel):
    group_id: str
    conversation_ids: list[str]
    checklist_id: str | None = None
    profile: str | None = None
    mode: Mode | None = None
    k: int | None = None
    transcript_source: str | None = None  # None = 'api', the organizer transcript


class AsrQuality(BaseModel):
    """One provider's benchmark row from `data/asr/quality.json`; every field may be absent."""

    label: str | None = None
    cer_vs_freedomspeech: float | None = None
    cer_vs_api: float | None = None
    speaker_turns: float | None = None
    seconds_per_min: float | None = None
    diarized: bool | None = None
    gold_hits: int | None = None  # evaluator verdicts on this transcript that match the gold labels
    gold_total: int | None = None
    manual_score: float | None = None
    notes: str | None = None


class TranscriptSourceInfo(BaseModel):
    source: str
    label: str
    kind: Literal['api', 'asr', 'custom']
    available: bool
    created_at: datetime | None = None
    provider_hosting: str | None = None
    quality: AsrQuality | None = None


class TranscribeRequest(BaseModel):
    group_id: str
    provider: str


class CustomTranscriptRequest(BaseModel):
    group_id: str
    text: str


class AppealCreate(BaseModel):
    evaluation_id: str
    criterion_id: str
    comment: str


class DecisionCreate(BaseModel):
    action: Literal['confirm', 'change']
    new_verdict: str | None = None
    reason: str


class AppealQueueItem(BaseModel):
    appeal: Appeal
    evaluation_id: str
    conversation_id: str
    item: Item
    criterion: Criterion


class DecisionResult(BaseModel):
    appeal: Appeal
    final: FinalResult


class BreakdownRow(BaseModel):
    key: str
    count: int
    mean_total: float | None


class CriterionStat(BaseModel):
    criterion_id: str
    title: str
    applicable: int
    yes: int
    no: int
    na: int
    mean_pct: float | None


class HistogramBin(BaseModel):
    label: str
    count: int


class GroupAnalytics(BaseModel):
    group_id: str
    dialogs: int
    evaluated: int
    mean_total: float | None
    gross_error_count: int
    gross_error_ids: list[str]
    by_channel: list[BreakdownRow]
    by_language: list[BreakdownRow]
    criteria: list[CriterionStat]
    histogram: list[HistogramBin]


ALL_MODELS: list[type[BaseModel]] = [
    Turn, Record, MaskedToken, DialogEvent, DialogFacts, Usage, EvaluationSummary, ConversationSummary, ScaleStep, Section, Criterion,
    Checklist, ChecklistSummary, Item, ScoreItem, SectionScore, Score, Evaluation, RawCall,
    Decision, Appeal, FinalItem, FinalResult, EvaluationView, Job, ApiError, BatchRequest,
    AppealCreate, DecisionCreate, AppealQueueItem, DecisionResult, AsrQuality, TranscriptSourceInfo, TranscribeRequest,
    CustomTranscriptRequest,
    BreakdownRow, CriterionStat, HistogramBin, GroupAnalytics,
]
