#!/usr/bin/env python3
"""하루 운영 대시보드 서버: 정적 파일(haru/) + 수동 새로고침 API.

  python3 haru/ops/serve.py [--port 8766]
  → http://localhost:8766/ops/dist/index.html

POST /api/refresh?revenue=0|1   refresh.py 를 백그라운드로 실행 (revenue=1 이면 Aside 수익 수집까지)
GET  /api/refresh/status        {"running","started","finished","ok","step","log"}
동시에 하나만 돈다. 외부 입력은 revenue 플래그 하나뿐이고 셸로 넘기지 않는다.
"""
import argparse
import json
import subprocess
import sys
import threading
from datetime import datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
HARU = HERE.parent
sys.path.insert(0, str(HARU))
from pipeline import KST  # noqa: E402

STATE = {"running": False, "started": None, "finished": None, "ok": None, "step": "", "log": ""}
LOCK = threading.Lock()


def _run(with_revenue: bool) -> None:
    args = [sys.executable, str(HERE / "refresh.py")] + ([] if with_revenue else ["--no-revenue"])
    log = []
    try:
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=str(HARU.parent))
        for line in p.stdout:  # type: ignore[union-attr]
            log.append(line.rstrip())
            if line.startswith("--- "):
                with LOCK:
                    STATE["step"] = line.split()[1]
        ok = p.wait() == 0
    except Exception as e:  # noqa: BLE001
        log.append(f"serve: {e}"); ok = False
    with LOCK:
        STATE.update({"running": False, "finished": datetime.now(KST).isoformat(timespec="seconds"), "ok": ok, "step": "", "log": "\n".join(log)[-3000:]})


class Handler(SimpleHTTPRequestHandler):
    def _json(self, code: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if urlparse(self.path).path == "/api/refresh/status":
            with LOCK:
                return self._json(200, dict(STATE))
        return super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        u = urlparse(self.path)
        if u.path != "/api/refresh":
            return self._json(404, {"error": "no such endpoint"})
        with_revenue = parse_qs(u.query).get("revenue", ["0"])[0] == "1"
        with LOCK:
            if STATE["running"]:
                return self._json(409, {"error": "already running", **STATE})
            STATE.update({"running": True, "started": datetime.now(KST).isoformat(timespec="seconds"), "finished": None, "ok": None, "step": "시작", "log": ""})
        threading.Thread(target=_run, args=(with_revenue,), daemon=True).start()
        return self._json(202, {"started": STATE["started"], "revenue": with_revenue})

    def end_headers(self) -> None:
        if self.path.startswith("/ops/dist/"):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt: str, *args) -> None:  # 조용히
        if "/api/" in (args[0] if args else ""):
            sys.stderr.write("%s - %s\n" % (self.log_date_time_string(), fmt % args))


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=8766); ns = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", ns.port), partial(Handler, directory=str(HARU)))
    print(f"[serve] http://localhost:{ns.port}/ops/dist/index.html (새로고침 API 포함)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
