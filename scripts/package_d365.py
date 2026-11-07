"""Build validated Dataverse resources using only the standard library."""
import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOWED = {'.htm', '.html', '.css', '.js', '.png', '.jpg', '.gif', '.svg', '.ico', '.xml', '.xsl', '.resx'}
NAME = re.compile(r'^[A-Za-z0-9.]+(/[A-Za-z0-9.]+)*$')
BUILD = 'Run the build first: tsc -p web (or web/node_modules/.bin/tsc -p web).'


def split_selectors(prelude: str) -> list[str]:
    """Split a selector list on top-level commas: commas inside :is(...), :not(...) or [...] stay in place."""
    parts: list[str] = []
    depth = 0
    quote = ''
    start = 0
    for i, char in enumerate(prelude):
        if quote:
            if char == quote:
                quote = ''
        elif char in "\"'":
            quote = char
        elif char in '([':
            depth += 1
        elif char in ')]':
            depth -= 1
        elif char == ',' and depth == 0:
            parts.append(prelude[start:i])
            start = i + 1
    parts.append(prelude[start:])
    return parts


def check_css(css: str) -> None:
    """Check rule preludes, including rules nested inside grouping at-rules.

    Strings/comments are skipped by the scanner, so braces in data URLs and
    generated content cannot be mistaken for rule boundaries. Unknown at-rules
    and CSS nesting fail closed rather than bypassing the scope check.
    """
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)

    def rules(start: int, end: int, keyframes: bool = False) -> None:
        pos = start
        while pos < end:
            while pos < end and css[pos].isspace():
                pos += 1
            if pos == end:
                return
            begin = pos
            quote = ''
            while pos < end:
                char = css[pos]
                if quote:
                    if char == '\\':
                        pos += 2
                        continue
                    if char == quote:
                        quote = ''
                elif char in "\"'":
                    quote = char
                elif char == '{':
                    break
                elif char in ';}':
                    raise ValueError(f'Unsupported CSS rule: {css[begin:pos + 1].strip()}')
                pos += 1
            if pos == end:
                raise ValueError('Unterminated CSS rule')
            prelude = css[begin:pos].strip()
            body = pos + 1
            depth = 1
            pos += 1
            quote = ''
            while pos < end and depth:
                char = css[pos]
                if quote:
                    if char == '\\':
                        pos += 2
                        continue
                    if char == quote:
                        quote = ''
                elif char in "\"'":
                    quote = char
                elif char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                pos += 1
            if depth:
                raise ValueError('Unbalanced CSS braces')
            if re.match(r'@(?:media|supports|container|layer)\b', prelude):
                rules(body, pos - 1)
            elif re.match(r'@(?:-webkit-)?keyframes\b', prelude):
                rules(body, pos - 1, keyframes=True)
            elif prelude == '@font-face':
                pass
            elif prelude.startswith('@'):
                raise ValueError(f'Unsupported CSS at-rule: {prelude}')
            elif not keyframes:
                for selector in split_selectors(prelude):
                    selector = selector.strip()
                    root = re.match(r'^\.cqa(?:[.#][\w-]+|:{1,2}[\w-]+(?:\([^()]*\))?|\[[^\]]*\])*(?=\s|>|$)', selector)
                    if not root or selector[root.end():].lstrip().startswith(('+', '~')):
                        raise ValueError(f'CSS selector outside .cqa: {selector}')
                # No nested style rules are used by this stylesheet.
                if '{' in re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', '', css[body:pos - 1]):
                    raise ValueError(f'Nested CSS rule is not supported: {prelude}')

    rules(0, len(css))


def package(web: Path, output: Path) -> list[tuple[str, int]]:
    dist = web / 'dist'
    if not dist.is_dir():
        raise ValueError(f'web/dist is missing. {BUILD}')
    sources = [p for p in (web / 'src').rglob('*.ts') if not p.name.endswith('.d.ts')]
    if not sources:
        raise ValueError(f'No TypeScript sources found. {BUILD}')
    config_time = (web / 'tsconfig.json').stat().st_mtime_ns
    expected = set()
    for source in sources:
        compiled = dist / source.relative_to(web / 'src').with_suffix('.js')
        expected.add(compiled)
        if not compiled.is_file() or compiled.stat().st_mtime_ns < max(source.stat().st_mtime_ns, config_time):
            raise ValueError(f'Missing or stale {compiled.relative_to(web)}. {BUILD}')
    resources = [(web / 'd365/index.htm', 'index.htm'), (web / 'd365/loader.js', 'loader.js'), (web / 'cqa.css', 'cqa.css')]
    resources += [(p, p.relative_to(web).as_posix()) for folder in [dist, web / 'assets'] for p in sorted(folder.rglob('*')) if p.is_file()]
    rows = []
    for source, name in resources:
        # The publisher prefix cqa_ is not part of this validation. Microsoft
        # itself uses new_/test/test.htm; validate the name AFTER that prefix.
        if not NAME.fullmatch(name):
            raise ValueError(f'Invalid web resource name after cqa_/: {name}')
        if source.suffix.lower() not in ALLOWED:
            raise ValueError(f'Unsupported resource extension (maps/fonts are not shipped): {name}')
        if source.is_relative_to(dist) and source not in expected:
            raise ValueError(f'Unexpected dist resource: {name}. Remove stale build output and rebuild. {BUILD}')
        size = source.stat().st_size
        if size >= 5_000_000:
            raise ValueError(f'Resource must be smaller than 5 MB: {name} ({size} bytes)')
        text = source.read_bytes().decode('utf-8', errors='replace')
        if '/static/' in text or re.search(r'url\(\s*[\"\']?/', text, re.I):
            raise ValueError(f'Root-absolute resource URL in {name}; use relative URLs')
        rows.append((f'cqa_/{name}', size))
    check_css((web / 'cqa.css').read_text(encoding='utf-8'))
    target = output / 'cqa_'
    if target.exists():
        shutil.rmtree(target)
    for source, name in resources:
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--web', type=Path, default=ROOT / 'web', help='Source web directory, also useful for isolated negative checks')
    parser.add_argument('--output', type=Path, default=ROOT / 'out/d365')
    args = parser.parse_args()
    try:
        rows = package(args.web.resolve(), args.output.resolve())
    except (OSError, ValueError) as exc:
        print(f'D365 package error: {exc}', file=sys.stderr)
        return 1
    print(f'{"Web resource":60} {"Bytes":>9}')
    for name, size in rows:
        print(f'{name:60} {size:9}')
    print(f'{len(rows)} resources, {sum(size for _, size in rows)} bytes. Output: {args.output}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
