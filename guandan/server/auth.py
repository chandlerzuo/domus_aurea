"""Local user accounts: scrypt password hashes in SQLite, in-memory session tokens."""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
import threading
import time
from pathlib import Path

USERNAME = re.compile(r"^[A-Za-z0-9_]{3,20}$")
MIN_PASSWORD = 8
SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}
SESSION_TTL = 7 * 24 * 3600
MAX_FAILURES, LOCKOUT = 5, 15 * 60


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, **SCRYPT)


class Users:
    def __init__(self, path: str | Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.lock = threading.Lock()
        self.failures: dict[str, list[float]] = {}
        self._dummy = _hash("dummy-password", b"0" * 16)
        with self.lock, self.db:
            self.db.execute("""CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY COLLATE NOCASE, salt BLOB NOT NULL, hash BLOB NOT NULL,
                created REAL NOT NULL, deals_won INTEGER DEFAULT 0, deals_lost INTEGER DEFAULT 0,
                matches_won INTEGER DEFAULT 0, matches_lost INTEGER DEFAULT 0)""")

    def register(self, username: str, password: str) -> None:
        if not USERNAME.match(username or ""):
            raise ValueError("username: 3-20 letters, digits or _")
        if len(password or "") < MIN_PASSWORD:
            raise ValueError(f"password: at least {MIN_PASSWORD} characters")
        salt = secrets.token_bytes(16)
        try:
            with self.lock, self.db:
                self.db.execute("INSERT INTO users (username, salt, hash, created) VALUES (?, ?, ?, ?)",
                                (username, salt, _hash(password, salt), time.time()))
        except sqlite3.IntegrityError:
            raise ValueError("username taken") from None

    def verify(self, username: str, password: str) -> str | None:
        """Canonical username on success. Repeated failures lock the account for a while."""
        key = (username or "").lower()
        now = time.time()
        recent = [t for t in self.failures.get(key, []) if now - t < LOCKOUT]
        if len(recent) >= MAX_FAILURES:
            raise ValueError("too many failed attempts; try again later")
        with self.lock:
            row = self.db.execute("SELECT username, salt, hash FROM users WHERE username = ?",
                                  (username or "",)).fetchone()
        if row is None:
            hmac.compare_digest(_hash(password or "", b"1" * 16), self._dummy)  # same cost as a real check
            ok = False
        else:
            ok = hmac.compare_digest(_hash(password or "", row[1]), row[2])
        if ok:
            self.failures.pop(key, None)
            return row[0]
        self.failures[key] = recent + [now]
        return None

    def record(self, username: str, field: str) -> None:
        assert field in ("deals_won", "deals_lost", "matches_won", "matches_lost")
        with self.lock, self.db:
            self.db.execute(f"UPDATE users SET {field} = {field} + 1 WHERE username = ?", (username,))

    def stats(self, username: str) -> dict:
        with self.lock:
            row = self.db.execute("SELECT deals_won, deals_lost, matches_won, matches_lost FROM users "
                                  "WHERE username = ?", (username,)).fetchone()
        return dict(zip(("deals_won", "deals_lost", "matches_won", "matches_lost"), row or (0, 0, 0, 0)))


class Sessions:
    def __init__(self):
        self.tokens: dict[str, tuple[str, float]] = {}
        self.lock = threading.Lock()

    def create(self, username: str) -> str:
        token = secrets.token_urlsafe(32)
        with self.lock:
            self.tokens[token] = (username, time.time() + SESSION_TTL)
        return token

    def get(self, token: str | None) -> str | None:
        if not token:
            return None
        with self.lock:
            entry = self.tokens.get(token)
            if entry is None:
                return None
            if entry[1] < time.time():
                del self.tokens[token]
                return None
            return entry[0]

    def delete(self, token: str | None) -> None:
        with self.lock:
            self.tokens.pop(token or "", None)
