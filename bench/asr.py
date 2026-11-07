"""ASR benchmark: transcribe the DEV calls with several providers, mask, audit, compare and score downstream.

    python -m bench.asr [--providers a,b] [--calls p4-ru-001,...] [--profile NAME] [--reuse-raw] [--no-score]

Reads audio from data/audio/<cid>.mp3 (else fetches it from the record's audio_url). Writes:
  data/asr/raw/<provider>/<cid>.json        raw ASR result, UNMASKED, gitignored
  data/calls/<provider>.dev.json            masked Records in the organizer API shape, seeded by the app as transcript sources
                                            (the live FreedomSpeech run goes to bench/asr/freedomspeech-live.dev.json)
  bench/asr/transcripts/<provider>/<cid>.md masked, readable `[N] (mm:ss) role: text` for the manual comparison
  bench/asr/summary.md, data/asr/metrics.json, data/asr/quality.json

CER/WER are AGREEMENT between two transcripts, not accuracy: there is no ground truth. The one objective number is the
downstream score: verdict hits of the evaluator on that transcript against the gold labels.
No file is written for a call whose masked output fails the PII audit.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

import server  # noqa: F401  (loads .env)
from server.asr.audio import fetch_call_audio
from server.asr.base import AsrError, AsrResult
from server.asr.providers import AsrProvider, load_asr_providers, transcribe
from server.asr.to_record import asr_to_record, find_leaks
from server.config import Profile, default_profile, load_profiles
from server.dataset import normalize_response
from server.evaluator import evaluate
from server.http import new_session
from server.llm.client import LLMClient, make_client
from server.models import Record

from bench.prefill import load_gold
from bench.sets import checklist_for

ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = ROOT / 'data' / 'audio'
RAW_DIR = ROOT / 'data' / 'asr' / 'raw'
CALLS_DIR = ROOT / 'data' / 'calls'
TRANSCRIPTS_DIR = ROOT / 'bench' / 'asr' / 'transcripts'
SUMMARY = ROOT / 'bench' / 'asr' / 'summary.md'
METRICS = ROOT / 'data' / 'asr' / 'metrics.json'
QUALITY = ROOT / 'data' / 'asr' / 'quality.json'
API_CACHE = ROOT / 'data' / 'cache' / 'DEV.json'
FREEDOMSPEECH_REF = CALLS_DIR / 'freedomspeech.dev.json'  # Batyrkhan's hand-checked version: never overwritten here

MASK_RE = re.compile(r'\[[^\]]*скрыт[^\]]*\]')
DIGIT_RUN = re.compile(r'\d{4,}')
EVAL_ATTEMPTS = 3


# ---------------------------------------------------------------- metrics

def normalize(text: str) -> str:
    """Lowercase, ё->е, drop mask tokens and punctuation, collapse whitespace."""
    text = MASK_RE.sub(' ', text.lower().replace('ё', 'е'))
    text = re.sub(r'[^\w\s]|_', ' ', text)
    return ' '.join(text.split())


def edit_distance(a: Sequence, b: Sequence) -> int:
    """Levenshtein distance (Myers/Hyyrö bit-parallel): fast enough for 10 minute calls in pure Python."""
    if len(a) < len(b):
        a, b = b, a
    m = len(b)
    if m == 0:
        return len(a)
    peq: dict[Any, int] = {}
    for i, c in enumerate(b):
        peq[c] = peq.get(c, 0) | (1 << i)
    mask = (1 << m) - 1
    high = 1 << (m - 1)
    pv, mv, score = mask, 0, m
    for c in a:
        eq = peq.get(c, 0)
        xv = eq | mv
        xh = ((((eq & pv) + pv) ^ pv) | eq) & mask
        ph = (mv | ~(xh | pv)) & mask
        mh = pv & xh
        if ph & high:
            score += 1
        elif mh & high:
            score -= 1
        ph = ((ph << 1) | 1) & mask
        mh = (mh << 1) & mask
        pv = (mh | ~(xv | ph)) & mask
        mv = ph & xv
    return score


def cer(ref: str, hyp: str) -> float | None:
    ref, hyp = normalize(ref), normalize(hyp)
    return edit_distance(ref, hyp) / len(ref) if ref else None


def wer(ref: str, hyp: str) -> float | None:
    ref_w, hyp_w = normalize(ref).split(), normalize(hyp).split()
    return edit_distance(ref_w, hyp_w) / len(ref_w) if ref_w else None


def plain_text(record: Record) -> str:
    return ' '.join(t.text for t in record.transcript if t.speaker != 'system')


# ---------------------------------------------------------------- PII audit

async def llm_audit(llm: LLMClient, record: Record) -> list[dict]:
    """Independent re-run of the leak finder on the final masked transcript: anything it finds fails the audit."""
    return await find_leaks(llm, record.transcript)


def digit_runs(record: Record) -> list[int]:
    return [t.idx for t in record.transcript if DIGIT_RUN.search(t.text)]


# ---------------------------------------------------------------- rendering

def out_name(provider: str) -> str:
    """`freedomspeech` is Batyrkhan's hand-checked file; the live run of the provider is kept beside it."""
    return 'freedomspeech-live' if provider == 'freedomspeech' else provider


def calls_file(provider: str) -> Path:
    """Masked records the app seeds as transcript sources. The live FreedomSpeech run is benchmark-only: the UI
    already shows Batyrkhan's hand-checked FreedomSpeech file, so the live copy stays out of `data/calls`."""
    base = ROOT / 'bench' / 'asr' if provider == 'freedomspeech' else CALLS_DIR
    return base / f'{out_name(provider)}.dev.json'


def api_payload(records: list[Record], name: str) -> dict:
    return {
        'error': '',
        'isSuccess': True,
        'data': {
            'dataset_group_id': f'DEV-CALLS-{name.upper()}',
            'total_records': len(records),
            'records': [
                {
                    'conversation_id': r.conversation_id,
                    'channel': r.channel,
                    'language': r.language,
                    'transcript': [{'timestamp': t.timestamp, 'speaker': t.speaker, 'text': t.text} for t in r.transcript],
                    # The audio URL carries the organizers' signed `sig=`: a secret that must not reach the public repo.
                    'audio_url': re.sub(r'(sig=)[^&]+', r'\1REDACTED', r.audio_url) if r.audio_url else r.audio_url,
                }
                for r in records
            ],
        },
    }


def render_review(record: Record, label: str) -> str:
    lines = [
        f'# {record.conversation_id} · {label} · маскированный транскрипт',
        '',
        'Формат: `[N] (мм:сс) роль: текст`. Время считается от начала диалога с учётом паузы записи. '
        'Персональные данные замаскированы; ASR-ошибки намеренно не исправлены.',
        '',
    ]
    for t in record.transcript:
        stamp = f'{int(t.offset_s) // 60:02d}:{int(t.offset_s) % 60:02d}' if t.offset_s is not None else '--:--'
        lines.append(f'[{t.idx}] ({stamp}) {t.speaker}: {t.text}')
    return '\n'.join(lines) + '\n'


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')


# ---------------------------------------------------------------- run

def load_api_records() -> dict[str, Record]:
    records = normalize_response(json.loads(API_CACHE.read_text(encoding='utf-8')), 'DEV')
    return {r.conversation_id: r for r in records}


def load_reference_records(path: Path) -> dict[str, Record]:
    if not path.exists():
        return {}
    return {r.conversation_id: r for r in normalize_response(json.loads(path.read_text(encoding='utf-8')), 'DEV')}


async def get_audio(record: Record) -> bytes:
    path = AUDIO_DIR / f'{record.conversation_id}.mp3'
    if path.exists():
        return path.read_bytes()
    audio = await fetch_call_audio(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(audio)
    return audio


OPENROUTER_BUDGET_USD = 0.60  # abort a paid OpenRouter provider when the key's spend grew by more than this during the run


def is_openrouter(provider: AsrProvider) -> bool:
    return 'openrouter.ai' in (provider.resolved_base_url() or '')


async def openrouter_spend(provider: AsrProvider) -> float:
    """Spend of the provider's OpenRouter key so far (GET /key). AsrError when it cannot be read: a paid call without a
    working budget guard is not made."""
    last = ''
    for _ in range(4):
        try:
            resp = await new_session().get(
                f'{provider.resolved_base_url()}/key',
                headers={'Authorization': f'Bearer {provider.api_key()}', 'User-Agent': 'Mozilla/5.0 (cqa)'},
                timeout=60,
            )
            return float(resp.json()['data']['budgets'][0]['spend_usd'])
        except Exception as exc:  # noqa: BLE001
            last = type(exc).__name__
            await asyncio.sleep(5)
    raise AsrError(f'не удалось прочитать расход ключа OpenRouter ({last})')


async def run_asr(
    provider: AsrProvider, calls: dict[str, Record], audio: dict[str, bytes], reuse_raw: bool
) -> tuple[dict[str, AsrResult], dict[str, str]]:
    results: dict[str, AsrResult] = {}
    errors: dict[str, str] = {}
    paid = is_openrouter(provider)
    spend0 = None
    if paid and not (reuse_raw and all((RAW_DIR / provider.name / f'{c}.json').exists() for c in calls)):
        try:
            spend0 = await openrouter_spend(provider)
        except AsrError as exc:
            print(f'  {provider.name}: {exc}: провайдер пропущен', file=sys.stderr)
            return results, {cid: str(exc) for cid in calls}
    for cid in calls:
        if spend0 is not None and not (reuse_raw and (RAW_DIR / provider.name / f'{cid}.json').exists()):
            try:
                spend = await openrouter_spend(provider)
            except AsrError as exc:
                errors[cid] = str(exc)
                print(f'  {provider.name} {cid}: {exc}: звонок пропущен', file=sys.stderr)
                continue
            if spend - spend0 > OPENROUTER_BUDGET_USD:
                errors[cid] = f'бюджет OpenRouter превышен: +${spend - spend0:.2f} за прогон (предел ${OPENROUTER_BUDGET_USD:.2f})'
                print(f'  {provider.name} {cid}: {errors[cid]}', file=sys.stderr)
                break
        raw = RAW_DIR / provider.name / f'{cid}.json'
        if reuse_raw and raw.exists():
            results[cid] = AsrResult.model_validate_json(raw.read_text(encoding='utf-8'))
            continue
        try:
            if cid not in audio:
                audio[cid] = await get_audio(calls[cid])
            result = await transcribe(provider, audio[cid], f'{cid}.mp3')
        except AsrError as exc:
            errors[cid] = str(exc)
            print(f'  {provider.name} {cid}: ОШИБКА {exc}', file=sys.stderr)
            continue
        write_text(raw, result.model_dump_json(indent=1))
        results[cid] = result
        print(f'  {provider.name} {cid}: {result.seconds:.1f} s, сегментов {len(result.segments)}, diarized={result.diarized}')
    if spend0 is not None:
        try:
            spend = await openrouter_spend(provider)
            print(f'  {provider.name}: расход ключа OpenRouter за прогон ≈ ${spend - spend0:.3f} (предел ${OPENROUTER_BUDGET_USD:.2f})')
        except AsrError as exc:
            print(f'  {provider.name}: {exc}', file=sys.stderr)
    return results, errors


async def mask_all(
    provider: AsrProvider, results: dict[str, AsrResult], calls: dict[str, Record], profile: Profile, llm: LLMClient
) -> tuple[dict[str, Record], dict[str, str]]:
    sem = asyncio.Semaphore(3)

    async def one(cid: str) -> tuple[str, Record | str]:
        async with sem:
            try:
                return cid, await asr_to_record(results[cid], calls[cid], profile, llm)
            except Exception as exc:  # noqa: BLE001
                return cid, f'{type(exc).__name__}: {exc}'

    records: dict[str, Record] = {}
    errors: dict[str, str] = {}
    for cid, out in await asyncio.gather(*(one(c) for c in results)):
        if isinstance(out, Record):
            records[cid] = out
        else:
            errors[cid] = out
            print(f'  {provider.name} {cid}: разметка не удалась: {out}', file=sys.stderr)
    return records, errors


async def audit_all(
    provider: str, records: dict[str, Record], llm: LLMClient, show: bool
) -> dict[str, dict]:
    sem = asyncio.Semaphore(3)

    async def one(cid: str, record: Record) -> tuple[str, dict]:
        digits = digit_runs(record)
        try:
            async with sem:
                findings = await llm_audit(llm, record)
            error = None
        except AsrError as exc:
            findings, error = [], str(exc)
        return cid, {'digit_runs': digits, 'findings': findings, 'error': error}

    audit = dict(await asyncio.gather(*(one(c, r) for c, r in records.items())))
    for cid, a in audit.items():
        kinds = sorted({f['kind'] for f in a['findings']})
        status = 'OK' if not (a['digit_runs'] or a['findings'] or a['error']) else 'FAIL'
        print(
            f'  аудит ПДн {provider} {cid}: {status}; цифровых серий 4+: {len(a["digit_runs"])}; '
            f'LLM-находок: {len(a["findings"])} {kinds or ""}' + (f'; ошибка: {a["error"]}' if a['error'] else '')
        )
        if show:
            for f in a['findings']:
                print(f'    [{f["idx"]}] {f["kind"]}: {f["quote"]}')
    return audit


def audit_passed(audit: dict[str, dict]) -> bool:
    return all(not (a['digit_runs'] or a['findings'] or a['error']) for a in audit.values())


def call_metrics(
    result: AsrResult, record: Record, api: Record, fs: Record | None, audio_s: float | None
) -> dict[str, Any]:
    hyp = plain_text(record)
    turns = [t.speaker for t in record.transcript if t.speaker != 'system']
    m: dict[str, Any] = {
        'seconds': round(result.seconds, 2),
        'audio_s': round(audio_s, 1) if audio_s else None,
        'seconds_per_min': round(result.seconds / (audio_s / 60), 2) if audio_s else None,
        'diarized': result.diarized,
        'turns': len(turns),
        'operator_turns': turns.count('operator'),
        'client_turns': turns.count('client'),
        'segments': len(result.segments),
    }
    for key, ref in (('api', api), ('freedomspeech', fs)):
        text = plain_text(ref) if ref else None
        m[f'cer_vs_{key}'] = round(cer(text, hyp), 4) if text and normalize(text) else None
        m[f'wer_vs_{key}'] = round(wer(text, hyp), 4) if text and normalize(text) else None
    return m


async def score_source(
    source: str, records: dict[str, Record], gold: dict[str, dict[str, str]], profile: Profile, llm: LLMClient
) -> dict[str, dict]:
    sem = asyncio.Semaphore(4)

    async def one(cid: str, record: Record) -> tuple[str, dict]:
        checklist = checklist_for(record)
        wanted = gold.get(cid, {})
        failure = ''
        for attempt in range(EVAL_ATTEMPTS):
            try:
                async with sem:
                    evaluation, _ = await evaluate(record, checklist, profile=profile, mode='per_criterion', k=1, llm=llm)
            except Exception as exc:  # noqa: BLE001  network flakes must not abort the benchmark
                failure = f'{type(exc).__name__}: {str(exc)[:120]}'
                await asyncio.sleep(2 * (attempt + 1))
                continue
            verdicts = {it.criterion_id: it.verdict for it in evaluation.items}
            hits = sum(1 for crit, v in wanted.items() if verdicts.get(crit) == v)
            return cid, {'hits': hits, 'total': len(wanted), 'error': None}
        print(f'  оценка {source} {cid} не удалась: {failure}', file=sys.stderr)
        return cid, {'hits': 0, 'total': len(wanted), 'error': failure}

    return dict(await asyncio.gather(*(one(c, r) for c, r in records.items())))


# ---------------------------------------------------------------- reporting

def _mean(values: list[float | None]) -> float | None:
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def _fmt(value: float | None, digits: int = 3) -> str:
    return '—' if value is None else f'{value:.{digits}f}'


def build_summary(store: dict, call_ids: list[str]) -> str:
    providers = store['providers']
    downstream = store.get('downstream', {})
    out = [
        '# ASR benchmark: сводка',
        '',
        f'Сформировано: {store.get("generated", "")}. Звонки: {", ".join(call_ids)}.',
        '',
        '**CER/WER показывают согласие двух транскриптов, а не точность распознавания: эталона нет.** '
        'Оба эталона — тоже ASR: транскрипт API организаторов (`api`, плохой ASR) и FreedomSpeech, проверенный руками '
        '(`data/calls/freedomspeech.dev.json`). Текст до сравнения: нижний регистр, без пунктуации и меток маскирования. '
        'Единственная объективная метрика — «попадания gold»: сколько вердиктов оценщика (`h200-gemma`, per_criterion) '
        'на этом транскрипте совпало с gold-разметкой (gold размечали по транскрипту API и FreedomSpeech).',
        '',
        'Маскированные транскрипты для ручного сравнения: `bench/asr/transcripts/<провайдер>/<звонок>.md`.',
        '',
    ]
    header = (
        '| Провайдер | Сек | Сек/мин аудио | Диаризация | Реплик (опер./клиент) | '
        'CER vs FS | WER vs FS | CER vs API | WER vs API | Gold-попадания |'
    )
    sep = '|---|---:|---:|:---:|---:|---:|---:|---:|---:|---:|'
    for cid in call_ids:
        out += [f'## {cid}', '', header, sep]
        for name, p in providers.items():
            m = p['calls'].get(cid)
            if not m:
                out.append(f'| {name} | нет результата | | | | | | | | |')
                continue
            d = downstream.get(out_name(name), {}).get(cid)
            hits = f'{d["hits"]}/{d["total"]}' if d else '—'
            out.append(
                f'| {name} | {m["seconds"]:.1f} | {_fmt(m["seconds_per_min"], 2)} | {"да" if m["diarized"] else "нет"} | '
                f'{m["turns"]} ({m["operator_turns"]}/{m["client_turns"]}) | {_fmt(m["cer_vs_freedomspeech"])} | '
                f'{_fmt(m["wer_vs_freedomspeech"])} | {_fmt(m["cer_vs_api"])} | {_fmt(m["wer_vs_api"])} | {hits} |'
            )
        out.append('')
    out += ['## Средние по звонкам', '', header, sep]
    for name, p in providers.items():
        ms = list(p['calls'].values())
        if not ms:
            continue
        ds = [downstream.get(out_name(name), {}).get(c) for c in p['calls']]
        hits = sum(d['hits'] for d in ds if d)
        total = sum(d['total'] for d in ds if d)
        out.append(
            f'| {name} | {_mean([m["seconds"] for m in ms]):.1f} | {_fmt(_mean([m["seconds_per_min"] for m in ms]), 2)} | '
            f'{"да" if any(m["diarized"] for m in ms) else "нет"} | '
            f'{_mean([m["turns"] for m in ms]):.1f} ({_mean([m["operator_turns"] for m in ms]):.1f}/'
            f'{_mean([m["client_turns"] for m in ms]):.1f}) | {_fmt(_mean([m["cer_vs_freedomspeech"] for m in ms]))} | '
            f'{_fmt(_mean([m["wer_vs_freedomspeech"] for m in ms]))} | {_fmt(_mean([m["cer_vs_api"] for m in ms]))} | '
            f'{_fmt(_mean([m["wer_vs_api"] for m in ms]))} | {f"{hits}/{total}" if total else "—"} |'
        )
    out += ['', '## Попадания gold по источнику транскрипта', '']
    calls_shown = call_ids
    out += ['| Источник | ' + ' | '.join(calls_shown) + ' | Всего |', '|---|' + '---:|' * (len(calls_shown) + 1)]
    for source, per_call in downstream.items():
        cells = []
        for cid in calls_shown:
            d = per_call.get(cid)
            cells.append('—' if not d else f'{d["hits"]}/{d["total"]}' + (' (сбой)' if d.get('error') else ''))
        total_hits = sum(d['hits'] for d in per_call.values())
        total = sum(d['total'] for d in per_call.values())
        out.append(f'| {source} | ' + ' | '.join(cells) + f' | **{total_hits}/{total}** |')
    failed = store.get('audit_failed', {})
    if failed:
        out += ['', '## Не прошли аудит ПДн (файлы не записаны)', '']
        out += [f'- {name}: {", ".join(cids)}' for name, cids in failed.items()]
    out.append('')
    return '\n'.join(out)


def build_quality(store: dict, providers: dict[str, AsrProvider]) -> dict:
    existing = json.loads(QUALITY.read_text(encoding='utf-8')) if QUALITY.exists() else {}
    quality = dict(existing)
    for name, p in store['providers'].items():
        ms = list(p['calls'].values())
        if not ms:
            continue
        old = existing.get(name, {})
        ds = [store.get('downstream', {}).get(out_name(name), {}).get(c) for c in p['calls']]
        hits = sum(d['hits'] for d in ds if d)
        total = sum(d['total'] for d in ds if d)
        note = (
            f'Автоматически: согласие с эталонами, не точность (эталона нет). '
            f'Gold-попадания оценщика: {hits}/{total}. Средние по {len(ms)} звонкам.'
            if total
            else 'Автоматически: согласие с эталонами, не точность (эталона нет).'
        )
        quality[name] = {
            'label': providers[name].label if name in providers else old.get('label', name),
            # Agreement of FreedomSpeech with its own hand-checked version says nothing; keep it out of the badge.
            'cer_vs_freedomspeech': None if name == 'freedomspeech' else _round(_mean([m['cer_vs_freedomspeech'] for m in ms])),
            'cer_vs_api': _round(_mean([m['cer_vs_api'] for m in ms])),
            'speaker_turns': _round(_mean([m['turns'] for m in ms]), 1),
            'seconds_per_min': _round(_mean([m['seconds_per_min'] for m in ms]), 2),
            'diarized': any(m['diarized'] for m in ms),
            'gold_hits': hits if total else None,
            'gold_total': total or None,
            'manual_score': old.get('manual_score'),
            'notes': note,
        }
    return quality


def _round(value: float | None, digits: int = 4) -> float | None:
    return None if value is None else round(value, digits)


async def main_async(args: argparse.Namespace) -> int:
    providers = load_asr_providers()
    names = [n.strip() for n in args.providers.split(',')] if args.providers else [n for n, p in providers.items() if p.enabled]
    unknown = [n for n in names if n not in providers]
    if unknown:
        print(f'неизвестные провайдеры: {unknown}; есть: {list(providers)}', file=sys.stderr)
        return 2
    api = load_api_records()
    call_ids = [c.strip() for c in args.calls.split(',')] if args.calls else sorted(
        cid for cid, r in api.items() if r.channel == 'voice call'
    )
    missing = [c for c in call_ids if c not in api]
    if missing:
        print(f'нет звонков в data/cache/DEV.json: {missing}', file=sys.stderr)
        return 2
    calls = {cid: api[cid] for cid in call_ids}
    fs_ref = load_reference_records(FREEDOMSPEECH_REF)
    profile = load_profiles()[args.profile] if args.profile else default_profile()
    llm = make_client(profile)
    print(f'LLM-профиль: {profile.name}; провайдеры: {names}; звонки: {call_ids}')

    store: dict = json.loads(METRICS.read_text(encoding='utf-8')) if METRICS.exists() else {}
    store.setdefault('providers', {})
    store.setdefault('downstream', {})
    store.setdefault('audit_failed', {})

    todo = []
    for n in names:
        if not providers[n].enabled and not args.providers:
            continue
        if not providers[n].configured():
            print(f'{n}: пропущен, не настроен ({", ".join(providers[n].missing_env())})', file=sys.stderr)
            continue
        todo.append(n)

    audio: dict[str, bytes] = {}
    if not args.reuse_raw:
        for cid, rec in calls.items():
            audio[cid] = await get_audio(rec)

    masked: dict[str, dict[str, Record]] = {}  # provider -> cid -> record, only audited and clean
    failed_audit = False
    for name in todo:
        provider = providers[name]
        print(f'== {name}: распознавание')
        results, asr_errors = await run_asr(provider, calls, audio, args.reuse_raw)
        if not results:
            print(f'{name}: ни один звонок не распознан', file=sys.stderr)
            continue
        print(f'== {name}: маскирование')
        records, mask_errors = await mask_all(provider, results, calls, profile, llm)
        print(f'== {name}: аудит ПДн')
        audit = await audit_all(name, records, llm, args.show_findings)
        bad = sorted(cid for cid, a in audit.items() if a['digit_runs'] or a['findings'] or a['error'])
        if bad:
            failed_audit = True
            store['audit_failed'][name] = bad
            print(f'{name}: АУДИТ НЕ ПРОЙДЕН для {bad}: файлы этих звонков не записаны', file=sys.stderr)
        else:
            store['audit_failed'].pop(name, None)
        good = {cid: rec for cid, rec in records.items() if cid not in bad}
        if not good:
            continue
        print(f'{name}: аудит ПДн пройден ({len(good)} из {len(records)} звонков)')
        # only calls that passed the audit are written; calls kept from earlier runs stay in the file
        oname = out_name(name)
        merged = {**load_reference_records(calls_file(name)), **good}
        for cid in bad:
            merged.pop(cid, None)
        masked[name] = merged
        ordered = [merged[c] for c in call_ids if c in merged] + [r for c, r in merged.items() if c not in call_ids]
        payload = api_payload(ordered, oname)
        normalize_response(payload, 'DEV')  # must stay readable by the app
        write_text(calls_file(name), json.dumps(payload, ensure_ascii=False, indent=1) + '\n')
        for cid, rec in good.items():
            write_text(TRANSCRIPTS_DIR / oname / f'{cid}.md', render_review(rec, provider.label))
        previous = store['providers'].get(name, {}).get('calls', {})
        per_call = {c: m for c, m in previous.items() if c in merged and c not in good}
        for cid, rec in good.items():
            per_call[cid] = call_metrics(results[cid], rec, api[cid], fs_ref.get(cid), results[cid].duration_s)
        store['providers'][name] = {
            'label': provider.label,
            'calls': {c: per_call[c] for c in sorted(per_call)},
            'errors': {**asr_errors, **mask_errors},
        }

    if not args.no_score:
        gold = load_gold()
        gold = {cid: g for cid, g in gold.items() if cid in calls}
        total = sum(len(g) for g in gold.values())
        print(f'== оценка по транскриптам; gold-вердиктов: {total}')
        sources: dict[str, dict[str, Record]] = {
            'api': calls,
            'freedomspeech': {c: r for c, r in fs_ref.items() if c in calls},
        }
        for name, records in masked.items():
            sources[out_name(name)] = records
        for source, recs in sources.items():
            if not recs:
                continue
            store['downstream'][source] = await score_source(source, recs, gold, profile, llm)
            d = store['downstream'][source]
            print(f'  {source}: {sum(x["hits"] for x in d.values())}/{sum(x["total"] for x in d.values())}')

    store['generated'] = date.today().isoformat()
    write_text(METRICS, json.dumps(store, ensure_ascii=False, indent=1) + '\n')
    # a partial run merges into the stored results: the summary always shows every provider and call seen so far
    all_cids = sorted({c for p in store['providers'].values() for c in p['calls']} | set(call_ids))
    write_text(SUMMARY, build_summary(store, all_cids))
    write_text(QUALITY, json.dumps(build_quality(store, providers), ensure_ascii=False, indent=1) + '\n')
    print(f'записано: {SUMMARY.relative_to(ROOT)}, {QUALITY.relative_to(ROOT)}, {METRICS.relative_to(ROOT)}')
    return 1 if failed_audit else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--providers', help='comma-separated provider names from config/asr.toml (default: all enabled)')
    parser.add_argument('--calls', help='comma-separated call ids (default: every voice call of DEV)')
    parser.add_argument('--profile', help='LLM profile for masking, audit and scoring (default: LLM_PROFILE)')
    parser.add_argument('--reuse-raw', action='store_true', help='use data/asr/raw instead of calling the ASR again')
    parser.add_argument('--no-score', action='store_true', help='skip the downstream evaluator scoring')
    parser.add_argument('--show-findings', action='store_true', help='print the quotes of PII audit findings (local console only)')
    return asyncio.run(main_async(parser.parse_args(argv)))


if __name__ == '__main__':
    raise SystemExit(main())
