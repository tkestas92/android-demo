#!/usr/bin/env python3
import json
import secrets
import subprocess
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SCRIPT = "/opt/android-demo/apps/djbook/reset-session.sh"
IDLE_SECONDS = 90
MAX_SECONDS = 15 * 60
LOCK = threading.Lock()
SLOTS = {1: None, 2: None, 3: None}


def lease_valid(slot, now):
    if not slot:
        return False
    if now - slot["heartbeat_at"] >= IDLE_SECONDS:
        return False
    if now - slot["assigned_at"] >= MAX_SECONDS:
        return False
    return True


def expire_locked(now):
    for n, slot in list(SLOTS.items()):
        if slot and not lease_valid(slot, now):
            SLOTS[n] = None


def allocate():
    now = time.monotonic()
    with LOCK:
        expire_locked(now)
        for n in (1, 2, 3):
            if SLOTS[n] is None:
                session = secrets.token_urlsafe(18)
                SLOTS[n] = {
                    "session": session,
                    "assigned_at": now,
                    "heartbeat_at": now,
                }
                return n, session
    return None, None


def touch(session):
    now = time.monotonic()
    with LOCK:
        expire_locked(now)
        for slot in SLOTS.values():
            if slot and slot["session"] == session and lease_valid(slot, now):
                slot["heartbeat_at"] = now
                return True
    return False


def release_session(session):
    with LOCK:
        for n, slot in SLOTS.items():
            if slot and slot["session"] == session:
                SLOTS[n] = None
                return True
    return False


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)

        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = urllib.parse.parse_qs(parsed.query)
        session = (query.get("session") or [None])[0]

        if path == "/demo-reset":
            self.handle_reset()
        elif path == "/demo-heartbeat":
            self.handle_heartbeat(session)
        elif path == "/demo-release":
            self.handle_release(session)
        else:
            self.reply(404)

    def handle_reset(self):
        slot, session = allocate()
        if slot is None:
            self.reply(503, {"busy": True})
            return
        try:
            result = subprocess.run([SCRIPT, str(slot)], timeout=120, check=False)
        except subprocess.TimeoutExpired:
            release_session(session)
            self.reply(504)
            return
        except OSError:
            release_session(session)
            self.reply(500)
            return
        if result.returncode != 0:
            release_session(session)
            self.reply(500)
            return
        self.reply(200, {"udid": "redroid%d:5555" % slot, "session": session})

    def handle_heartbeat(self, session):
        if not session or not touch(session):
            self.reply(404)
            return
        self.reply(204)

    def handle_release(self, session):
        if session:
            release_session(session)
        self.reply(204)

    def reply(self, code, payload=None):
        body = b""
        if payload is not None:
            body = json.dumps(payload).encode()
        self.send_response(code)
        if payload is not None:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def log_message(self, _format, *_args):
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 9003), Handler).serve_forever()
