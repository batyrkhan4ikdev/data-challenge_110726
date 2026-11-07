"""Evaluate a whole dataset group with the same store and JobRunner as the app.

    python scripts/run_batch.py <group_id> [--refresh] [--checklist auto|<id>] [--profile P] [--mode M] [--k K]
                                [--fallback-profile P] [--submit dev|prod --team-name NAME]

Prints one row per dialog plus token, time and cost totals, writes `out/<group_id>.results.json` and
`out/<group_id>.results.csv`, and keeps every evaluation in `data/store` so the UI shows it. With
`--submit`, also writes the organizer file `results/<dev|prod>/results.json` and validates it.
"""

import argparse
import asyncio
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import get_args

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from server.checklists import ChecklistStore  # noqa: E402
from server.config import Profile, load_profiles  # noqa: E402
from server.dataset import DatasetError, load_dataset  # noqa: E402
from server.jobs import JobRunner, fallback_names, resolve_settings  # noqa: E402
from server.models import BatchRequest, Evaluation, Mode, Record  # noqa: E402
from server.store import NotFound, Store  # noqa: E402
from server import submission  # noqa: E402

STORE = Path('data/store')
SEED = Path('data/checklists')
OUT = Path('out')
RESULTS = Path('results')


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Batch-evaluate a dataset group.')
    p.add_argument('group_id')
    p.add_argument('--refresh', action='store_true', help='refetch the dataset instead of using data/cache')
    p.add_argument('--checklist', default='auto', help='"auto" picks the default by channel, else a checklist id')
    p.add_argument('--profile', help='model profile from config/profiles.toml (default: env LLM_PROFILE or fake)')
    p.add_argument('--mode', choices=get_args(Mode), help='default: env EVAL_MODE or single')
    p.add_argument('--k', type=int, help='samples per criterion (default: env EVAL_K or 1)')
    p.add_argument(
        '--fallback-profile',
        default=os.environ.get('FALLBACK_PROFILE') or None,
        help='comma-separated profiles, tried in order on dialogs that still fail (default: env FALLBACK_PROFILE)',
    )
    p.add_argument('--submit', choices=['dev', 'prod'], help='also write results/<set>/results.json for the organizers')
    p.add_argument('--team-name', default=os.environ.get('TEAM_NAME') or None,
                   help='team_name in results.json (default: env TEAM_NAME)')
    p.add_argument('--reset-defaults', action='store_true',
                   help='with --submit: if a default checklist was edited, save data/checklists/*.default.json '
                        'back as its new version (history is kept) instead of aborting')
    return p.parse_args(argv)


def cost_usd(profile: Profile, evs: list[Evaluation]) -> float | None:
    """Cost via the profile cost model: GPU-hours shared across `concurrency`, or token prices."""
    cost = profile.cost
    if cost is None:
        return None
    if cost.kind == 'gpu':
        seconds = sum(e.usage.seconds for e in evs)
        return cost.usd_per_hour * seconds / max(cost.concurrency, 1) / 3600
    return sum(
        e.usage.prompt_tokens * cost.usd_per_mtok_in / 1e6 + e.usage.completion_tokens * cost.usd_per_mtok_out / 1e6
        for e in evs
    )


def result_row(ev: Evaluation, record: Record) -> dict:
    return {
        'conversation_id': ev.conversation_id,
        'channel': record.channel,
        'language': record.language,
        'checklist_id': ev.checklist_id,
        'checklist_version': ev.checklist_version,
        'profile': ev.profile,
        'model': ev.model,
        'total': ev.score.total,
        'gross_error': ev.score.gross_error,
        'items': [
            {
                'criterion_id': i.criterion_id,
                'verdict': i.verdict,
                'explanation': i.explanation,
                'evidence_idx': i.evidence_idx,
                'expected_range': list(i.expected_range) if i.expected_range else None,
                'na_reason': i.na_reason,
            }
            for i in ev.items
        ],
    }


def print_table(rows: list[list[str]]) -> None:
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    for n, r in enumerate(rows):
        print('  '.join(cell.ljust(w) for cell, w in zip(r, widths)).rstrip())
        if n == 0:
            print('  '.join('-' * w for w in widths))


def fmt_total(value: float | None) -> str:
    return '—' if value is None else f'{value:.2f}'


def write_outputs(
    group_id: str, records: list[Record], evs: dict[str, Evaluation], failed: dict[str, str]
) -> tuple[Path, Path]:
    OUT.mkdir(exist_ok=True)
    results = [result_row(evs[r.conversation_id], r) for r in records if r.conversation_id in evs]
    json_path = OUT / f'{group_id}.results.json'
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')

    criteria: list[str] = []
    for ev in evs.values():
        for i in ev.items:
            if i.criterion_id not in criteria:
                criteria.append(i.criterion_id)
    criteria.sort()
    csv_path = OUT / f'{group_id}.results.csv'
    with csv_path.open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['conversation_id', 'channel', 'language', 'checklist_id', 'checklist_version', 'profile', *criteria,
                    'total', 'gross_error', 'error'])
        for r in records:
            ev = evs.get(r.conversation_id)
            verdicts = {i.criterion_id: i.verdict for i in ev.items} if ev else {}
            w.writerow([
                r.conversation_id, r.channel, r.language,
                ev.checklist_id if ev else '', ev.checklist_version if ev else '', ev.profile if ev else '',
                *(verdicts.get(c, '') for c in criteria),
                '' if ev is None or ev.score.total is None else ev.score.total,
                '' if ev is None else ev.score.gross_error,
                failed.get(r.conversation_id, ''),
            ])
        known = {r.conversation_id for r in records}
        for cid, reason in failed.items():  # records the loader could not parse
            if cid not in known:
                w.writerow([cid, '', '', '', '', '', *('' for _ in criteria), '', '', reason])
    return json_path, csv_path


async def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.submit and not (args.team_name or '').strip():
        print('ошибка: --submit требует --team-name или env TEAM_NAME', file=sys.stderr)
        return 2
    req = BatchRequest(
        group_id=args.group_id,
        conversation_ids=[],
        checklist_id=None if args.checklist == 'auto' else args.checklist,
        profile=args.profile,
        mode=args.mode,
        k=args.k,
    )
    profiles = load_profiles()
    try:
        profile, mode, k = resolve_settings(req, profiles)
    except ValueError as e:
        print(f'ошибка: {e}', file=sys.stderr)
        return 2
    try:
        fallbacks = fallback_names(args.fallback_profile, profiles)
    except ValueError as e:
        print(f'ошибка: {e}', file=sys.stderr)
        return 2
    rejects: dict[str, str] = {}
    try:
        records = await load_dataset(args.group_id, args.refresh, rejects=rejects)
    except DatasetError as e:
        print(f'Датасет недоступен: {e}', file=sys.stderr)
        return 2
    for cid, reason in rejects.items():
        print(f'skipped {cid}: {reason}', file=sys.stderr)

    store = Store(STORE)
    checklists = ChecklistStore(STORE / 'checklists')
    await checklists.seed_defaults(SEED)
    if args.submit and args.checklist == 'auto':
        drift = await checklists.seed_drift(SEED, {r.channel for r in records})
        for current, seed in drift:
            if args.reset_defaults:
                restored = await checklists.save(seed)
                print(f'restored {seed.id} from {SEED.as_posix()}/{seed.id}.default.json as v{restored.version} '
                      f'(was {current.id} v{current.version})')
            else:
                print(f'ошибка: для «{seed.channel_default}» сейчас действует {current.id} v{current.version}, а он '
                      f'отличается от {SEED.as_posix()}/{seed.id}.default.json. Сдача оценивается по чек-листу '
                      f'организаторов: перезапустите с --reset-defaults.', file=sys.stderr)
        if drift and not args.reset_defaults:
            return 2
    runner = JobRunner(store, checklists, profiles, fallbacks)
    req.conversation_ids = [r.conversation_id for r in records]
    print(f'{args.group_id}: {len(records)} dialogs · profile {profile.name} ({profile.model}) · {mode} · k={k}'
          f' · fallbacks {", ".join(fallbacks) or "none"}')

    t0 = time.perf_counter()
    evs: dict[str, Evaluation] = {}
    failed: dict[str, str] = {}
    if records:
        try:
            job = await runner.start(req, {r.conversation_id: r for r in records})
        except NotFound as e:
            print(f'ошибка: {e}', file=sys.stderr)
            return 2
        job = await runner.wait(job.id)
        evs = {ev.conversation_id: ev for ev in [await store.get_evaluation(i) for i in job.evaluation_ids]}
        failed = dict(job.failed)
    failed.update(rejects)  # unparseable records stay visible as errors; never dropped, never zeroed
    wall = time.perf_counter() - t0

    rows = [['id', 'channel', 'lang', 'total', 'gross', 'profile', 'error']]
    for r in records:
        ev = evs.get(r.conversation_id)
        rows.append([
            r.conversation_id,
            r.channel,
            r.language,
            fmt_total(ev.score.total) if ev else '',
            ('yes' if ev.score.gross_error else 'no') if ev else '',
            ev.profile if ev else '',
            failed.get(r.conversation_id, ''),
        ])
    rows += [[cid, '', '', '', '', '', reason] for cid, reason in rejects.items()]
    print_table(rows)

    done = list(evs.values())
    prompt = sum(e.usage.prompt_tokens for e in done)
    completion = sum(e.usage.completion_tokens for e in done)
    model_seconds = sum(e.usage.seconds for e in done)
    print()
    print(f'evaluated {len(done)}/{len(records) + len(rejects)}, failed {len(failed)}')
    print(f'tokens: prompt {prompt}, completion {completion}, total {prompt + completion}')
    print(f'seconds: wall {wall:.1f}, summed per dialog {model_seconds:.1f}')
    for name in sorted({e.profile for e in done}):
        group = [e for e in done if e.profile == name]
        cost = cost_usd(profiles[name], group)
        print(f'cost: {"n/a (no cost model)" if cost is None else f"${cost:.4f}"} ({name}, {len(group)} dialogs)')

    json_path, csv_path = write_outputs(args.group_id, records, evs, failed)
    print(f'wrote {json_path.as_posix()} and {csv_path.as_posix()}')
    if args.submit:
        ids = [r.conversation_id for r in records] + list(rejects)
        problems = write_submission(args.submit, args.team_name, ids, evs, failed, profiles, profile)
        if problems:
            return 1
    return 1 if failed else 0


def write_submission(
    which: str, team_name: str, ids: list[str], evs: dict[str, Evaluation], failed: dict[str, str],
    profiles: dict[str, Profile], primary: Profile,
) -> list[str]:
    """Write results/<which>/results.json; print and return validation problems (the file is written anyway)."""
    doc = submission.build(team_name.strip(), ids, evs, failed, profiles, primary)
    path = RESULTS / which / 'results.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    # tmp + replace: a run killed mid-write must not leave a truncated file where a good one was
    atomic_write(path, json.dumps(doc, ensure_ascii=False, indent=2) + '\n')
    problems = submission.validate(json.loads(path.read_text(encoding='utf-8')), ids)
    errors = sum(r['status'] == 'error' for r in doc['results'])
    print(f'wrote {path.as_posix()}: {len(doc["results"])} entries, {errors} errors, model {doc["model"]}')
    for p in problems:
        print(f'  INVALID: {p}', file=sys.stderr)
    if not problems:
        print('  valid against the appendix format 1.0')
    return problems


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(asyncio.run(main()))
