"""Synthetic call evaluation set with exact ground truth: scripts -> TTS -> telephony degradation -> ASR -> judge.

    python -m bench.synth_calls scripts [--force] [--only ID ...]
    python -m bench.synth_calls tts [--only ID ...]
    python -m bench.synth_calls asr [--providers P ...] [--only ID ...] [--no-ablation]
    python -m bench.synth_calls judge [--providers P ...]
    python -m bench.synth_calls report

Everything here is SYNTHETIC: dialogs are written by an LLM from a scenario matrix (invented names, no real PII), read out by
one TTS voice family and run through a telephony chain. The script text is the exact reference for CER/WER, speaker
attribution and the judge. Audio and raw ASR output stay in `data/asr/synthetic/` (git-ignored); the committed artefacts are
`bench/asr/synthetic/scripts.json`, `results.json` and `bench/asr/synthetic.md`.
"""

from __future__ import annotations

import argparse
import array
import asyncio
import itertools
import json
import math
import random
import re
import statistics
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import server  # noqa: F401  (loads .env)
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env')

from server.asr.base import AsrError, AsrResult  # noqa: E402
from server.asr.providers import AsrProvider, load_asr_providers, transcribe  # noqa: E402
from server.asr.to_record import asr_to_record  # noqa: E402
from server.config import default_profile, load_profiles  # noqa: E402
from server.evaluator import evaluate  # noqa: E402
from server.http import new_session  # noqa: E402
from server.llm.client import make_client  # noqa: E402
from server.models import Record, Turn  # noqa: E402

from bench.asr import cer, edit_distance, normalize, wer  # noqa: E402
from bench.sets import checklist_for  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / 'bench' / 'asr' / 'synthetic' / 'scripts.json'
RESULTS = ROOT / 'bench' / 'asr' / 'synthetic' / 'results.json'
REPORT = ROOT / 'bench' / 'asr' / 'synthetic.md'
DATA = ROOT / 'data' / 'asr' / 'synthetic'
TTS_DIR = DATA / 'tts'  # one WAV per turn, as returned by the TTS
MASTER_DIR = DATA / 'master'  # clean 24 kHz concatenation
TIMING_DIR = DATA / 'timings'
DEGRADED_DIR = DATA / 'degraded'  # telephony chain, 16 kHz mono MP3
CLEAN_DIR = DATA / 'clean'  # ablation: 16 kHz mono MP3 without the chain
RAW_DIR = DATA / 'raw'  # raw ASR results: raw/<variant>/<provider>/<id>.json
JUDGE_DIR = DATA / 'judge'

SEED = 20261108
TTS_MODEL = 'alemai/k2-fsa/OmniVoice'
TTS_RATE = 24000
LANG_NAMES = {'RU': 'Russian', 'KZ': 'Kazakh', 'EN': 'English'}
RU_ONLY_PROVIDERS = {'h200-gigaam-v3', 'h200-t-one'}  # documented Russian-only engines: run on RU dialogs only
SKIP_PROVIDERS = {'h200-whisperx-kk'}  # same endpoint as h200-whisperx, which receives `kk` for KZ exactly like the server does
ABLATION_N = 8

# ---------------------------------------------------------------- scenario matrix

TOPICS: dict[str, tuple[str, bool]] = {
    # id: (what the client wants, call needs identification before account-specific details)
    'withdrawal': ('the client asks why a withdrawal of money from their brokerage account has not arrived yet', True),
    'block': ('the client cannot trade: the account or the login was blocked after several wrong password attempts', True),
    'tariff': ('the client asks what the difference between two commission tariff plans is and which one suits a beginner', False),
    'documents': ('the client needs a brokerage account statement for the tax office and asks how to get it', True),
    'app_login': ('the client cannot log in to the mobile app after changing the phone and asks how to restore access', True),
    'open_account': ('the client wants to open a brokerage account and asks which documents and steps are needed', False),
    'deposit': ('the client asks how to top up the brokerage account from a bank card or by transfer and how long it takes', False),
    'complaint': ('the client complains that a buy order was not executed and wants to know why', True),
}

PROFILES: dict[str, dict[str, Any]] = {
    'clean': {
        'instr': 'The operator is exemplary: greets the client in the client\'s language and introduces themself by name and company in the first reply; asks one or two clarifying questions before answering; is polite and empathetic; gives a correct, complete answer with a concrete next step; ends with a short recap or an offer of further help and a farewell.',
        'c01': 'Да', 'c02': 'Да', 'c05': 'Да', 'c07': 'Да', 'c08': 'Нет', 'c04': 'high', 'c06': 'high',
    },
    'no_greeting': {
        'instr': 'The operator NEVER greets and NEVER introduces themself or the company: the very first operator reply goes straight to the matter ("Слушаю.", "Yes, what is it?"). Otherwise the operator is correct, polite, solves the problem and ends with a farewell. The call has no IVR line.',
        'c01': 'Нет', 'c02': 'Да', 'c05': 'Да', 'c07': 'Да', 'c08': 'Нет', 'c04': 'high', 'c06': 'high',
    },
    'no_ident': {
        'instr': 'The operator greets and introduces themself, but then reads out account-specific details (balance, order status, amount and date of the withdrawal) WITHOUT ever asking the client to confirm identity (no full name, no code word, no passport digits, no verification of any kind). Otherwise polite, ends with a farewell.',
        'c01': 'Да', 'c02': 'Да', 'c03': 'Нет', 'c05': 'Да', 'c07': 'Да', 'c08': 'Да', 'c04': 'high', 'c06': 'any',
    },
    'rude': {
        'instr': 'The operator\'s FIRST reply is a normal polite greeting with name and company (for example "Здравствуйте, меня зовут Игорь, Фридом Брокер" in the dialog language) - that is mandatory. After that the operator is impatient, cold and dismissive: sighs, interrupts, tells the client to "read the instructions yourself", shows no understanding of the client\'s inconvenience and does not acknowledge the problem. NO insults and no profanity. Still answers briefly and says goodbye curtly.',
        'c01': 'Да', 'c02': 'any', 'c05': 'Нет', 'c07': 'any', 'c08': 'Нет', 'c04': 'any', 'c06': 'any',
    },
    'insult': {
        'instr': 'The operator greets and introduces themself, then loses patience and openly insults the client at least twice (calls the client stupid / an idiot / says "you understand nothing"). The client is upset. The call ends with the operator hanging up in an irritated way.',
        'c01': 'Да', 'c02': 'any', 'c05': 'Нет', 'c07': 'any', 'c08': 'Да', 'c04': 'any', 'c06': 'any',
    },
    'no_close': {
        'instr': 'The operator greets, introduces themself and helps correctly, but the call has NO closing: the operator never recaps, never offers further help and never says goodbye. The dialog ends right after the client says thanks, or right after the operator\'s last piece of information, with the last turn being the client\'s "thank you" and nothing after it.',
        'c01': 'Да', 'c02': 'Да', 'c05': 'Да', 'c07': 'Нет', 'c08': 'Нет', 'c04': 'high', 'c06': 'any',
    },
    'wrong_info': {
        'instr': 'The operator greets, introduces themself, is polite and ends with a farewell, BUT the substance of the advice is clearly wrong or evasive: invents wrong deadlines, wrong fees or wrong steps (e.g. says it takes thirty days, or that the fee is fifty percent), and never solves the client\'s actual question; the client leaves without a usable answer.',
        'c01': 'Да', 'c02': 'any', 'c05': 'Да', 'c07': 'Да', 'c08': 'Нет', 'c04': 'low', 'c06': 'any',
    },
    'combo_bad': {
        'instr': 'The operator does NOT greet or introduce themself, is rude and dismissive to the client (no insults), gives a thin answer, and ends the call abruptly with no recap, no offer of help and no goodbye (the last turn is the client\'s). The call has no IVR line.',
        'c01': 'Нет', 'c02': 'any', 'c05': 'Нет', 'c07': 'Нет', 'c08': 'Нет', 'c04': 'any', 'c06': 'any',
    },
}

# (language, profile, topic): fixed so that reruns and the report are comparable
MATRIX: list[tuple[str, str, str]] = (
    [('RU', 'clean', t) for t in ('tariff', 'open_account', 'deposit', 'withdrawal', 'app_login', 'documents')]
    + [('RU', 'no_greeting', t) for t in ('withdrawal', 'tariff', 'block')]
    + [('RU', 'no_ident', t) for t in ('withdrawal', 'block', 'documents', 'app_login')]
    + [('RU', 'rude', t) for t in ('tariff', 'block', 'complaint')]
    + [('RU', 'insult', t) for t in ('withdrawal', 'complaint')]
    + [('RU', 'no_close', t) for t in ('deposit', 'tariff', 'app_login')]
    + [('RU', 'wrong_info', t) for t in ('tariff', 'deposit')]
    + [('RU', 'combo_bad', t) for t in ('open_account',)]
    + [(lang, p, t) for lang in ('KZ', 'EN') for p, t in (
        ('clean', 'tariff'), ('clean', 'withdrawal'), ('clean', 'app_login'), ('no_greeting', 'deposit'),
        ('no_ident', 'block'), ('rude', 'complaint'), ('no_close', 'open_account'), ('wrong_info', 'tariff'))]
)

GREETING_RE = {
    'RU': re.compile(r'здравствуйте|добрый\s+(день|вечер|утро)|доброе\s+утро|приветствую', re.I),
    'KZ': re.compile(r'сәлем|қайырлы|ассалаумағалейкум|амансыз', re.I),
    'EN': re.compile(r'\b(hello|hi|good (morning|afternoon|evening)|welcome)\b', re.I),
}
WORDS_RANGE = {'RU': (125, 175), 'EN': (140, 195), 'KZ': (95, 150)}
KZ_ONLY = set('әғқңөұүһіӘҒҚҢӨҰҮҺІ')


def script_id(lang: str, n: int) -> str:
    return f'syn-{lang.lower()}-{n:03d}'


def intended_verdicts(profile: str, topic: str) -> dict[str, str]:
    """Designed verdict per criterion; `any` = the design does not pin it down. c03 depends on the topic."""
    spec = PROFILES[profile]
    out = {c: spec[c] for c in ('c01', 'c02', 'c04', 'c05', 'c06', 'c07', 'c08')}
    out['c03'] = spec.get('c03') or ('Да' if TOPICS[topic][1] else 'N/A')
    if profile in ('no_ident',) and not TOPICS[topic][1]:
        raise ValueError(f'{profile} needs a topic that requires identification, got {topic}')
    return dict(sorted(out.items()))


def build_specs() -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    counters: Counter[str] = Counter()
    rng = random.Random(SEED)
    for lang, profile, topic in MATRIX:
        counters[lang] += 1
        ivr = profile not in ('no_greeting', 'combo_bad') and rng.random() < 0.35
        specs.append({
            'id': script_id(lang, counters[lang]), 'language': lang, 'profile': profile, 'topic': topic,
            'ivr': ivr, 'intended': intended_verdicts(profile, topic),
        })
    return specs


# ---------------------------------------------------------------- scripts

SCRIPT_SCHEMA = {
    'type': 'object',
    'properties': {
        'turns': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {'speaker': {'type': 'string', 'enum': ['bot', 'operator', 'client']}, 'text': {'type': 'string'}},
                'required': ['speaker', 'text'],
                'additionalProperties': False,
            },
        }
    },
    'required': ['turns'],
    'additionalProperties': False,
}


def script_prompt(spec: dict[str, Any]) -> list[dict]:
    lang = LANG_NAMES[spec['language']]
    lo, hi = WORDS_RANGE[spec['language']]
    topic = TOPICS[spec['topic']][0]
    ivr = (
        f'The call starts with ONE short automated IVR bot line in {lang} (speaker "bot": the company name Freedom Broker, '
        '"the call may be recorded", "connecting you to an operator"), then the operator picks up.'
        if spec['ivr'] else 'There is NO IVR bot line: the first turn is the operator or the client as the scenario says.'
    )
    system = (
        'You write short, realistic telephone dialogs between a customer-support operator of a brokerage company '
        '"Freedom Broker" and a client, for a quality-assurance test set. Output JSON only.'
    )
    user = f"""Write a phone call transcript in {lang}.
Scenario: {topic}.
Operator behaviour (follow this EXACTLY, it is the point of the test): {PROFILES[spec['profile']]['instr']}
{ivr}
Hard rules:
- speakers: "operator", "client" and (only if requested) one leading "bot"; operator and client strictly alternate, 12 to 18 turns in total.
- total length {lo}-{hi} words in {lang} (spoken-language style, short sentences, natural fillers allowed).
- Write EVERY number, date and amount in words, never digits. No abbreviations, no emoji, no markdown, no stage directions.
- Use only invented names (operator and client first names). No real phone numbers, no card or passport numbers.
- All text must be in {lang} only (the company name may be written as "Фридом Брокер" in Russian/Kazakh, "Freedom Broker" in English).
Return {{"turns": [{{"speaker": ..., "text": ...}}, ...]}}."""
    return [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]


def word_count(turns: list[dict]) -> int:
    return sum(len(t['text'].split()) for t in turns)


def validate_script(spec: dict[str, Any], turns: list[dict]) -> list[str]:
    """Problems of a generated script; empty list = usable."""
    problems: list[str] = []
    lang = spec['language']
    if not 10 <= len(turns) <= 22:
        problems.append(f'turns={len(turns)}')
    speakers = [t['speaker'] for t in turns]
    body = [s for s in speakers if s != 'bot']
    if 'operator' not in body or 'client' not in body:
        problems.append('missing speaker')
    if speakers.count('bot') > (1 if spec['ivr'] else 0) or (spec['ivr'] and speakers[:1] != ['bot']) or 'bot' in speakers[1:]:
        problems.append('bot placement')
    if any(a == b for a, b in zip(body, body[1:])):
        problems.append('speakers do not alternate')
    if any(not t['text'].strip() for t in turns):
        problems.append('empty turn')
    text = ' '.join(t['text'] for t in turns)
    if re.search(r'\d', text):
        problems.append('digits')
    letters = [c for c in text if c.isalpha()]
    cyr = sum('\u0400' <= c <= '\u04ff' for c in letters)
    lat = sum('a' <= c.lower() <= 'z' for c in letters)
    if letters:
        if lang == 'EN' and lat / len(letters) < 0.97:
            problems.append('not English')
        if lang in ('RU', 'KZ') and cyr / len(letters) < 0.93:
            problems.append('not Cyrillic')
        if lang == 'KZ' and sum(c in KZ_ONLY for c in letters) / len(letters) < 0.02:
            problems.append('no Kazakh letters')
        if lang == 'RU' and sum(c in KZ_ONLY - set('іІ') for c in letters) / len(letters) > 0.005:
            problems.append('Kazakh letters in RU')
    lo, hi = WORDS_RANGE[lang]
    if not lo - 10 <= word_count(turns) <= hi + 15:
        problems.append(f'words={word_count(turns)}')
    first_op = next((t['text'] for t in turns if t['speaker'] == 'operator'), '')
    greets = bool(GREETING_RE[lang].search(first_op))
    if spec['intended']['c01'] == 'Да' and not greets:
        problems.append('clean opening lacks greeting')
    if spec['intended']['c01'] == 'Нет' and greets:
        problems.append('greeting present in no_greeting profile')
    if spec['intended']['c07'] == 'Нет' and turns[-1]['speaker'] != 'client':
        problems.append('no_close must end on the client')
    return problems


def merge_same_speaker(turns: list[dict]) -> list[dict]:
    out: list[dict] = []
    for t in turns:
        if out and out[-1]['speaker'] == t['speaker']:
            out[-1] = {'speaker': t['speaker'], 'text': f"{out[-1]['text'].rstrip()} {t['text'].strip()}"}
        else:
            out.append({'speaker': t['speaker'], 'text': t['text'].strip()})
    return out


async def cmd_scripts(args: argparse.Namespace) -> int:
    profile = load_profiles()['h200-gemma']
    llm = make_client(profile)
    existing = {s['id']: s for s in json.loads(SCRIPTS.read_text(encoding='utf-8'))['dialogs']} if SCRIPTS.exists() else {}
    specs = [s for s in build_specs() if not args.only or s['id'] in args.only]
    sem = asyncio.Semaphore(6)

    async def one(spec: dict[str, Any]) -> dict[str, Any] | None:
        old = existing.get(spec['id'])
        if old and not args.force and (not args.only or spec['id'] not in args.only):
            return old
        async with sem:
            for attempt in range(6):
                try:
                    comp = (await llm.complete(script_prompt(spec), SCRIPT_SCHEMA, 0.8 + 0.05 * attempt, 1))[0]
                    turns = merge_same_speaker(json.loads(comp.text or '{}').get('turns', []))
                except Exception as exc:  # noqa: BLE001
                    print(f'  {spec["id"]} attempt {attempt}: {type(exc).__name__}: {str(exc)[:100]}', file=sys.stderr)
                    continue
                problems = validate_script(spec, turns)
                if not problems:
                    print(f'  {spec["id"]}: ok, {len(turns)} turns, {word_count(turns)} words (attempt {attempt})')
                    return {**spec, 'turns': turns, 'generator': profile.name}
                print(f'  {spec["id"]} attempt {attempt}: {", ".join(problems)}', file=sys.stderr)
        return None

    out = await asyncio.gather(*(one(s) for s in specs))
    failed = [s['id'] for s, o in zip(specs, out) if o is None]
    dialogs = [o for o in out if o is not None]
    keep = [d for i, d in existing.items() if i not in {s['id'] for s in specs}]
    SCRIPTS.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'note': 'SYNTHETIC dialogs written by an LLM from a scenario matrix; invented names, no real personal data',
        'seed': SEED, 'generator': profile.name, 'dialogs': sorted(dialogs + keep, key=lambda d: d['id']),
    }
    SCRIPTS.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(f'scripts: {len(payload["dialogs"])} saved, failed: {failed}')
    return 1 if failed else 0


def load_scripts() -> list[dict[str, Any]]:
    return json.loads(SCRIPTS.read_text(encoding='utf-8'))['dialogs']


# ---------------------------------------------------------------- audio: pure parts

PAUSE_RANGE_S = (0.25, 0.70)
SNR_RANGE_DB = (15, 25)
# The TTS draws a different voice for every request (raw F0 of one role ranged 118-252 Hz inside one dialog) and has no voice control
# (`instructions` is rejected with HTTP 400), so every turn is pitch-normalised to a per-role target F0 measured on that turn's raw clip.
VOICE_TARGET_F0 = {'operator': 115.0, 'client': 215.0, 'bot': 165.0}
VOICE_TEMPO = {'operator': '', 'client': ':tempo=1.04', 'bot': ':tempo=0.95'}
PITCH_RATIO_LIMITS = (0.5, 2.0)


def pitch_ratio(raw_f0: float | None, target: float) -> float:
    """Pitch factor that moves a clip with median F0 `raw_f0` to `target` (1.0 when F0 could not be measured), within limits."""
    if not raw_f0:
        return 1.0
    return max(PITCH_RATIO_LIMITS[0], min(PITCH_RATIO_LIMITS[1], target / raw_f0))
BANDPASS = 'highpass=f=300,lowpass=f=3400,aresample=8000'
MP3_BITRATE = '48k'  # the real calls are 16 kHz mono MP3 at ~48 kbit/s


def pauses_for(call_id: str, n: int) -> list[float]:
    """Seeded pause (seconds) before each turn but the first."""
    rng = random.Random(f'{SEED}:{call_id}:pauses')
    return [round(rng.uniform(*PAUSE_RANGE_S), 3) for _ in range(max(n - 1, 0))]


def snr_for(call_id: str) -> int:
    return random.Random(f'{SEED}:{call_id}:snr').randint(*SNR_RANGE_DB)


def turn_boundaries(durations_s: list[float], pauses_s: list[float]) -> list[tuple[float, float]]:
    """(start, end) of every turn on the concatenated timeline: turn i starts after turn i-1 plus pause i-1."""
    out: list[tuple[float, float]] = []
    t = 0.0
    for i, d in enumerate(durations_s):
        if i:
            t += pauses_s[i - 1]
        out.append((round(t, 3), round(t + d, 3)))
        t += d
    return out


def mulaw_encode(sample: int) -> int:
    """G.711 mu-law encode of one 16-bit sample to a byte."""
    bias, clip = 0x84, 32635
    sign = 0x80 if sample < 0 else 0
    s = min(abs(sample), clip) + bias
    exponent = s.bit_length() - 8  # s in [0x84, 0x7FFF+0x84] -> segment 0..7
    exponent = max(0, min(exponent, 7))
    mantissa = (s >> (exponent + 3)) & 0x0F
    return ~(sign | (exponent << 4) | mantissa) & 0xFF


def mulaw_decode(byte: int) -> int:
    byte = ~byte & 0xFF
    sign, exponent, mantissa = byte & 0x80, (byte >> 4) & 0x07, byte & 0x0F
    s = (((mantissa << 3) + 0x84) << exponent) - 0x84
    return -s if sign else s


def mulaw_roundtrip(samples: array.array) -> array.array:
    return array.array('h', (mulaw_decode(mulaw_encode(x)) for x in samples))


def rms(samples: array.array | list[float]) -> float:
    return math.sqrt(sum(x * x for x in samples) / len(samples)) if len(samples) else 0.0


def add_noise(samples: array.array, snr_db: float, rng: random.Random) -> array.array:
    """White Gaussian noise whose power is `snr_db` below the mean power of the whole signal."""
    sigma = rms(samples) / (10 ** (snr_db / 20))
    return array.array('h', (max(-32768, min(32767, round(x + rng.gauss(0.0, sigma)))) for x in samples))


def degrade_chain(call_id: str) -> dict[str, Any]:
    """Parameters of the telephony chain for one call (all seeded by id)."""
    return {
        'mono': True, 'bandpass_hz': (300, 3400), 'sample_rate_hz': 8000, 'codec': 'G.711 mu-law',
        'snr_db': snr_for(call_id), 'mp3': {'sample_rate_hz': 16000, 'channels': 1, 'bitrate': MP3_BITRATE},
    }


# ---------------------------------------------------------------- audio: ffmpeg / TTS

def ffmpeg(*args: str, stdin: bytes | None = None) -> bytes:
    proc = subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', *args], input=stdin, capture_output=True)
    if proc.returncode:
        raise RuntimeError(f'ffmpeg failed: {proc.stderr.decode(errors="replace")[:300]}')
    return proc.stdout


def pcm_from(path_or_bytes: Path | bytes, filter_chain: str, rate: int) -> array.array:
    """Decode any audio to mono s16le at `rate` through an ffmpeg filter chain."""
    src = ['-i', str(path_or_bytes)] if isinstance(path_or_bytes, Path) else ['-i', 'pipe:0']
    out = ffmpeg(*src, '-af', filter_chain, '-ac', '1', '-ar', str(rate), '-f', 's16le', 'pipe:1',
                 stdin=None if isinstance(path_or_bytes, Path) else path_or_bytes)
    arr = array.array('h')
    arr.frombytes(out)
    return arr


def write_wav(path: Path, samples: array.array, rate: int) -> None:
    import wave
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(samples.tobytes())


async def tts_turn(call_id: str, idx: int, speaker: str, text: str) -> array.array:
    """TTS of one turn (cached as raw WAV), pitch-shifted per speaker, mono s16 at 24 kHz."""
    import os
    wav = TTS_DIR / call_id / f'{idx:02d}.wav'
    if not wav.exists():
        base = os.environ['AIGW_BASE_URL'].rstrip('/')
        body = {'model': TTS_MODEL, 'input': text, 'voice': 'default', 'response_format': 'wav'}
        headers = {'Authorization': f'Bearer {os.environ["AIGW_API_KEY"]}'}
        last = ''
        for attempt in range(4):
            try:
                resp = await new_session().post(f'{base}/audio/speech', json=body, headers=headers, timeout=120)
                if resp.status_code == 200 and resp.content[:4] == b'RIFF':
                    wav.parent.mkdir(parents=True, exist_ok=True)
                    wav.write_bytes(resp.content)
                    break
                last = f'HTTP {resp.status_code}'
            except Exception as exc:  # noqa: BLE001
                last = type(exc).__name__
            await asyncio.sleep(2 * (attempt + 1))
        else:
            raise RuntimeError(f'TTS failed for {call_id}#{idx}: {last}')
    samples = await asyncio.to_thread(pcm_from, wav, 'anull', 16000)
    raw_f0 = await asyncio.to_thread(median_f0, samples, 16000, 40)
    flt = f'rubberband=pitch={pitch_ratio(raw_f0, VOICE_TARGET_F0[speaker]):.4f}:formant=preserved' + VOICE_TEMPO[speaker]
    return await asyncio.to_thread(pcm_from, wav, flt, TTS_RATE)


def build_master(call_id: str, turns: list[dict], clips: list[array.array]) -> tuple[array.array, list[dict]]:
    pauses = pauses_for(call_id, len(turns))
    bounds = turn_boundaries([len(c) / TTS_RATE for c in clips], pauses)
    master = array.array('h')
    for i, clip in enumerate(clips):
        if i:
            master.extend(array.array('h', bytes(2 * round(pauses[i - 1] * TTS_RATE))))
        master.extend(clip)
    timings = [{'idx': i, 'speaker': t['speaker'], 'start': s, 'end': e} for i, (t, (s, e)) in enumerate(zip(turns, bounds))]
    return master, timings


def degrade_audio(call_id: str, master_wav: Path) -> None:
    """Telephony chain: mono -> band-pass 300-3400 Hz -> 8 kHz -> mu-law -> noise at seeded SNR -> 16 kHz mono MP3."""
    params = degrade_chain(call_id)
    samples = pcm_from(master_wav, BANDPASS, 8000)
    samples = mulaw_roundtrip(samples)
    samples = add_noise(samples, params['snr_db'], random.Random(f'{SEED}:{call_id}:noise'))
    DEGRADED_DIR.mkdir(parents=True, exist_ok=True)
    tmp = DEGRADED_DIR / f'{call_id}.tel.wav'
    write_wav(tmp, samples, 8000)
    ffmpeg('-i', str(tmp), '-ac', '1', '-ar', '16000', '-b:a', MP3_BITRATE, str(DEGRADED_DIR / f'{call_id}.mp3'))
    tmp.unlink()


def clean_audio(call_id: str, master_wav: Path) -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    ffmpeg('-i', str(master_wav), '-ac', '1', '-ar', '16000', '-b:a', MP3_BITRATE, str(CLEAN_DIR / f'{call_id}.mp3'))


def ablation_ids(dialogs: list[dict[str, Any]]) -> list[str]:
    """8 dialogs spread over the set: 5 RU, 2 KZ, 1 EN (every k-th of each language)."""
    quota = {'RU': 5, 'KZ': 2, 'EN': 1}
    out: list[str] = []
    for lang, n in quota.items():
        ids = sorted(d['id'] for d in dialogs if d['language'] == lang)
        out += [ids[round(i * len(ids) / n)] for i in range(n)] if ids else []
    return out


async def cmd_tts(args: argparse.Namespace) -> int:
    dialogs = [d for d in load_scripts() if not args.only or d['id'] in args.only]
    abl = set(ablation_ids(load_scripts()))
    sem = asyncio.Semaphore(4)
    rows = {}

    async def one(d: dict[str, Any]) -> None:
        async with sem:
            clips = [await tts_turn(d['id'], i, t['speaker'], t['text']) for i, t in enumerate(d['turns'])]
        master, timings = build_master(d['id'], d['turns'], clips)
        wav = MASTER_DIR / f'{d["id"]}.wav'
        write_wav(wav, master, TTS_RATE)
        TIMING_DIR.mkdir(parents=True, exist_ok=True)
        dur = len(master) / TTS_RATE
        (TIMING_DIR / f'{d["id"]}.json').write_text(
            json.dumps({'duration_s': round(dur, 3), 'turns': timings, 'chain': degrade_chain(d['id'])}), encoding='utf-8')
        await asyncio.to_thread(degrade_audio, d['id'], wav)
        if d['id'] in abl:
            await asyncio.to_thread(clean_audio, d['id'], wav)
        rows[d['id']] = dur
        print(f'  {d["id"]}: {dur:.1f} s, snr {snr_for(d["id"])} dB')

    await asyncio.gather(*(one(d) for d in dialogs))
    out_of_range = {i: round(v, 1) for i, v in rows.items() if not 45 <= v <= 75}
    print(f'tts: {len(rows)} dialogs, duration {min(rows.values()):.1f}-{max(rows.values()):.1f} s, outside 45-75 s: {out_of_range}')
    return 0


# ---------------------------------------------------------------- ASR metrics

LOOP_RUN = 5


def count_loops(text: str, run: int = LOOP_RUN) -> int:
    """Decoding loops: maximal runs of at least `run` identical consecutive words."""
    words = normalize(text).split()
    loops = 0
    i = 0
    while i < len(words):
        j = i
        while j + 1 < len(words) and words[j + 1] == words[i]:
            j += 1
        if j - i + 1 >= run:
            loops += 1
        i = j + 1
    return loops


def reference_words(turns: list[dict], timings: list[dict]) -> list[tuple[float, str]]:
    """(time, speaker) of every reference word: words spread over the turn by character count (midpoint of each word's span)."""
    out: list[tuple[float, str]] = []
    for turn, tm in zip(turns, timings):
        words = normalize(turn['text']).split()
        total = sum(len(w) for w in words) or 1
        done = 0
        for w in words:
            mid = done + len(w) / 2
            out.append((tm['start'] + (tm['end'] - tm['start']) * mid / total, turn['speaker']))
            done += len(w)
    return out


def attribution(ref: list[tuple[float, str]], segments: list[dict]) -> float | None:
    """Fraction of reference words whose time lies in a segment carrying the right speaker, under the best label->role mapping.

    `segments`: dicts with start, end, speaker, with real times. A word covered by no segment counts as wrong."""
    segs = [s for s in segments if s.get('start') is not None and s.get('end') is not None and s.get('speaker')]
    if not ref or not segs:
        return None
    cover: list[str | None] = []
    for t, _ in ref:
        hit = [s for s in segs if s['start'] - 0.05 <= t <= s['end'] + 0.05]
        cover.append(min(hit, key=lambda s: s['end'] - s['start'])['speaker'] if hit else None)
    roles = sorted({r for _, r in ref})
    labels = sorted({c for c in cover if c is not None}, key=lambda lab: -cover.count(lab))[:6]
    best = 0
    for combo in itertools.permutations(labels + [None] * len(roles), len(roles)):  # role i <- label combo[i]
        mapping = {lab: role for role, lab in zip(roles, combo) if lab is not None}
        best = max(best, sum(1 for (_, r), c in zip(ref, cover) if c is not None and mapping.get(c) == r))
    return best / len(ref)


def hyp_text(result: AsrResult) -> str:
    return ' '.join(s.text for s in result.segments if s.text.strip()) or result.text


def mean(values: list[float | None]) -> float | None:
    vals = [v for v in values if v is not None]
    return statistics.fmean(vals) if vals else None


def pooled_error(pairs: list[tuple[str, str]], unit: str) -> float | None:
    """Pooled CER/WER over many (ref, hyp) pairs: total edits / total reference length."""
    edits = length = 0
    for ref, hyp in pairs:
        r, h = normalize(ref), normalize(hyp)
        if unit == 'word':
            r, h = r.split(), h.split()
        edits += edit_distance(r, h)
        length += len(r)
    return edits / length if length else None


# ---------------------------------------------------------------- ASR run

def selected_providers(names: list[str] | None) -> list[AsrProvider]:
    providers = load_asr_providers()
    out = []
    for name, p in providers.items():
        if names and name not in names:
            continue
        if not p.enabled or name in SKIP_PROVIDERS or not p.configured():
            continue
        out.append(p)
    return out


def raw_path(variant: str, provider: str, call_id: str) -> Path:
    return RAW_DIR / variant / provider / f'{call_id}.json'


def hint_for(language: str) -> str | None:
    """The server rule (server/routes/transcripts.py): only KZ forces a language."""
    return 'kk' if language.upper() == 'KZ' else None


async def run_provider(
    provider: AsrProvider, items: list[tuple[str, dict[str, Any]]], concurrency: int, status: dict[str, dict]
) -> None:
    sem = asyncio.Semaphore(concurrency)

    async def one(variant: str, d: dict[str, Any]) -> None:
        path = raw_path(variant, provider.name, d['id'])
        if path.exists():
            return
        src = (DEGRADED_DIR if variant == 'degraded' else CLEAN_DIR) / f'{d["id"]}.mp3'
        async with sem:
            try:
                result = await transcribe(provider, src.read_bytes(), src.name, language=hint_for(d['language']))
            except AsrError as exc:
                status.setdefault(provider.name, {})[f'{variant}/{d["id"]}'] = str(exc)[:160]
                print(f'  {provider.name} {variant} {d["id"]}: {str(exc)[:120]}', file=sys.stderr)
                return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(result.model_dump_json(indent=1), encoding='utf-8')
        print(f'  {provider.name} {variant} {d["id"]}: {result.seconds:.1f} s, {len(result.segments)} seg')

    await asyncio.gather(*(one(v, d) for v, d in items))


async def cmd_asr(args: argparse.Namespace) -> int:
    dialogs = load_scripts()
    abl = set(ablation_ids(dialogs))
    providers = selected_providers(args.providers)
    status: dict[str, dict] = {}
    skipped = [n for n, p in load_asr_providers().items() if (not p.enabled or not p.configured() or n in SKIP_PROVIDERS) and not args.providers]
    print('providers:', [p.name for p in providers], '| not run:', skipped)

    def items_for(p: AsrProvider) -> list[tuple[str, dict[str, Any]]]:
        ds = [d for d in dialogs if (not args.only or d['id'] in args.only) and (p.name not in RU_ONLY_PROVIDERS or d['language'] == 'RU')]
        out = [('degraded', d) for d in ds]
        if not args.no_ablation:
            out += [('clean', d) for d in ds if d['id'] in abl]
        return out

    local = [p for p in providers if p.hosting == 'local']
    cloud = [p for p in providers if p.hosting != 'local']

    async def run_local() -> None:
        for p in local:
            t0 = time.perf_counter()
            await run_provider(p, items_for(p), 1, status)
            print(f'{p.name}: {time.perf_counter() - t0:.0f} s wall')

    async def run_cloud() -> None:
        await asyncio.gather(*(run_provider(p, items_for(p), 2, status) for p in cloud))

    t0 = time.perf_counter()
    await asyncio.gather(run_local(), run_cloud())
    (DATA / 'asr_status.json').write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'asr: wall {time.perf_counter() - t0:.0f} s; errors: {sum(len(v) for v in status.values())}')
    for name, errs in status.items():
        print(f'  {name}: {len(errs)} failed, e.g. {next(iter(errs.values()))}')
    return 0


def load_raw(variant: str, provider: str, call_id: str) -> AsrResult | None:
    path = raw_path(variant, provider, call_id)
    return AsrResult.model_validate_json(path.read_text(encoding='utf-8')) if path.exists() else None


def asr_metrics(dialogs: list[dict[str, Any]], providers: list[str]) -> dict[str, Any]:
    """Per provider x dialog numbers (degraded variant) plus clean-vs-degraded CER on the ablation subset."""
    out: dict[str, Any] = {}
    for prov in providers:
        per: dict[str, Any] = {}
        for d in dialogs:
            result = load_raw('degraded', prov, d['id'])
            if result is None:
                continue
            ref = ' '.join(t['text'] for t in d['turns'])
            hyp = hyp_text(result)
            timings = json.loads((TIMING_DIR / f'{d["id"]}.json').read_text(encoding='utf-8'))
            att = None
            if result.diarized:
                segs = [s.model_dump() for s in result.segments]
                att = attribution(reference_words(d['turns'], timings['turns']), segs)
            audio_s = timings['duration_s']
            row = {
                'language': d['language'], 'cer': cer(ref, hyp), 'wer': wer(ref, hyp), 'attribution': att,
                'loops': count_loops(hyp), 'seconds': result.seconds, 'audio_s': audio_s, 'diarized': result.diarized,
                'segments': len(result.segments), 'hyp_words': len(normalize(hyp).split()), 'ref_words': len(normalize(ref).split()),
            }
            clean = load_raw('clean', prov, d['id'])
            if clean is not None:
                row['cer_clean'] = cer(ref, hyp_text(clean))
                row['wer_clean'] = wer(ref, hyp_text(clean))
            per[d['id']] = row
        out[prov] = per
    return out


def summarize_asr(metrics: dict[str, Any], dialogs: list[dict[str, Any]]) -> dict[str, Any]:
    """provider -> language|ALL -> aggregates (mean of per-dialog CER/WER, pooled CER/WER, loops, latency, attribution)."""
    texts = {d['id']: ' '.join(t['text'] for t in d['turns']) for d in dialogs}
    out: dict[str, Any] = {}
    for prov, per in metrics.items():
        agg: dict[str, Any] = {}
        for lang in ('RU', 'KZ', 'EN', 'ALL'):
            rows = {i: r for i, r in per.items() if lang == 'ALL' or r['language'] == lang}
            if not rows:
                continue
            pairs_hyp = {}
            for i in rows:
                res = load_raw('degraded', prov, i)
                pairs_hyp[i] = (texts[i], hyp_text(res)) if res else None
            pairs = [p for p in pairs_hyp.values() if p]
            agg[lang] = {
                'n': len(rows),
                'cer_mean': mean([r['cer'] for r in rows.values()]),
                'wer_mean': mean([r['wer'] for r in rows.values()]),
                'cer_pooled': pooled_error(pairs, 'char'),
                'wer_pooled': pooled_error(pairs, 'word'),
                'attribution': mean([r['attribution'] for r in rows.values()]),
                'loops': sum(r['loops'] for r in rows.values()),
                'dialogs_with_loops': sum(1 for r in rows.values() if r['loops']),
                'seconds_mean': mean([r['seconds'] for r in rows.values()]),
                'seconds_per_audio_min': sum(r['seconds'] for r in rows.values()) / (sum(r['audio_s'] for r in rows.values()) / 60),
            }
        abl = {i: r for i, r in per.items() if 'cer_clean' in r}
        if abl:
            agg['ablation'] = {
                'n': len(abl), 'cer_clean': mean([r['cer_clean'] for r in abl.values()]),
                'cer_degraded': mean([r['cer'] for r in abl.values()]),
                'wer_clean': mean([r['wer_clean'] for r in abl.values()]),
                'wer_degraded': mean([r['wer'] for r in abl.values()]),
            }
        out[prov] = agg
    return out


# ---------------------------------------------------------------- judge

def exact_record(d: dict[str, Any], timings: dict[str, Any]) -> Record:
    turns = []
    for i, (t, tm) in enumerate(zip(d['turns'], timings['turns'])):
        sec = int(tm['start'])
        turns.append(Turn(idx=i, timestamp=f'{sec // 60:02d}:{sec % 60:02d}', offset_s=tm['start'], speaker=t['speaker'], text=t['text']))
    return Record(conversation_id=d['id'], channel='voice call', language=d['language'], transcript=turns, audio_url=None)


def base_record(d: dict[str, Any]) -> Record:
    return Record(conversation_id=d['id'], channel='voice call', language=d['language'], transcript=[], audio_url=None)


async def judge_record(record: Record, profile, llm, sem: asyncio.Semaphore) -> dict[str, Any] | None:
    for attempt in range(3):
        try:
            async with sem:
                ev, _ = await evaluate(record, checklist_for(record), profile=profile, mode='per_criterion', k=1, llm=llm)
            return {'verdicts': {it.criterion_id: it.verdict for it in ev.items}, 'total': ev.score.total, 'gross': ev.score.gross_error}
        except Exception as exc:  # noqa: BLE001
            print(f'  {record.conversation_id}: {type(exc).__name__}: {str(exc)[:100]}', file=sys.stderr)
            await asyncio.sleep(2 * (attempt + 1))
    return None


async def cmd_judge(args: argparse.Namespace) -> int:
    dialogs = load_scripts()
    profile = load_profiles()['h200-gemma']
    llm = make_client(profile)
    sem = asyncio.Semaphore(6)
    provs = [p.name for p in selected_providers(args.providers)]
    jobs: list[tuple[str, dict[str, Any]]] = []
    for d in dialogs:
        jobs += [('exact', d), ('exact-rerun', d)]
        for prov in provs:
            if load_raw('degraded', prov, d['id']):
                jobs.append((prov, d))

    async def one(source: str, d: dict[str, Any]) -> None:
        path = JUDGE_DIR / source / f'{d["id"]}.json'
        if path.exists():
            return
        timings = json.loads((TIMING_DIR / f'{d["id"]}.json').read_text(encoding='utf-8'))
        if source.startswith('exact'):
            record = exact_record(d, timings)
        else:
            try:
                record = await asr_to_record(load_raw('degraded', source, d['id']), base_record(d), profile, llm)
            except AsrError as exc:
                result = {'error': str(exc)[:160]}
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
                return
            (JUDGE_DIR / 'records' / source).mkdir(parents=True, exist_ok=True)
            (JUDGE_DIR / 'records' / source / f'{d["id"]}.json').write_text(record.model_dump_json(), encoding='utf-8')
        result = await judge_record(record, profile, llm, sem)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result or {'error': 'judge failed'}, ensure_ascii=False), encoding='utf-8')
        print(f'  {source} {d["id"]}: {"ok" if result else "FAILED"}')

    t0 = time.perf_counter()
    await asyncio.gather(*(one(s, d) for s, d in jobs))
    print(f'judge: {len(jobs)} records, wall {time.perf_counter() - t0:.0f} s')
    return 0


def load_judged(source: str, call_id: str) -> dict[str, Any] | None:
    path = JUDGE_DIR / source / f'{call_id}.json'
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding='utf-8'))
    return None if 'error' in data else data


def scale_value(verdict: str) -> float | None:
    m = re.search(r'-?\d+(?:[.,]\d+)?', verdict or '')
    return float(m.group().replace(',', '.')) if m else None


SCALE_MAX = {'c04': 20.0, 'c06': 10.0}
YES_NO = {'Да': 'yes', 'Нет': 'no', 'N/A': 'na'}  # the evaluator's verdict strings


def verdict_matches(intended: str, verdict: str | None, scale_max: float = 20.0) -> bool | None:
    """Did the judge verdict hit the designed one? None = not pinned (`any`) or no verdict. high >= 75 % of the scale, low <= 50 %."""
    if intended == 'any' or verdict is None:
        return None
    if intended in ('high', 'low'):
        v = scale_value(verdict)
        if v is None:
            return False
        return v >= 0.75 * scale_max if intended == 'high' else v <= 0.5 * scale_max
    return verdict.strip().lower() == YES_NO[intended]


def norm_verdict(verdict: str) -> str:
    return verdict.strip().lower()


def compare_judgements(ref: dict[str, Any], other: dict[str, Any]) -> tuple[int, int, float | None]:
    """(flips, cells, abs total difference) of one dialog against the reference judgement."""
    flips = cells = 0
    for crit, rv in ref['verdicts'].items():
        if crit in other['verdicts']:
            cells += 1
            flips += norm_verdict(rv) != norm_verdict(other['verdicts'][crit])
    diff = abs(ref['total'] - other['total']) if ref['total'] is not None and other['total'] is not None else None
    return flips, cells, diff


def judge_metrics(dialogs: list[dict[str, Any]], providers: list[str]) -> dict[str, Any]:
    design: dict[str, Any] = {'per_criterion': {}, 'per_profile': {}}
    hits: Counter[str] = Counter()
    tot: Counter[str] = Counter()
    phits: Counter[str] = Counter()
    ptot: Counter[str] = Counter()
    for d in dialogs:
        j = load_judged('exact', d['id'])
        if not j:
            continue
        for crit, intended in d['intended'].items():
            m = verdict_matches(intended, j['verdicts'].get(crit), SCALE_MAX.get(crit, 20.0))
            if m is None:
                continue
            tot[crit] += 1
            hits[crit] += m
            ptot[d['profile']] += 1
            phits[d['profile']] += m
    design['per_criterion'] = {c: {'hit': hits[c], 'n': tot[c]} for c in sorted(tot)}
    design['per_profile'] = {p: {'hit': phits[p], 'n': ptot[p]} for p in sorted(ptot)}
    design['all'] = {'hit': sum(hits.values()), 'n': sum(tot.values())}

    sources: dict[str, Any] = {}
    for src in ['exact-rerun', *providers]:
        stats: dict[str, Any] = {}
        for lang in ('RU', 'KZ', 'EN', 'ALL'):
            flips = cells = calls = failed = 0
            diffs: list[float] = []
            for d in dialogs:
                if lang != 'ALL' and d['language'] != lang:
                    continue
                ref = load_judged('exact', d['id'])
                if not ref:
                    continue
                other = load_judged(src, d['id'])
                if other is None:
                    if (JUDGE_DIR / src / f'{d["id"]}.json').exists():
                        failed += 1
                    continue
                f, c, diff = compare_judgements(ref, other)
                flips, cells, calls = flips + f, cells + c, calls + 1
                if diff is not None:
                    diffs.append(diff)
            if calls or failed:
                stats[lang] = {'calls': calls, 'failed': failed, 'flips': flips, 'cells': cells,
                               'flip_rate': flips / cells if cells else None, 'mae_total': mean(diffs)}
        sources[src] = stats
    return {'design': design, 'sources': sources}


# ---------------------------------------------------------------- report

def fmt(v: float | None, digits: int = 3) -> str:
    return '—' if v is None else f'{v:.{digits}f}'


def build_results() -> dict[str, Any]:
    dialogs = load_scripts()
    providers = [n for n in load_asr_providers() if (RAW_DIR / 'degraded' / n).exists()]
    metrics = asr_metrics(dialogs, providers)
    summary = summarize_asr(metrics, dialogs)
    judged = judge_metrics(dialogs, providers)
    durations = {d['id']: json.loads((TIMING_DIR / f'{d["id"]}.json').read_text(encoding='utf-8'))['duration_s'] for d in dialogs}
    counts = Counter(d['language'] for d in dialogs)
    verdicts = {}
    for d in dialogs:
        row = {}
        for src in ['exact', 'exact-rerun', *providers]:
            j = load_judged(src, d['id'])
            if j:
                row[src] = {'verdicts': j['verdicts'], 'total': j['total']}
        verdicts[d['id']] = row
    return {
        'synthetic': True, 'seed': SEED,
        'dialogs': {'count': len(dialogs), 'by_language': dict(counts), 'audio_s': {
            'min': min(durations.values()), 'max': max(durations.values()), 'mean': statistics.fmean(durations.values()),
            'total': sum(durations.values())}, 'ablation_ids': ablation_ids(dialogs),
            'by_profile': dict(Counter(d['profile'] for d in dialogs)),
            'snr_db': {d['id']: snr_for(d['id']) for d in dialogs}},
        'asr': summary, 'asr_per_dialog': metrics, 'judge': judged, 'verdicts': verdicts,
        'checks': json.loads(CHECKS.read_text(encoding='utf-8')) if CHECKS.exists() else None,
    }


def ranking(summary: dict[str, Any], key: str = 'cer_pooled', lang: str = 'ALL') -> list[tuple[str, float]]:
    rows = [(p, a[lang][key]) for p, a in summary.items() if lang in a and a[lang].get(key) is not None]
    return sorted(rows, key=lambda r: r[1])


def labels() -> dict[str, str]:
    return {n: p.label for n, p in load_asr_providers().items()}


def render_report(res: dict[str, Any]) -> str:
    asr, judge = res['asr'], res['judge']
    lab = labels()
    L: list[str] = []
    n = res['dialogs']
    L += [
        '# Синтетический набор звонков: ASR и судья с точным эталоном',
        '',
        '**Всё здесь синтетика.** Диалоги написаны LLM (`h200-gemma`) по матрице сценариев, выговорены TTS и пропущены через модель '
        'телефонного канала. Текст сценария — точный эталон: CER/WER, привязка к спикеру и вердикты судьи считаются относительно него, '
        'а не относительно другого ASR (как в `summary.md` и `noise-floor.md`). Числа ниже измерены этим прогоном; '
        'абсолютные значения на реальных звонках они не предсказывают (см. «Ограничения»).',
        '',
        '## Метод',
        '',
        f'- Диалоги: {n["count"]} ({", ".join(f"{k} {v}" for k, v in n["by_language"].items())}), звук {n["audio_s"]["min"]:.0f}–{n["audio_s"]["max"]:.0f} с '
        f'(среднее {n["audio_s"]["mean"]:.0f} с, всего {n["audio_s"]["total"] / 60:.1f} мин). Оператор + клиент, у части диалогов первой идёт реплика IVR-бота. '
        'Для каждого диалога задан профиль качества (чистый / без приветствия / без идентификации / грубость / оскорбление / без завершения / неверная консультация / комбинация) '
        'и замысел по критериям c01–c08 (`bench/asr/synthetic/scripts.json`).',
        '- TTS: `alemai/k2-fsa/OmniVoice` через aigw, один вызов на реплику, голос только `default` (поле `instructions` отвергается HTTP 400). '
        'TTS рисует новый голос на каждый запрос (сырой F0 одной роли внутри диалога гулял в пределах ~120–250 Гц), управлять голосом нельзя, поэтому каждая реплика приводится к целевому F0 своей роли '
        '(rubberband, `formant=preserved`; оператор 115 Гц, клиент 215 Гц + темп 1.04, бот 165 Гц + темп 0.95; F0 меряется по сырой реплике). Паузы 250–700 мс (seed), точные границы реплик сохранены.',
        '- Телефонный тракт: моно → полосовой фильтр 300–3400 Гц → 8 кГц → G.711 μ-law (кодирование и декодирование) → белый шум с SNR 15–25 дБ (seed по id) → MP3 16 кГц моно, 48 кбит/с (как реальные записи).',
        f'- ASR: все включённые провайдеры из `config/asr.toml`, которые настроены, на деградированном MP3; подсказка языка как в сервере (только KZ → `kk`, остальные авто). '
        f'Локальные (H200) — по одному запросу; `h200-gigaam-v3` и `h200-t-one` — только RU (русскоязычные движки); `h200-whisperx-kk` не запускался отдельно: '
        f'`h200-whisperx` получает `kk` для KZ так же, как на сервере. Ablation: {len(n["ablation_ids"])} диалогов дополнительно в чистом 16 кГц MP3 без тракта.',
        '- Метрики: CER/WER — нормализация `bench.asr.normalize` (регистр, ё→е, пунктуация); «среднее» — среднее по диалогам, «пул» — сумма правок / сумма длины эталона. '
        'Привязка к спикеру: доля слов эталона, время которых (слова равномерно по символам внутри реплики) попадает в сегмент с правильным спикером при лучшем сопоставлении меток и ролей; слово вне сегментов — ошибка. '
        'Петли — серии ≥5 одинаковых слов подряд в выводе. Задержка — время запроса к провайдеру.',
        '- Судья: `h200-gemma`, per_criterion, k=1, чек-лист звонков. (а) точный сценарий как Record с истинными ролями; (б) вывод `asr_to_record` каждого провайдера. '
        'Флип — вердикт критерия отличается от вердикта на точном сценарии; MAE — |итог ASR − итог точного|. Строка `exact-rerun` — повторная оценка того же точного сценария (шум модели).',
        '',
    ]

    def table(key_c: str, key_w: str, title: str) -> None:
        L.append(f'### {title}')
        L.append('')
        L.append('| провайдер | RU | KZ | EN | все |')
        L.append('|---|---:|---:|---:|---:|')
        for prov, _ in ranking(asr, key_c):
            cells = []
            for lang in ('RU', 'KZ', 'EN', 'ALL'):
                a = asr[prov].get(lang)
                cells.append(f'{fmt(a[key_c])} / {fmt(a[key_w])}' if a else '—')
            L.append(f'| {lab.get(prov, prov)} (`{prov}`) | ' + ' | '.join(cells) + ' |')
        L.append('')

    L += ['## Результаты ASR (деградированный звук)', '']
    L += ['Формат ячейки: CER / WER. Строки отсортированы по пулу CER на всех диалогах, которые провайдер обработал (у RU-only провайдеров — только RU, сравнивать их по колонке RU).', '']
    table('cer_pooled', 'wer_pooled', 'CER / WER, пул')
    table('cer_mean', 'wer_mean', 'CER / WER, среднее по диалогам')
    L += ['### Привязка к спикеру, петли, задержка', '',
          '| провайдер | диалогов | привязка RU | KZ | EN | петель (диалогов с петлёй) | задержка, с (среднее) | с на минуту звука |',
          '|---|---:|---:|---:|---:|---:|---:|---:|']
    for prov, _ in ranking(asr, 'cer_pooled'):
        a = asr[prov]
        al = a['ALL']
        att = [fmt(a[g]['attribution'], 3) if g in a else '—' for g in ('RU', 'KZ', 'EN')]
        L.append(f'| `{prov}` | {al["n"]} | {" | ".join(att)} | {al["loops"]} ({al["dialogs_with_loops"]}) | {fmt(al["seconds_mean"], 1)} | {fmt(al["seconds_per_audio_min"], 2)} |')
    L += ['', '«—» в привязке: провайдер не диаризует или язык не запускался.', '']

    L += ['### Ablation: чистый звук против телефонного тракта', '', 'Одни и те же диалоги ablation-подмножества, CER / WER; сколько стоит тракт.', '',
          '| провайдер | диалогов | CER чистый | CER тракт | Δ CER | WER чистый | WER тракт |', '|---|---:|---:|---:|---:|---:|---:|']
    for prov, _ in ranking(asr, 'cer_pooled'):
        ab = asr[prov].get('ablation')
        if ab:
            L.append(f'| `{prov}` | {ab["n"]} | {fmt(ab["cer_clean"])} | {fmt(ab["cer_degraded"])} | {fmt(ab["cer_degraded"] - ab["cer_clean"])} | {fmt(ab["wer_clean"])} | {fmt(ab["wer_degraded"])} |')
    L.append('')

    d = judge['design']
    L += ['## Судья на точном сценарии: попал ли замысел', '',
          f'Вердикт судьи на точном тексте против замысла, ячейки с заданным замыслом: **{d["all"]["hit"]} из {d["all"]["n"]}**. '
          '`high`/`low` у c04, c06 — шкала ≥75 % / ≤50 % максимума (c04: 20, c06: 10).', '',
          '| критерий | совпало | из |', '|---|---:|---:|']
    for c, v in d['per_criterion'].items():
        L.append(f'| {c} | {v["hit"]} | {v["n"]} |')
    L += ['', '| профиль | совпало | из |', '|---|---:|---:|']
    for p, v in d['per_profile'].items():
        L.append(f'| {p} | {v["hit"]} | {v["n"]} |')
    L += ['', 'Промахи по критерию — это либо слабый сценарий, либо судья; различить без ручной проверки нельзя.', '']

    L += ['## ASR → судья: флипы вердиктов и MAE итога против точного сценария', '',
          '| источник | оценено | не оценено | флипов | из ячеек | доля | MAE итога | доля RU | KZ | EN |', '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    order = ['exact-rerun'] + [p for p, _ in sorted(((p, s['ALL']['flip_rate']) for p, s in judge['sources'].items() if p != 'exact-rerun' and 'ALL' in s and s['ALL']['flip_rate'] is not None), key=lambda r: r[1])]
    for src in order:
        s = judge['sources'][src]
        a = s.get('ALL')
        if not a:
            continue
        name = '**exact-rerun (шум модели)**' if src == 'exact-rerun' else f'`{src}`'
        per = [fmt(s[g]['flip_rate'], 3) if g in s else '—' for g in ('RU', 'KZ', 'EN')]
        L.append(f'| {name} | {a["calls"]} | {a["failed"]} | {a["flips"]} | {a["cells"]} | {fmt(a["flip_rate"])} | {fmt(a["mae_total"], 2)} | {" | ".join(per)} |')
    L += ['', 'Строка exact-rerun — нижняя граница шума: тот же текст, оценённый второй раз.', '']
    ck = res.get('checks')
    if ck:
        L += ['## Проверки синтетики', '', '### Различимость голосов (F0 после нормализации, Гц)', '',
              'Медиана по самым громким вокализованным кадрам всех реплик роли; в скобках — минимум и максимум по репликам (медиана реплики).', '',
              '| диалог | оператор | клиент | бот |', '|---|---:|---:|---:|']
        rng = ck.get('f0_turn_range', {})
        for cid, v in ck['f0'].items():
            cells = []
            for sp in ('operator', 'client', 'bot'):
                r = rng.get(cid, {}).get(sp)
                cells.append(f'{fmt(v.get(sp), 0)} ({r[0]:.0f}–{r[1]:.0f})' if v.get(sp) and r else '—')
            L.append(f'| {cid} | ' + ' | '.join(cells) + ' |')
        raw = ck['f0_unshifted_ru_first_turns']
        L += ['', f'Сырой вывод TTS, первые реплики оператора и клиента в одном RU-диалоге: оператор {fmt(raw["operator"], 0)} Гц, клиент {fmt(raw["client"], 0)} Гц — без нормализации роли не различались бы. '
              'Голос один (`default`), различие ролей — только высота тона и темп; тембр остаётся случайным, поэтому разделение спикеров проверено только на этой искусственно разведённой паре и на реальных звонках может вести себя иначе.', '']
        s = ck['kz_summary']
        L += ['### Казахский TTS: круговой тест через `h200-whisperx-kk`', '',
              'Чистый звук (без телефонного тракта), язык `kk`. Доля слов с казахскими буквами (әғқңөұүһі) в сценарии и в распознанном тексте; CER к сценарию.', '',
              '| диалог | доля в сценарии | доля в ASR | CER | WER |', '|---|---:|---:|---:|---:|']
        for cid, v in ck['kz'].items():
            L.append(f'| {cid} | {fmt(v["script_kz_share"], 2)} | {fmt(v["asr_kz_share"], 2)} | {fmt(v["cer"])} | {fmt(v["wer"])} |')
        L += ['', f'Среднее: сценарий {fmt(s["script_share_mean"], 2)}, ASR {fmt(s["asr_share_mean"], 2)}, CER {fmt(s["cer_mean"])}.', '']
    return '\n'.join(L) + '\n'


def cmd_report(args: argparse.Namespace) -> int:
    res = build_results()
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(res, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    text = render_report(res)
    if REPORT.exists() and '<!-- manual -->' in REPORT.read_text(encoding='utf-8'):
        manual = REPORT.read_text(encoding='utf-8').split('<!-- manual -->', 1)[1]
        text += '<!-- manual -->' + manual
    REPORT.write_text(text, encoding='utf-8', newline='\n')
    print(text)
    return 0


# ---------------------------------------------------------------- checks: speaker distinctness, Kazakh TTS round trip

CHECKS = DATA / 'checks.json'


def median_f0(samples: array.array, rate: int, max_frames: int = 120) -> float | None:
    """Median autocorrelation F0 (70-400 Hz) over the loudest voiced 40 ms frames (pure Python, enough for a speaker comparison)."""
    n = int(rate * 0.04)
    frames = []
    for i in range(0, len(samples) - n, n):
        fr = samples[i:i + n]
        mean_v = sum(fr) / n
        fr = [x - mean_v for x in fr]
        frames.append((sum(x * x for x in fr), fr))
    frames.sort(key=lambda f: -f[0])
    f0s = []
    for e, fr in frames[:max_frames]:
        if e / n < 400 ** 2:
            break
        lo, hi = int(rate / 400), int(rate / 70)
        ac = [sum(fr[j] * fr[j + lag] for j in range(n - lag)) for lag in range(lo, hi)]
        peak = max(ac)
        k = next(i for i in range(len(ac)) if ac[i] >= 0.9 * peak and (i == 0 or ac[i] >= ac[i - 1]) and (i == len(ac) - 1 or ac[i] >= ac[i + 1]))
        if ac[k] > 0.5 * e:
            f0s.append(rate / (lo + k))
    return statistics.median(f0s) if len(f0s) >= 10 else None


async def cmd_checks(args: argparse.Namespace) -> int:
    dialogs = load_scripts()
    checks: dict[str, Any] = {'f0': {}, 'kz': {}}
    # 1) the two speakers of the same dialog differ in F0 after the per-role shift
    for lang in ('RU', 'KZ', 'EN'):
        for d in [x for x in dialogs if x['language'] == lang][:2]:
            samples = pcm_from(MASTER_DIR / f'{d["id"]}.wav', 'anull', 16000)
            tm = json.loads((TIMING_DIR / f'{d["id"]}.json').read_text(encoding='utf-8'))['turns']
            per: dict[str, array.array] = {}
            for t in tm:
                per.setdefault(t['speaker'], array.array('h')).extend(samples[int(t['start'] * 16000):int(t['end'] * 16000)])
            checks['f0'][d['id']] = {sp: median_f0(a, 16000) for sp, a in per.items()}
            turn_f0: dict[str, list[float]] = {}
            for t in tm:
                f = median_f0(samples[int(t['start'] * 16000):int(t['end'] * 16000)], 16000, 40)
                if f:
                    turn_f0.setdefault(t['speaker'], []).append(f)
            checks.setdefault('f0_turn_range', {})[d['id']] = {sp: [min(v), max(v)] for sp, v in turn_f0.items()}
    # unshifted reference: the raw TTS output of the first operator turn and first client turn
    raw = {}
    for sp in ('operator', 'client'):
        d = next(x for x in dialogs if x['language'] == 'RU')
        i = next(i for i, t in enumerate(d['turns']) if t['speaker'] == sp)
        raw[sp] = median_f0(pcm_from(TTS_DIR / d['id'] / f'{i:02d}.wav', 'anull', 16000), 16000, 60)
    checks['f0_unshifted_ru_first_turns'] = raw
    # 2) Kazakh TTS round trip: clean (no telephony chain) audio through whisperx forced to kk
    from server.asr.providers import kazakh_share
    provider = load_asr_providers()['h200-whisperx-kk']
    for d in [x for x in dialogs if x['language'] == 'KZ']:
        mp3 = CLEAN_DIR / f'{d["id"]}.mp3'
        if not mp3.exists():
            await asyncio.to_thread(clean_audio, d['id'], MASTER_DIR / f'{d["id"]}.wav')
        cache = RAW_DIR / 'kzcheck' / f'{d["id"]}.json'
        if cache.exists():
            result = AsrResult.model_validate_json(cache.read_text(encoding='utf-8'))
        else:
            result = await transcribe(provider, mp3.read_bytes(), mp3.name, language='kk')
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(result.model_dump_json(indent=1), encoding='utf-8')
        ref = ' '.join(t['text'] for t in d['turns'])
        hyp = hyp_text(result)
        checks['kz'][d['id']] = {'script_kz_share': kazakh_share(ref), 'asr_kz_share': kazakh_share(hyp), 'cer': cer(ref, hyp), 'wer': wer(ref, hyp)}
        print(f'  {d["id"]}: {checks["kz"][d["id"]]}')
    kz = checks['kz']
    checks['kz_summary'] = {
        'script_share_mean': mean([v['script_kz_share'] for v in kz.values()]),
        'asr_share_mean': mean([v['asr_kz_share'] for v in kz.values()]),
        'cer_mean': mean([v['cer'] for v in kz.values()]),
    }
    CHECKS.write_text(json.dumps(checks, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({k: checks[k] for k in ('f0', 'f0_unshifted_ru_first_turns', 'kz_summary')}, ensure_ascii=False, indent=1))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('scripts')
    p.add_argument('--force', action='store_true')
    p.add_argument('--only', nargs='*')
    p = sub.add_parser('tts')
    p.add_argument('--only', nargs='*')
    p = sub.add_parser('asr')
    p.add_argument('--providers', nargs='*')
    p.add_argument('--only', nargs='*')
    p.add_argument('--no-ablation', action='store_true')
    p = sub.add_parser('judge')
    p.add_argument('--providers', nargs='*')
    sub.add_parser('checks')
    sub.add_parser('report')
    args = ap.parse_args(argv)
    if args.cmd == 'report':
        return cmd_report(args)
    return asyncio.run({'scripts': cmd_scripts, 'tts': cmd_tts, 'asr': cmd_asr, 'judge': cmd_judge, 'checks': cmd_checks}[args.cmd](args))


if __name__ == '__main__':
    raise SystemExit(main())
