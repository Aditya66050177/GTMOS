"""The public, internet-facing GTMOS demo API.

The full API (app.api.main.create_app) has every route open, which is right for
local use and wrong for a public website. This module builds a separate instance
and wraps it so that:

* Shared demo data is read-only. It is opened with SQLite's ``mode=ro``, so even a
  bug cannot change what other visitors see.
* Only the writes the website needs are allowed (see WRITE_POLICY). Each one runs
  against a private copy of the demo database owned by one browser, identified by
  a random ``X-Demo-Session`` header. Every other write returns 403.
* Request bodies are capped and every client is rate limited.
* The LLM is forced into offline mock mode, so the public site never spends
  Gemini credits.

Limits of this design (documented, not hidden):

* Rate limits and sandboxes live in process memory and /tmp. On Vercel each warm
  instance has its own, so limits are best-effort and a visitor whose request
  lands on a different instance sees the shared data instead of their sandbox.
* The session header is not authentication. It only keeps visitors' demo edits
  apart; anyone who learns a session id can act on that sandbox.
"""
from __future__ import annotations

import logging
import re
import secrets
import shutil
import sqlite3
import threading
import time
from collections import OrderedDict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Deque, Dict, Iterator, Optional, Tuple

from fastapi import FastAPI, Header, HTTPException, Request
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.main import create_app
from app.core.config import settings
from app.db.database import engine as default_engine
from app.db.database import get_db

logger = logging.getLogger(__name__)

SESSION_HEADER = "x-demo-session"
SESSION_ID_RE = re.compile(r"^[a-f0-9]{32}$")

# --------------------------------------------------------------------------- #
# Write policy                                                                 #
# --------------------------------------------------------------------------- #

# (method, path regex, mutates data). Paths are relative to the API root (no /api).
# Anything not listed here and not a GET/HEAD/OPTIONS is refused with 403.
WRITE_POLICY: Tuple[Tuple[str, re.Pattern, bool], ...] = (
    ("POST", re.compile(r"^/web/playground$"), False),
    ("POST", re.compile(r"^/analytics/ask$"), False),
    ("POST", re.compile(r"^/web/reset$"), True),
    ("POST", re.compile(r"^/accounts/\d+/personalize$"), True),
    ("POST", re.compile(r"^/accounts/\d+/mark_sent$"), True),
    ("PATCH", re.compile(r"^/drafts/\d+$"), True),
    ("POST", re.compile(r"^/drafts/\d+/approve$"), True),
    ("POST", re.compile(r"^/drafts/\d+/reject$"), True),
)
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@dataclass(frozen=True)
class RouteDecision:
    allowed: bool
    mutates: bool


def classify(method: str, path: str) -> RouteDecision:
    if method in SAFE_METHODS:
        return RouteDecision(True, False)
    for m, pattern, mutates in WRITE_POLICY:
        if m == method and pattern.match(path):
            return RouteDecision(True, mutates)
    return RouteDecision(False, False)


# --------------------------------------------------------------------------- #
# Per-visitor sandboxes                                                        #
# --------------------------------------------------------------------------- #

def _enable_foreign_keys(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, _record):  # pragma: no cover - trivial
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def _sqlite_engine(path: Path, read_only: bool) -> Engine:
    if read_only:
        url = f"sqlite:///file:{path.as_posix()}?mode=ro&uri=true"
    else:
        url = f"sqlite:///{path.as_posix()}"
    engine = create_engine(url, connect_args={"check_same_thread": False})
    _enable_foreign_keys(engine)
    return engine


class SandboxRegistry:
    """Private copies of the template database, one per demo session id.

    Bounded in count and age so a flood of new ids cannot fill /tmp.
    """

    def __init__(self, template: Path, directory: Path, max_sandboxes: int, ttl_seconds: int,
                 clock: Callable[[], float] = time.monotonic):
        self.template = template
        self.directory = directory
        self.max_sandboxes = max_sandboxes
        self.ttl_seconds = ttl_seconds
        self.clock = clock
        self._lock = threading.Lock()
        # sid -> (engine, sessionmaker, last_seen, token). The token is random per sandbox, so a
        # recreated sandbox for the same browser id gets a different token.
        self._entries: "OrderedDict[str, Tuple[Engine, sessionmaker, float, str]]" = OrderedDict()
        if directory.exists():
            shutil.rmtree(directory, ignore_errors=True)
        directory.mkdir(parents=True, exist_ok=True)

    def _path(self, sid: str) -> Path:
        return self.directory / f"{sid}.db"

    def _drop(self, sid: str) -> None:
        engine, _maker, _seen, _token = self._entries.pop(sid)
        engine.dispose()
        self._path(sid).unlink(missing_ok=True)

    def _expire(self) -> None:
        cutoff = self.clock() - self.ttl_seconds
        for sid in [s for s, (_e, _m, seen, _t) in self._entries.items() if seen < cutoff]:
            self._drop(sid)

    def _copy_template(self, sid: str) -> Path:
        target = self._path(sid)
        src = sqlite3.connect(f"file:{self.template.as_posix()}?mode=ro", uri=True)
        dst = sqlite3.connect(target.as_posix())
        try:
            src.backup(dst)
        finally:
            src.close()
            dst.close()
        return target

    def session_factory(self, sid: str, create: bool) -> Optional[sessionmaker]:
        with self._lock:
            self._expire()
            if sid in self._entries:
                engine, maker, _seen, token = self._entries.pop(sid)
                self._entries[sid] = (engine, maker, self.clock(), token)
                return maker
            if not create:
                return None
            while len(self._entries) >= self.max_sandboxes:
                oldest = next(iter(self._entries))
                self._drop(oldest)
            engine = _sqlite_engine(self._copy_template(sid), read_only=False)
            maker = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            self._entries[sid] = (engine, maker, self.clock(), secrets.token_hex(8))
            return maker

    def token(self, sid: str) -> Optional[str]:
        """Token of the live sandbox for this browser id, or None if there isn't one here."""
        with self._lock:
            self._expire()
            entry = self._entries.get(sid)
            return entry[3] if entry else None

    def reset(self, sid: str) -> bool:
        with self._lock:
            if sid in self._entries:
                self._drop(sid)
                return True
            return False

    def __len__(self) -> int:
        return len(self._entries)


# --------------------------------------------------------------------------- #
# Rate limiting (per instance, best effort)                                    #
# --------------------------------------------------------------------------- #

class RateLimiter:
    """Sliding-window counter per (bucket, client). Memory is bounded."""

    def __init__(self, max_clients: int = 10_000, window_seconds: float = 60.0,
                 clock: Callable[[], float] = time.monotonic):
        self.window = window_seconds
        self.max_clients = max_clients
        self.clock = clock
        self._lock = threading.Lock()
        self._hits: "OrderedDict[Tuple[str, str], Deque[float]]" = OrderedDict()

    def hit(self, bucket: str, client: str, limit: int) -> Optional[int]:
        """Record a request. Returns None if allowed, else seconds until retry."""
        now = self.clock()
        key = (bucket, client)
        with self._lock:
            hits = self._hits.pop(key, None) or deque()
            while hits and hits[0] <= now - self.window:
                hits.popleft()
            if len(hits) >= limit:
                self._hits[key] = hits
                return max(1, int(hits[0] + self.window - now) + 1)
            hits.append(now)
            self._hits[key] = hits
            while len(self._hits) > self.max_clients:
                self._hits.popitem(last=False)
            return None


def client_ip(scope: dict) -> str:
    headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
    # Behind Vercel these are set by the platform. Elsewhere they can be spoofed,
    # which only matters for this best-effort limiter.
    if headers.get("x-real-ip"):
        return headers["x-real-ip"].strip()
    if headers.get("x-forwarded-for"):
        return headers["x-forwarded-for"].split(",")[0].strip()
    client = scope.get("client")
    return client[0] if client else "unknown"


# --------------------------------------------------------------------------- #
# ASGI guard middleware                                                        #
# --------------------------------------------------------------------------- #

async def _send_json(send, status: int, detail: str, extra_headers: Optional[Dict[str, str]] = None) -> None:
    import json

    body = json.dumps({"detail": detail}).encode()
    headers = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]
    for k, v in (extra_headers or {}).items():
        headers.append((k.lower().encode(), v.encode()))
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


class PublicDemoGuard:
    """Body cap → rate limits → write policy, before any route runs."""

    def __init__(self, app, limiter: RateLimiter, max_body: int,
                 per_minute: int, writes_per_minute: int, resets_per_minute: int,
                 sandboxes: Optional["SandboxRegistry"] = None):
        self.app = app
        self.sandboxes = sandboxes
        self.limiter = limiter
        self.max_body = max_body
        self.per_minute = per_minute
        self.writes_per_minute = writes_per_minute
        self.resets_per_minute = resets_per_minute

    def _with_sandbox_headers(self, scope, send):
        """Tell the browser whether its sandbox exists on this server, and which one.

        Added at response start, so it reflects the state after the request ran (e.g. after a
        reset). The browser compares the token with the one it saw when it last made an edit:
        "none" or a different token means its temporary edits are gone.
        """
        if self.sandboxes is None:
            return send
        sid = dict(scope.get("headers", [])).get(SESSION_HEADER.encode(), b"").decode("latin-1")
        sandboxes = self.sandboxes

        async def wrapped(message):
            if message["type"] == "http.response.start":
                token = sandboxes.token(sid) if SESSION_ID_RE.match(sid or "") else None
                headers = list(message.get("headers", []))
                headers.append((b"x-demo-sandbox", b"active" if token else b"none"))
                if token:
                    headers.append((b"x-demo-sandbox-id", token.encode()))
                message = {**message, "headers": headers}
            await send(message)
        return wrapped

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope["method"].upper()
        path = scope["path"]
        root = scope.get("root_path", "")
        if root and path.startswith(root):
            path = path[len(root):] or "/"

        decision = classify(method, path)
        if not decision.allowed:
            await _send_json(send, 403, "This action is disabled in the public demo.")
            return

        ip = client_ip(scope)
        checks = [("all", self.per_minute)]
        if method not in SAFE_METHODS:
            checks.append(("write", self.writes_per_minute))
        if path == "/web/reset":
            checks.append(("reset", self.resets_per_minute))
        for bucket, limit in checks:
            retry = self.limiter.hit(bucket, ip, limit)
            if retry is not None:
                await _send_json(send, 429, "Too many requests. Please slow down.", {"Retry-After": str(retry)})
                return

        send = self._with_sandbox_headers(scope, send)
        if method in SAFE_METHODS:
            await self.app(scope, receive, send)
            return

        # Buffer the body with a hard cap, then replay it to the app.
        declared = dict(scope.get("headers", [])).get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > self.max_body:
            await _send_json(send, 413, f"Request body too large (limit {self.max_body} bytes).")
            return
        chunks, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > self.max_body:
                await _send_json(send, 413, f"Request body too large (limit {self.max_body} bytes).")
                return
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        body = b"".join(chunks)
        replayed = False

        async def replay():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


# --------------------------------------------------------------------------- #
# App factory                                                                  #
# --------------------------------------------------------------------------- #

def _template_path() -> Path:
    database = default_engine.url.database
    if default_engine.url.get_backend_name() != "sqlite" or not database:
        raise RuntimeError("The public demo needs a file-based SQLite DATABASE_URL for its template data.")
    return Path(database).resolve()


def create_public_api(template: Optional[Path] = None, sandbox_dir: Optional[Path] = None) -> FastAPI:
    """Build the guarded demo API (mount it under /api). The template must already be seeded."""
    if settings.LLM_MODE != "mock":
        logger.warning("Public demo forces LLM_MODE=mock (was %r). Live LLM calls are never public.", settings.LLM_MODE)
    settings.LLM_MODE = "mock"

    template = (template or _template_path()).resolve()
    sandbox_dir = sandbox_dir or (
        Path(settings.DEMO_SANDBOX_DIR) if settings.DEMO_SANDBOX_DIR else template.parent / "gtmos_sandboxes"
    )
    shared_engine = _sqlite_engine(template, read_only=True)
    shared_sessions = sessionmaker(autocommit=False, autoflush=False, bind=shared_engine)
    sandboxes = SandboxRegistry(template, sandbox_dir, settings.DEMO_MAX_SANDBOXES, settings.DEMO_SANDBOX_TTL_SECONDS)

    api = create_app()

    @api.post("/web/reset", tags=["Web App"])
    def reset_my_sandbox(x_demo_session: Optional[str] = Header(None)) -> Dict[str, object]:
        """Discard this browser's private sandbox. Shared demo data is never touched."""
        if not x_demo_session or not SESSION_ID_RE.match(x_demo_session):
            raise HTTPException(status_code=400, detail="Missing or invalid X-Demo-Session header.")
        return {"status": "reset", "had_changes": sandboxes.reset(x_demo_session)}

    # Make the reset route above win over the shared one registered by create_app().
    reset_route = api.router.routes.pop()
    api.router.routes.insert(0, reset_route)

    def demo_db(request: Request) -> Iterator[Session]:
        sid = request.headers.get(SESSION_HEADER)
        valid_sid = bool(sid and SESSION_ID_RE.match(sid))
        root = request.scope.get("root_path", "")
        path = request.url.path[len(root):] if root and request.url.path.startswith(root) else request.url.path
        mutates = classify(request.method.upper(), path).mutates

        if mutates and not valid_sid:
            raise HTTPException(status_code=400, detail="Missing or invalid X-Demo-Session header.")
        maker = sandboxes.session_factory(sid, create=mutates) if valid_sid else None
        db = (maker or shared_sessions)()
        try:
            yield db
        finally:
            db.close()

    api.dependency_overrides[get_db] = demo_db
    api.state.sandboxes = sandboxes
    api.state.limiter = RateLimiter()
    api.add_middleware(
        PublicDemoGuard,
        limiter=api.state.limiter,
        max_body=settings.DEMO_MAX_BODY_BYTES,
        per_minute=settings.DEMO_RATE_LIMIT_PER_MINUTE,
        writes_per_minute=settings.DEMO_WRITE_LIMIT_PER_MINUTE,
        resets_per_minute=settings.DEMO_RESET_LIMIT_PER_MINUTE,
        sandboxes=sandboxes,
    )
    return api
