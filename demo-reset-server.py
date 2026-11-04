#!/usr/bin/env python3
"""Slot dispatcher for the live Android demos.

Runs on 127.0.0.1:9003 behind Caddy. Endpoints:

  POST /demo-reset      allocate a free emulator slot, wipe the app, return
                        {"udid", "session"} and set the demo_session cookie
  POST /demo-heartbeat  keep the caller's lease alive (?session=...)
  POST /demo-release    give the slot back (?session=..., sent on pagehide)
  GET  /demo-auth       Caddy forward_auth check for every WebSocket upgrade:
                        only the stream socket of the caller's own slot passes

Leases expire after IDLE_SECONDS without a heartbeat or MAX_SECONDS in total.
"""
import json
import secrets
import subprocess
import threading
import time
import urllib.parse
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

APPS = {
    "djbook": {
        "hosts": {"demo-djbook.kantrybes.lt"},
        "reset_script": "/opt/android-demo/apps/djbook/reset-session.sh",
        "slots": (1, 2, 3),
        "udid": "redroid{n}:5555",
    },
}

# Only this WebSocket may reach ws-scrcpy: the scrcpy video/control stream.
# Everything else ws-scrcpy offers (adb shell, devtools, file listing,
# device tracker) is refused before it reaches the container.
STREAM_REMOTE = "tcp:8886"

IDLE_SECONDS = 90
MAX_SECONDS = 15 * 60
MAX_SLOTS_PER_IP = 2          # one visitor can never hold every slot
MAX_RESETS_PER_IP = 6         # per RESET_WINDOW seconds
RESET_WINDOW = 60
MAX_BODY = 1024
COOKIE = "demo_session"

LOCK = threading.Lock()
SLOTS = {(app, n): None for app, cfg in APPS.items() for n in cfg["slots"]}
RESET_LOG = {}  # ip -> [timestamps]


def app_for_host(host):
    host = (host or "").split(":")[0].lower()
    for app, cfg in APPS.items():
        if host in cfg["hosts"]:
            return app
    return None


def udid_for(app, n):
    return APPS[app]["udid"].format(n=n)


def lease_valid(lease, now):
    return (
        lease is not None
        and now - lease["heartbeat_at"] < IDLE_SECONDS
        and now - lease["assigned_at"] < MAX_SECONDS
    )


def expire_locked(now):
    for key, lease in SLOTS.items():
        if lease is not None and not lease_valid(lease, now):
            SLOTS[key] = None


def rate_limited_locked(ip, now):
    recent = [t for t in RESET_LOG.get(ip, []) if now - t < RESET_WINDOW]
    if len(recent) >= MAX_RESETS_PER_IP:
        RESET_LOG[ip] = recent
        return True
    recent.append(now)
    RESET_LOG[ip] = recent
    # keep the table small
    if len(RESET_LOG) > 5000:
        for k in [k for k, v in RESET_LOG.items() if not v or now - v[-1] >= RESET_WINDOW]:
            RESET_LOG.pop(k, None)
    return False


def allocate(app, ip):
    """Return (n, session), or (None, reason) where reason is 'busy'/'limited'."""
    now = time.monotonic()
    with LOCK:
        expire_locked(now)
        if rate_limited_locked(ip, now):
            return None, "limited"
        mine = sorted(
            (lease["assigned_at"], key)
            for key, lease in SLOTS.items()
            if lease is not None and key[0] == app and lease["ip"] == ip
        )
        # A visitor who already holds the per-IP maximum gives up their
        # oldest phone instead of taking another one.
        while len(mine) >= MAX_SLOTS_PER_IP:
            _, key = mine.pop(0)
            SLOTS[key] = None
        for n in APPS[app]["slots"]:
            if SLOTS[(app, n)] is None:
                session = secrets.token_urlsafe(24)
                SLOTS[(app, n)] = {
                    "session": session,
                    "ip": ip,
                    "assigned_at": now,
                    "heartbeat_at": now,
                }
                return n, session
    return None, "busy"


def find_session_locked(session, now):
    if not session:
        return None
    for key, lease in SLOTS.items():
        if lease is not None and secrets.compare_digest(lease["session"], session):
            return key if lease_valid(lease, now) else None
    return None


def touch(session):
    now = time.monotonic()
    with LOCK:
        key = find_session_locked(session, now)
        if key is None:
            return False
        SLOTS[key]["heartbeat_at"] = now
        return True


def release(session):
    with LOCK:
        for key, lease in SLOTS.items():
            if lease is not None and secrets.compare_digest(lease["session"], session):
                SLOTS[key] = None
                return


def stream_allowed(app, uri, session):
    """forward_auth decision for one WebSocket upgrade."""
    parsed = urllib.parse.urlsplit(uri or "")
    if parsed.path not in ("", "/"):
        return False  # blocks the /proxy-adb/<udid>/<remote> path shortcut
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)

    def single(key):
        values = query.get(key, [])
        return values[0] if len(values) == 1 else None

    if single("action") != "proxy-adb" or single("remote") != STREAM_REMOTE:
        return False
    if "path" in query:
        return False
    udid = single("udid")
    with LOCK:
        key = find_session_locked(session, time.monotonic())
    return key is not None and key[0] == app and udid == udid_for(app, key[1])


class Handler(BaseHTTPRequestHandler):
    server_version = "demo-dispatcher"
    sys_version = ""

    # -- helpers -----------------------------------------------------------
    def client_ip(self):
        # Caddy is only reachable through the Cloudflare tunnel, and
        # Cloudflare always overwrites CF-Connecting-IP.
        return (
            self.headers.get("CF-Connecting-IP")
            or (self.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
            or self.client_address[0]
        )

    def cookie_session(self):
        jar = SimpleCookie()
        try:
            jar.load(self.headers.get("Cookie") or "")
        except Exception:
            return None
        morsel = jar.get(COOKIE)
        return morsel.value if morsel else None

    def drain_body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length > MAX_BODY:
            self.reply(413)
            return False
        if length > 0:
            self.rfile.read(length)
        return True

    def reply(self, code, payload=None, cookie=None):
        body = json.dumps(payload).encode() if payload is not None else b""
        self.send_response(code)
        self.send_header("Cache-Control", "no-store")
        if payload is not None:
            self.send_header("Content-Type", "application/json")
        if cookie is not None:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    # -- routes ------------------------------------------------------------
    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path.rstrip("/")
        if path != "/demo-auth":
            self.reply(404)
            return
        app = app_for_host(self.headers.get("X-Forwarded-Host") or self.headers.get("Host"))
        uri = self.headers.get("X-Forwarded-Uri")
        if app and stream_allowed(app, uri, self.cookie_session()):
            self.reply(204)
        else:
            self.reply(403)

    def do_POST(self):
        if not self.drain_body():
            return
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path.rstrip("/")
        session = (urllib.parse.parse_qs(parsed.query).get("session") or [None])[0]
        session = session or self.cookie_session()
        app = app_for_host(self.headers.get("Host"))
        if app is None:
            self.reply(404)
        elif path == "/demo-reset":
            self.handle_reset(app)
        elif path == "/demo-heartbeat":
            self.reply(204 if session and touch(session) else 404)
        elif path == "/demo-release":
            if session:
                release(session)
            self.reply(204)
        else:
            self.reply(404)

    def handle_reset(self, app):
        n, session = allocate(app, self.client_ip())
        if n is None:
            self.reply(429 if session == "limited" else 503, {"busy": True})
            return
        try:
            result = subprocess.run(
                [APPS[app]["reset_script"], str(n)],
                timeout=120,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            ok = result.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            ok = False
        if not ok:
            release(session)
            self.reply(500)
            return
        cookie = "%s=%s; Path=/; Max-Age=%d; HttpOnly; Secure; SameSite=Lax" % (
            COOKIE, session, MAX_SECONDS,
        )
        self.reply(200, {"udid": udid_for(app, n), "session": session}, cookie=cookie)

    def log_message(self, _format, *_args):
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 9003), Handler).serve_forever()
