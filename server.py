"""STEP ON static preview server. Run: python3 server.py --port 3000."""
import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
PUBLIC_FILES = {
    "index.html", "assets/favicon.svg"
}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def translate_path(self, path):
        # Preview proxies may forward their URL prefix. Serve only public files,
        # including at /preview/.../styles.css; never expose Git or config files.
        clean = unquote(urlsplit(path).path)
        if any(part in {".", ".."} for part in clean.split("/")):
            return str(ROOT / "__not_public__")
        for name in sorted(PUBLIC_FILES, key=len, reverse=True):
            if clean == "/" + name or clean.endswith("/" + name):
                return str(ROOT / name)
        if clean.endswith("/"):
            return str(ROOT / "index.html")
        return str(ROOT / "__not_public__")

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=3000)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print(f"STEP ON preview listening on port {args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
