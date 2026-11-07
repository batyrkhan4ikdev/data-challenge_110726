"""Push main to origin with retries, then prove the commit is on GitHub.

    python scripts/push_with_retry.py [--minutes 10]

This network drops GitHub for ~20 s at a time (port 443 timeouts; port 22 is blocked), so one failed push means
nothing. Retries with backoff until the deadline, rebases if a teammate pushed in between, and exits 0 only when
`git ls-remote origin main` reports the local HEAD. Git never prompts (GIT_TERMINAL_PROMPT=0) and every call has a
timeout, so a missing credential fails fast instead of hanging.
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = {**os.environ, 'GIT_TERMINAL_PROMPT': '0'}


def git(*args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(['git', *args], cwd=ROOT, env=ENV, capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args, 124, '', f'git {args[0]}: timed out after {timeout}s')


def remote_head() -> str | None:
    out = git('ls-remote', 'origin', 'refs/heads/main')
    return out.stdout.split()[0] if out.returncode == 0 and out.stdout.strip() else None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--minutes', type=float, default=10)
    args = p.parse_args(argv)
    deadline = time.monotonic() + args.minutes * 60
    delay = 5
    while True:
        head = git('rev-parse', 'HEAD').stdout.strip()
        push = git('push', '-q', 'origin', 'HEAD:main', timeout=90)
        if push.returncode != 0:
            print(f'push: {(push.stderr or push.stdout).strip()[:200]}')
        remote = remote_head()
        if remote == head:
            print(f'PUSHED {head} (origin/main confirmed by ls-remote)')
            return 0
        if git('fetch', '-q', 'origin').returncode == 0 and \
                git('merge-base', '--is-ancestor', 'origin/main', 'HEAD').returncode != 0:
            print('origin/main moved; rebasing onto it')
            if git('pull', '-q', '--rebase', 'origin', 'main', timeout=120).returncode != 0:
                print('REBASE CONFLICT: resolve it, then rerun')
                return 2
            continue
        if time.monotonic() >= deadline:
            print(f'NOT PUSHED after {args.minutes:g} min: HEAD {head}, origin/main {remote or "unreachable"}')
            print('Fallback: send results/prod/results.json to a teammate on another network to commit and push.')
            return 1
        print(f'not confirmed yet (origin/main={remote or "unreachable"}); retry in {delay}s')
        time.sleep(delay)
        delay = min(delay * 2, 30)


if __name__ == '__main__':
    sys.exit(main())
