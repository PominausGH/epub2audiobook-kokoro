"""
Database Module
SQLite database for users and jobs.
"""

import os
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass
from contextlib import contextmanager

from werkzeug.security import generate_password_hash, check_password_hash


DATABASE_PATH = os.environ.get('DATABASE_PATH', '/data/db/epub2audiobook.db')


@dataclass
class User:
    """User model."""
    id: int
    username: str
    email: str
    password_hash: str
    is_admin: bool
    created_at: str


@dataclass
class Job:
    """Conversion job model."""
    id: str
    user_id: int
    status: str  # queued, processing, completed, failed
    epub_filename: str
    epub_path: str
    output_path: Optional[str]
    voice_id: Optional[str]
    speed: int
    error_message: Optional[str]
    progress: int
    title: str
    author: str
    chapters: int
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]


def get_db_path():
    """Get database path, creating directory if needed."""
    db_dir = os.path.dirname(DATABASE_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    return DATABASE_PATH


@contextmanager
def get_db():
    """Get database connection context manager."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Initialize database schema."""
    with get_db() as conn:
        conn.executescript("""
            -- Users table
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Jobs queue
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                status TEXT DEFAULT 'queued',
                epub_filename TEXT NOT NULL,
                epub_path TEXT NOT NULL,
                output_path TEXT,
                voice_id TEXT,
                speed INTEGER DEFAULT 150,
                error_message TEXT,
                progress INTEGER DEFAULT 0,
                title TEXT DEFAULT '',
                author TEXT DEFAULT '',
                chapters INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP
            );

            -- Sessions
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            );
        """)


# User operations

def create_user(username: str, email: str, password: str) -> Optional[User]:
    """Create a new user. First user becomes admin."""
    user_id = None
    with get_db() as conn:
        # Check if first user
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        is_admin = count == 0

        password_hash = generate_password_hash(password)

        try:
            cursor = conn.execute(
                """INSERT INTO users (username, email, password_hash, is_admin)
                   VALUES (?, ?, ?, ?)""",
                (username, email, password_hash, is_admin)
            )
            user_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    # Fetch user after commit
    if user_id:
        return get_user_by_id(user_id)
    return None


def get_user_by_id(user_id: int) -> Optional[User]:
    """Get user by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if row:
            return User(**dict(row))
        return None


def get_user_by_username(username: str) -> Optional[User]:
    """Get user by username."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        if row:
            return User(**dict(row))
        return None


def verify_user(username: str, password: str) -> Optional[User]:
    """Verify username and password, return user if valid."""
    user = get_user_by_username(username)
    if user and check_password_hash(user.password_hash, password):
        return user
    return None


# Session operations

def create_session(user_id: int, days: int = 7) -> str:
    """Create a new session, return session ID."""
    session_id = str(uuid.uuid4())
    expires_at = datetime.now() + timedelta(days=days)

    with get_db() as conn:
        conn.execute(
            """INSERT INTO sessions (id, user_id, expires_at)
               VALUES (?, ?, ?)""",
            (session_id, user_id, expires_at.isoformat())
        )
    return session_id


def get_session_user(session_id: str) -> Optional[User]:
    """Get user from session ID if valid and not expired."""
    with get_db() as conn:
        row = conn.execute(
            """SELECT user_id FROM sessions
               WHERE id = ? AND expires_at > datetime('now')""",
            (session_id,)
        ).fetchone()
        if row:
            return get_user_by_id(row['user_id'])
        return None


def delete_session(session_id: str):
    """Delete a session (logout)."""
    with get_db() as conn:
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))


def cleanup_expired_sessions():
    """Remove expired sessions."""
    with get_db() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at < datetime('now')")


# Job operations

def create_job(user_id: int, epub_filename: str, epub_path: str,
               voice_id: str = None, speed: int = 150) -> Job:
    """Create a new conversion job."""
    job_id = str(uuid.uuid4())[:8]

    with get_db() as conn:
        conn.execute(
            """INSERT INTO jobs (id, user_id, epub_filename, epub_path, voice_id, speed)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (job_id, user_id, epub_filename, epub_path, voice_id, speed)
        )
    return get_job(job_id)


def get_job(job_id: str) -> Optional[Job]:
    """Get job by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()
        if row:
            return Job(**dict(row))
        return None


def get_user_jobs(user_id: int) -> list[Job]:
    """Get all jobs for a user, newest first."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()
        return [Job(**dict(row)) for row in rows]


def get_next_queued_job() -> Optional[Job]:
    """Get the next queued job (oldest first)."""
    with get_db() as conn:
        row = conn.execute(
            """SELECT * FROM jobs WHERE status = 'queued'
               ORDER BY created_at ASC LIMIT 1"""
        ).fetchone()
        if row:
            return Job(**dict(row))
        return None


def update_job(job_id: str, **kwargs):
    """Update job fields."""
    if not kwargs:
        return

    fields = ', '.join(f"{k} = ?" for k in kwargs.keys())
    values = list(kwargs.values()) + [job_id]

    with get_db() as conn:
        conn.execute(f"UPDATE jobs SET {fields} WHERE id = ?", values)


def update_job_progress(job_id: str, progress: int, message: str = None):
    """Update job progress."""
    updates = {'progress': progress}
    if message:
        updates['error_message'] = message  # Reusing for status message
    update_job(job_id, **updates)


def update_job_status(job_id: str, status: str, error_message: str = None):
    """Update job status."""
    updates = {'status': status}
    if status == 'processing':
        updates['started_at'] = datetime.now().isoformat()
    elif status in ('completed', 'failed'):
        updates['completed_at'] = datetime.now().isoformat()
    if error_message:
        updates['error_message'] = error_message
    update_job(job_id, **updates)


def delete_job(job_id: str):
    """Delete a job."""
    with get_db() as conn:
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))


def get_queue_position(job_id: str) -> int:
    """Get job's position in queue (1-based), 0 if not queued."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id FROM jobs WHERE status = 'queued'
               ORDER BY created_at ASC"""
        ).fetchall()
        for i, row in enumerate(rows):
            if row['id'] == job_id:
                return i + 1
        return 0
