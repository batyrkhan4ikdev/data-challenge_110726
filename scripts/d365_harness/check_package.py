"""Run after tsc. Every mutation is confined to a temporary copy of web/."""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    with tempfile.TemporaryDirectory(prefix='cqa-d365-package-') as temp:
        base = Path(temp)
        web = base / 'web'
        shutil.copytree(ROOT / 'web', web, ignore=shutil.ignore_patterns('node_modules'))
        command = [sys.executable, str(ROOT / 'scripts/package_d365.py'), '--web', str(web), '--output', str(base / 'out')]

        def check(label: str, expected: str | None) -> None:
            result = subprocess.run(command, capture_output=True, text=True)
            if expected is None:
                assert result.returncode == 0, result.stderr
            else:
                assert result.returncode != 0 and expected in result.stderr, result.stdout + result.stderr
            print(f'PASS {label}: exit={result.returncode}' + (f' {result.stderr.strip()}' if result.stderr else ''))

        check('valid copy', None)
        for name, expected in [('bad-name.js', 'Invalid web resource name'), ('debug.map', 'Unsupported resource extension'), ('font.woff2', 'Unsupported resource extension'), ('old.js', 'Unexpected dist resource')]:
            path = web / 'dist' / name
            path.write_text('export {};', encoding='utf-8')
            check(name, expected)
            path.unlink()

        css = web / 'cqa.css'
        original = css.read_text(encoding='utf-8')
        for label, addition, expected in [
            ('global selector', '\nbody { margin: 0; }', 'CSS selector outside .cqa'),
            ('grouped global selector', '\n@media (min-width: 1px) { html { color: red; } }', 'CSS selector outside .cqa'),
            ('escaped scope', '\n.cqa + body { color: red; }', 'CSS selector outside .cqa'),
            ('absolute CSS URL', '\n.cqa { background: url(/assets/logo.svg); }', 'Root-absolute resource URL'),
            ('absolute static URL', '\n/* /static/main.js */', 'Root-absolute resource URL'),
        ]:
            css.write_text(original + addition, encoding='utf-8')
            check(label, expected)
        css.write_text(original, encoding='utf-8')
        check('restored scoped stylesheet', None)

        oversized = web / 'assets' / 'large.svg'
        with oversized.open('wb') as stream:
            stream.truncate(5_000_000)
        check('5 MB boundary', 'smaller than 5 MB')
        oversized.unlink()

        module = web / 'dist/main.js'
        before = module.stat()
        os.utime(module, ns=(before.st_atime_ns, 0))
        check('stale module', 'Run the build first')
        os.utime(module, ns=(before.st_atime_ns, before.st_mtime_ns))
        module.unlink()
        check('missing module', 'Run the build first')
        shutil.rmtree(web / 'dist')
        check('missing build', 'web/dist is missing')


if __name__ == '__main__':
    main()
