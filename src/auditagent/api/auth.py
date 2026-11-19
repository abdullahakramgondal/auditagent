"""Users and login sessions in SQLite. Passwords are hashed with bcrypt, never stored as text.

A session is a random token: the browser keeps it in an httpOnly cookie, the database keeps only
its SHA-256 hash, so a copy of the database cannot be used to log in.
"""

import hashlib
import re
import secrets
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

import bcrypt
from pydantic import BaseModel

COOKIE = "audit_session"
SESSION_DAYS = 7
MIN_PASSWORD = 8
MAX_PASSWORD_BYTES = 72  # bcrypt reads only the first 72 bytes
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL
);
"""


class AuthError(Exception):
    """A refused sign-up or login: the HTTP status and a message that a person can read."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class Credentials(BaseModel):
    email: str
    password: str


class User(BaseModel):
    id: int
    email: str


class UserOut(BaseModel):
    """What the API tells the browser about the logged-in person (never the id or the hash)."""

    email: str


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def clean_email(email: str) -> str:
    """The email in one spelling (lower case, no spaces), or a 400 if it cannot be an email."""
    value = email.strip().lower()
    if len(value) > 254 or not _EMAIL.match(value):
        raise AuthError(400, "Enter a valid email address.")
    return value


def check_password(password: str) -> None:
    if len(password) < MIN_PASSWORD:
        raise AuthError(400, f"Use at least {MIN_PASSWORD} characters for the password.")
    if len(password.encode()) > MAX_PASSWORD_BYTES:
        raise AuthError(400, f"The password is too long ({MAX_PASSWORD_BYTES} characters at most).")


class UserStore:
    """The accounts and the sessions. One short database connection per call (safe with threads)."""

    def __init__(self, path, rounds: int = 12):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._rounds = rounds
        # A hash to compare against when the email is unknown, so that both cases take the same time.
        self._dummy = bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt(rounds))
        with self._db() as db:
            db.executescript(SCHEMA)

    @contextmanager
    def _db(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        try:
            with db:  # commits when the block ends well
                yield db
        finally:
            db.close()

    def create_user(self, email: str, password: str) -> User:
        email = clean_email(email)
        check_password(password)
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(self._rounds)).decode()
        try:
            with self._db() as db:
                cursor = db.execute(
                    "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
                    (email, hashed, _now()),
                )
                return User(id=cursor.lastrowid, email=email)
        except sqlite3.IntegrityError as exc:
            raise AuthError(409, "An account with this email already exists.") from exc

    def login(self, email: str, password: str) -> User:
        wrong = AuthError(401, "Wrong email or password.")
        try:
            value = clean_email(email)
        except AuthError:
            raise wrong from None
        with self._db() as db:
            row = db.execute("SELECT * FROM users WHERE email = ?", (value,)).fetchone()
        raw = password.encode()
        if len(raw) > MAX_PASSWORD_BYTES:
            raise wrong
        if row is None:
            bcrypt.checkpw(raw, self._dummy)
            raise wrong
        if not bcrypt.checkpw(raw, row["password_hash"].encode()):
            raise wrong
        return User(id=row["id"], email=row["email"])

    def new_session(self, user_id: int) -> str:
        token = secrets.token_urlsafe(32)
        expires = (datetime.now(UTC) + timedelta(days=SESSION_DAYS)).isoformat(timespec="seconds")
        with self._db() as db:
            db.execute("DELETE FROM sessions WHERE expires_at <= ?", (_now(),))
            db.execute(
                "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                (_hash_token(token), user_id, expires),
            )
        return token

    def user_for_token(self, token: str) -> User | None:
        with self._db() as db:
            row = db.execute(
                "SELECT users.id, users.email FROM sessions "
                "JOIN users ON users.id = sessions.user_id "
                "WHERE sessions.token_hash = ? AND sessions.expires_at > ?",
                (_hash_token(token), _now()),
            ).fetchone()
        return None if row is None else User(id=row["id"], email=row["email"])

    def end_session(self, token: str) -> None:
        with self._db() as db:
            db.execute("DELETE FROM sessions WHERE token_hash = ?", (_hash_token(token),))
