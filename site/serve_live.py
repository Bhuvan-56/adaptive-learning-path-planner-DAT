"""Local server for the live demo (site/live.html). Standard library only; uses the project .venv.

    python site/serve_live.py            then open http://127.0.0.1:8001/

Serves the repository's files (so site/live.html and its assets load as on the website) and
answers POST /api/live with site/py/live_session.run(log) (site/live.html) and
POST /api/simulate with live_session.simulate(theta, seed, skip_at_day) (site/sim.html). No internet is needed: the engine,
including the catsim diagnostic, runs here in the project's own Python, not in the browser.
Binds to 127.0.0.1 only.
"""
import argparse
import json
import os
import sys
import traceback
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "site", "py"))

import live_session  # noqa: E402


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Pages change while the demo is being prepared; never let the browser reuse a stale copy.
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_GET(self):
        if self.path == "/api/ping":
            self._json(200, {"ok": True})
            return
        if self.path in ("/", "/index.html"):
            self.send_response(302)
            self.send_header("Location", "/site/live.html")
            self.end_headers()
            return
        super().do_GET()

    def do_POST(self):
        if self.path not in ("/api/live", "/api/simulate"):
            self.send_error(404)
            return
        try:
            n = int(self.headers.get("Content-Length", "0"))
            req = json.loads(self.rfile.read(n) or b"{}")
            if self.path == "/api/live":
                out = live_session.run(req)
            else:
                skip = req.get("skip_at_day")
                out = live_session.simulate(float(req.get("theta", 0.0)), seed=int(req.get("seed", 1)),
                                            skip_at_day=int(skip) if skip else None,
                                            target=str(req.get("target", live_session.DEFAULT_TARGET)),
                                            budget=int(req.get("budget", live_session.DEFAULT_BUDGET)),
                                            horizon=int(req.get("horizon", live_session.DEFAULT_HORIZON)))
            self._json(200, {"ok": True, **out})
        except Exception as exc:  # shown on the page instead of failing silently
            traceback.print_exc()
            self._json(500, {"ok": False, "error": f"{type(exc).__name__}: {exc}"})

    def _json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        if args and "/api/" in str(args[0]):
            return  # keep the console quiet during the demo
        super().log_message(fmt, *args)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8001)
    args = ap.parse_args()
    live_session.questions()  # fail early if the question file is missing
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), partial(Handler, directory=ROOT))
    print(f"Live demo:       http://127.0.0.1:{args.port}/site/live.html")
    print(f"Live simulation: http://127.0.0.1:{args.port}/site/sim.html   (Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
