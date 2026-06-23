#!/usr/bin/env python3
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST_TO_SCRIPT = {
    "demo-djbook.kantrybes.lt": "/opt/android-demo/apps/djbook/reset-session.sh",
    "demo-dishcovery.kantrybes.lt": "/opt/android-demo/apps/dishcovery/reset-session.sh",
    "135.181.39.195": "/opt/android-demo/apps/dishcovery/reset-session.sh",
}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path.rstrip("/") != "/demo-reset":
            self.send_response(404)
            self.end_headers()
            return

        host = (self.headers.get("Host") or "").split(":")[0].lower()
        script = HOST_TO_SCRIPT.get(host)
        if not script:
            self.send_response(404)
            self.end_headers()
            return

        try:
            subprocess.run([script], timeout=120, check=False)
            self.send_response(204)
        except subprocess.TimeoutExpired:
            self.send_response(504)
        self.end_headers()

    def log_message(self, _format, *_args):
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 9003), Handler).serve_forever()
