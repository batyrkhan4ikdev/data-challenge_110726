"""Local D365 iframe rig: CSP is an HTTP response header, never a meta tag."""
import argparse
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def policy(profile: str, host_origin: str, api_origin: str, media_origin: str) -> str:
    if profile == 'default':
        return (
            "script-src * 'unsafe-inline' 'unsafe-eval' blob:; "
            "style-src * 'unsafe-inline' blob:; img-src * data: blob:; "
            "font-src * data:; connect-src * blob: data:; media-src * blob: data:; "
            f"frame-ancestors 'self' {host_origin}"
        )
    extra = f' {api_origin}' if profile == 'strict-api' else ''
    font = ' data:' if profile == 'strict-api' else ''
    media = f' {media_origin}' if profile == 'strict-api' and media_origin else ''
    return (
        f"default-src 'self'; connect-src 'self'{extra}; font-src 'self'{font}; "
        f"media-src 'self'{extra}{media}; frame-ancestors {host_origin}"
    )


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, '.js': 'text/javascript', '.htm': 'text/html', '.svg': 'image/svg+xml'}

    def translate_path(self, path: str) -> str:
        requested = urlsplit(path).path
        if requested in ['/', '/host.html']:
            return str(HERE / 'host.html')
        if requested == '/host.js':
            return str(HERE / 'host.js')
        return super().translate_path(path)

    def end_headers(self) -> None:
        self.send_header('Cache-Control', 'no-store')
        if urlsplit(self.path).path.startswith('/cqa_/'):
            self.send_header('Content-Security-Policy', self.server.cqa_policy)
        super().end_headers()

    def log_message(self, format: str, *args: object) -> None:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8807)
    parser.add_argument('--profile', choices=['default', 'strict-no-api', 'strict-api'], default='default')
    parser.add_argument('--package', type=Path, default=ROOT / 'out/d365')
    parser.add_argument('--host-origin', default='http://127.0.0.1:8807')
    parser.add_argument('--api-origin', default='http://127.0.0.1:8806')
    parser.add_argument('--media-origin', default='', help='Signed Dynamics audio origin, if different from the API')
    args = parser.parse_args()
    if not (args.package / 'cqa_/index.htm').is_file():
        parser.error('Package missing. Build web/ and run python scripts/package_d365.py first.')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), functools.partial(Handler, directory=str(args.package.resolve())))
    server.cqa_policy = policy(args.profile, args.host_origin, args.api_origin, args.media_origin)
    print(f'Rig ready http://127.0.0.1:{args.port}/host.html profile={args.profile} CSP={server.cqa_policy}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
