"""Pre-flight for the control run: everything `run_batch.py <GROUP> --refresh --submit prod` needs, checked in ~30 s.

    python scripts/preflight.py [--group <CONTROL_GROUP>]

Checks: .env keys, git state (main, clean, in sync with origin), default checklists equal to
data/checklists/*.default.json, the dataset API (DEV, plus the control group if given: expects 10 records),
and one real completion from the primary model and from each fallback. Exit 1 if anything fails.
"""

import argparse
import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from server.checklists import ChecklistStore  # noqa: E402
from server.config import ConfigError, Profile, load_profiles  # noqa: E402
from server.dataset import DatasetError, load_dataset  # noqa: E402
from server.llm.client import LLMError, make_client  # noqa: E402

SEED = Path('data/checklists')
PING_SCHEMA = {
    'type': 'object',
    'properties': {'ok': {'type': 'boolean'}},
    'required': ['ok'],
    'additionalProperties': False,
}
results: list[tuple[bool, str]] = []


def report(ok: bool, what: str) -> None:
    results.append((ok, what))
    print(f'{"PASS" if ok else "FAIL"}  {what}')


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(['git', *args], capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60)


def check_env(profiles: dict[str, Profile]) -> list[Profile]:
    """Report missing keys; return [primary, *fallbacks] profiles in FALLBACK_PROFILE order."""
    missing = [k for k in ('DATASET_URL', 'TEAM_NAME', 'LLM_PROFILE', 'EVAL_MODE', 'EVAL_K', 'FALLBACK_PROFILE')
               if not os.environ.get(k)]
    report(not missing, '.env keys set' + (f' — missing {missing}' if missing else ''))
    print(f'      LLM_PROFILE={os.environ.get("LLM_PROFILE")} EVAL_MODE={os.environ.get("EVAL_MODE")} '
          f'EVAL_K={os.environ.get("EVAL_K")} FALLBACK_PROFILE={os.environ.get("FALLBACK_PROFILE")} '
          f'TEAM_NAME={os.environ.get("TEAM_NAME")!r}')
    names = [os.environ.get('LLM_PROFILE') or '']
    names += [n.strip() for n in (os.environ.get('FALLBACK_PROFILE') or '').split(',') if n.strip()]
    used = []
    for name in names:
        if name not in profiles:
            report(False, f'profile {name!r} (LLM_PROFILE / FALLBACK_PROFILE) is not in config/profiles.toml')
            continue
        used.append(profiles[name])
    return used


def check_git() -> None:
    branch = git('rev-parse', '--abbrev-ref', 'HEAD').stdout.strip()
    report(branch == 'main', f'git branch is main (got {branch!r})')
    dirty = [line.strip() for line in git('status', '--porcelain', '--untracked-files=no').stdout.splitlines()
             if line.strip()]
    report(not dirty, 'no uncommitted changes to tracked files' + (f' — {dirty[:5]}' if dirty else ''))
    if git('fetch', '-q', 'origin').returncode != 0:
        report(False, 'git fetch origin failed (GitHub unreachable?): the prod file must be PUSHED before stop-code')
        return
    ahead, behind = git('rev-list', '--left-right', '--count', 'HEAD...origin/main').stdout.split()
    report(ahead == behind == '0', f'main in sync with origin/main (ahead {ahead}, behind {behind})')


async def check_checklists() -> None:
    store = ChecklistStore(Path('data/store/checklists'))
    await store.seed_defaults(SEED)
    drift = await store.seed_drift(SEED, ['agent chat', 'voice call'])
    report(not drift, 'default checklists equal data/checklists/*.default.json' + ''.join(
        f' — {c.id} v{c.version} differs: run_batch --submit needs --reset-defaults' for c, _ in drift))


async def check_dataset(group: str, expect: int | None) -> None:
    rejects: dict[str, str] = {}
    t = time.perf_counter()
    try:
        records = await load_dataset(group, refresh=True, rejects=rejects)
    except DatasetError as e:
        report(False, f'dataset {group}: {e}')
        return
    chats = sum(r.channel == 'agent chat' for r in records)
    wrong_count = expect is not None and len(records) != expect
    report(not rejects and not wrong_count,
           f'dataset {group}: {len(records)} records ({chats} chats), {len(rejects)} unparseable, '
           f'{time.perf_counter() - t:.1f}s' + (f' — expected {expect}' if wrong_count else ''))
    for cid, reason in rejects.items():
        print(f'      {cid}: {reason}')


async def model_answers(profile: Profile) -> bool:
    if profile.provider == 'ensemble':
        # An ensemble has no endpoint of its own: every member must answer for the vote to be complete.
        answers = [await model_answers(member) for member, _ in profile.member_profiles()]
        return all(answers)
    t = time.perf_counter()
    try:
        out = await make_client(profile).complete(
            [{'role': 'user', 'content': 'Верни JSON {"ok": true}.'}], PING_SCHEMA, 0.0, 1
        )
    except (ConfigError, LLMError) as e:
        print(f'      {profile.name}: {str(e)[:200]}')
        return False
    ok = bool(out) and 'true' in (out[0].text or '').lower()
    print(f'      {profile.name} ({profile.model}): {"ok" if ok else "unexpected answer"}, {time.perf_counter() - t:.1f}s')
    return ok


async def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description='Pre-flight checks for the control run.')
    p.add_argument('--group', help='control group_id, once announced: must return exactly 10 records')
    args = p.parse_args(argv)
    used = check_env(load_profiles())
    check_git()
    await check_checklists()
    await check_dataset('DEV', None)
    if args.group:
        await check_dataset(args.group, 10)
    if used:
        primary, *fallbacks = used
        report(await model_answers(primary), f'primary model {primary.name} answers')
        alive = [f.name for f in fallbacks if await model_answers(f)]
        report(bool(alive), f'at least one fallback answers: {", ".join(alive) or "none"} of '
                            f'{", ".join(f.name for f in fallbacks) or "none configured"}')
    failed = [w for ok, w in results if not ok]
    print(f'\n{len(results) - len(failed)}/{len(results)} passed' + (' — fix the FAIL lines first' if failed else ''))
    return 1 if failed else 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(asyncio.run(main()))
