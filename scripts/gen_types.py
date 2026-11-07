import json
import subprocess
import sys
from pathlib import Path

from pydantic.json_schema import models_json_schema

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from server.models import ALL_MODELS  # noqa: E402


def main() -> int:
    _, schema = models_json_schema([(m, 'serialization') for m in ALL_MODELS])
    out = ROOT / 'contracts' / 'schema.json'
    out.write_text(json.dumps({'$defs': schema['$defs']}, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    (ROOT / 'web' / 'src').mkdir(parents=True, exist_ok=True)
    cmd = 'npx --prefix web json2ts -i contracts/schema.json -o web/src/types.gen.ts --unreachableDefinitions'
    windows = sys.platform == 'win32'
    return subprocess.run(cmd if windows else cmd.split(), cwd=ROOT, shell=windows).returncode


if __name__ == '__main__':
    sys.exit(main())
