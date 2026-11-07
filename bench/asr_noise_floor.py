"""ASR -> judge noise floor: how much do verdicts move when only the transcript source changes?

    python -m bench.asr_noise_floor [--profile h200-gemma] [--out bench/asr/noise-floor.md]

Evaluates every voice call of every `data/calls/*.dev.json` source with the default judge (per_criterion, k=1) and
compares with the FreedomSpeech reference transcript (`freedomspeech.dev.json`, hand-checked): verdict flips over
all (call, criterion) cells and mean absolute difference of the total. The reference is evaluated twice; its
second run is the pure model-noise row (same transcript, different run). Numbers only, no transcript text.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
from pathlib import Path

import server  # noqa: F401  (loads .env)
from server.config import default_profile, load_profiles
from server.dataset import normalize_response
from server.evaluator import evaluate
from server.llm.client import make_client

from bench.sets import checklist_for

ROOT = Path(__file__).resolve().parent.parent
CALLS_DIR = ROOT / "data" / "calls"
REFERENCE = "freedomspeech"
OUT = ROOT / "bench" / "asr" / "noise-floor.md"


async def score(records, profile, llm, concurrency: int = 4) -> dict[str, tuple[dict[str, str], float | None]]:
    sem = asyncio.Semaphore(concurrency)

    async def one(cid: str, record):
        for attempt in range(3):
            try:
                async with sem:
                    ev, _ = await evaluate(record, checklist_for(record), profile=profile, mode="per_criterion", k=1, llm=llm)
                return cid, ({it.criterion_id: it.verdict for it in ev.items}, ev.score.total)
            except Exception as e:  # noqa: BLE001
                print(f"  {cid}: {type(e).__name__}: {str(e)[:100]}", file=sys.stderr)
                await asyncio.sleep(2 * (attempt + 1))
        return cid, None

    out = await asyncio.gather(*(one(c, r) for c, r in records.items()))
    return {cid: v for cid, v in out if v is not None}


def compare(ref: dict, other: dict) -> tuple[int, int, float | None, int]:
    flips = cells = 0
    diffs: list[float] = []
    calls = 0
    for cid in ref.keys() & other.keys():
        rv, rt = ref[cid]
        ov, ot = other[cid]
        calls += 1
        for crit in rv.keys() & ov.keys():
            cells += 1
            flips += rv[crit] != ov[crit]
        if rt is not None and ot is not None:
            diffs.append(abs(rt - ot))
    return flips, cells, statistics.fmean(diffs) if diffs else None, calls


async def main_async(args) -> int:
    profile = load_profiles()[args.profile] if args.profile else default_profile()
    llm = make_client(profile)
    sources: dict[str, dict] = {}
    for path in sorted(CALLS_DIR.glob("*.dev.json")):
        recs = [r for r in normalize_response(json.loads(path.read_text(encoding="utf-8")), "DEV") if r.channel == "voice call"]
        sources[path.name.removesuffix(".dev.json")] = {r.conversation_id: r for r in recs}
    if REFERENCE not in sources:
        print(f"нет эталонного источника {REFERENCE}", file=sys.stderr)
        return 2
    results = {}
    for name, recs in sources.items():
        print(f"оценка {name}: {len(recs)} звонков")
        results[name] = await score(recs, profile, llm)
    print("повторная оценка эталона")
    rerun = await score(sources[REFERENCE], profile, llm)

    ref = results[REFERENCE]
    rows = [("**" + REFERENCE + " (повторный прогон, шум модели)**", compare(ref, rerun))]
    rows += [(n, compare(ref, r)) for n, r in results.items() if n != REFERENCE]
    lines = [
        "# ASR -> судья: пол шума (#48)",
        "",
        f"Судья: `{profile.name}` · per_criterion · k=1. Источники — `data/calls/*.dev.json`, эталон — `{REFERENCE}` (проверен вручную). "
        "Звонки: 5 DEV-звонков, 8 критериев каждый. Флип — вердикт критерия отличается от вердикта на эталонном транскрипте. "
        "Текст транскриптов в отчёт не попадает.",
        "",
        "| источник | звонков | флипов вердикта | из ячеек | доля | MAE итога vs эталон |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, (flips, cells, mae, calls) in rows:
        share = f"{flips / cells:.3f}" if cells else "—"
        lines.append(f"| {name} | {calls} | {flips} | {cells} | {share} | {'—' if mae is None else f'{mae:.2f}'} |")
    lines += [
        "",
        "Первая строка — тот же транскрипт, оценённый второй раз: это нижняя граница шума. Всё, что источники дают сверх неё, — вклад качества ASR.",
        "",
    ]
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile")
    ap.add_argument("--out", type=Path, default=OUT)
    return asyncio.run(main_async(ap.parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
