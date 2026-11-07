"""Verify a RegPack ZIP offline: `python scripts/verify_regpack.py <zip>`; exit 1 on mismatch."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server.regpack import verify_regpack  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: verify_regpack.py <regpack.zip>', file=sys.stderr)
        return 2
    res = verify_regpack(Path(sys.argv[1]).read_bytes())
    print(res['selfcheck'])
    for p in res['problems']:
        print('FAIL:', p)
    print('OK' if res['ok'] else 'MISMATCH')
    return 0 if res['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
