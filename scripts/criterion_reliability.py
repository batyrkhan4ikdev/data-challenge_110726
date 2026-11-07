"""Per-criterion agreement with the DEV gold from a bench summary -> data/criterion_reliability.json.

Usage: python scripts/criterion_reliability.py [summary.md] [out.json]
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = ROOT / 'bench' / 'results' / '20261107-213616' / 'summary.md'
DEFAULT_OUT = ROOT / 'data' / 'criterion_reliability.json'
THRESHOLD = 0.85


def parse(text: str) -> dict[str, dict]:
    block = text.split('Per criterion:', 1)[1]
    out: dict[str, dict] = {}
    header: list[str] | None = None
    for line in block.splitlines():
        if not line.startswith('|'):
            if out:
                break
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if header is None:
            header = cells
            continue
        if set(line) <= set('|- '):
            continue
        row = dict(zip(header, cells))
        if re.fullmatch(r'c\d+', row['criterion']):
            out[row['criterion']] = {'agree': float(row['agree']), 'n': int(row['n'])}
    return out


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT
    crit = parse(src.read_text(encoding='utf-8'))
    if not crit:
        raise SystemExit(f'no per-criterion rows in {src}')
    rel = src.resolve().relative_to(ROOT).as_posix() if src.resolve().is_relative_to(ROOT) else str(src)
    dst.write_text(
        json.dumps({'source': rel, 'threshold': THRESHOLD, 'criteria': crit}, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )
    print(f'{len(crit)} criteria -> {dst}')


if __name__ == '__main__':
    main()
