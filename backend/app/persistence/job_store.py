from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

from app.models.job import JobResponse, JobStatus


class JobStore:
    """Small persistence boundary for jobs.

    SQLite is intentionally used as the local/test backend. API and processing
    code depend on this boundary instead of depending on SQLite query details,
    so a PostgreSQL implementation can replace it in a later milestone.
    """

    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL DEFAULT 'local-dev',
                    tool_slug TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress INTEGER NOT NULL DEFAULT 0 CHECK(progress >= 0 AND progress <= 100),
                    original_filename TEXT NOT NULL,
                    output_filename TEXT,
                    error_message TEXT,
                    result_metadata TEXT,
                    completed_at TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            columns = {row[1] for row in connection.execute("PRAGMA table_info(jobs)").fetchall()}
            if "user_id" not in columns:
                connection.execute("ALTER TABLE jobs ADD COLUMN user_id TEXT NOT NULL DEFAULT 'local-dev'")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON jobs(status, created_at)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_jobs_user_created ON jobs(user_id, created_at)")

    @staticmethod
    def _iso(value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    @staticmethod
    def _datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value)

    @staticmethod
    def _to_job(row: sqlite3.Row) -> JobResponse:
        metadata = json.loads(row["result_metadata"]) if row["result_metadata"] else None
        return JobResponse(
            id=row["id"],
            user_id=row["user_id"] if "user_id" in row.keys() else "local-dev",
            tool_slug=row["tool_slug"],
            status=JobStatus(row["status"]),
            progress=row["progress"],
            original_filename=row["original_filename"],
            output_filename=row["output_filename"],
            error_message=row["error_message"],
            result_metadata=metadata,
            completed_at=JobStore._datetime(row["completed_at"]),
            created_at=JobStore._datetime(row["created_at"]) or datetime.now(timezone.utc),
        )

    def save(self, job: JobResponse) -> JobResponse:
        payload = job.model_dump(mode="json")
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs (
                    id, user_id, tool_slug, status, progress, original_filename,
                    output_filename, error_message, result_metadata,
                    completed_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    user_id=excluded.user_id,
                    tool_slug=excluded.tool_slug,
                    status=excluded.status,
                    progress=excluded.progress,
                    original_filename=excluded.original_filename,
                    output_filename=excluded.output_filename,
                    error_message=excluded.error_message,
                    result_metadata=excluded.result_metadata,
                    completed_at=excluded.completed_at,
                    created_at=excluded.created_at
                """,
                (
                    payload["id"],
                    payload["user_id"],
                    payload["tool_slug"],
                    payload["status"],
                    payload["progress"],
                    payload["original_filename"],
                    payload["output_filename"],
                    payload["error_message"],
                    json.dumps(payload["result_metadata"], ensure_ascii=False) if payload["result_metadata"] is not None else None,
                    payload["completed_at"],
                    payload["created_at"],
                ),
            )
        return job

    def get(self, job_id: str) -> JobResponse | None:
        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._to_job(row) if row else None

    def get_for_user(self, job_id: str, user_id: str) -> JobResponse | None:
        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE id = ? AND user_id = ?", (job_id, user_id)).fetchone()
        return self._to_job(row) if row else None

    def count(self) -> int:
        with self._lock, self._connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0])

    def recover_incomplete(self) -> int:
        """Mark in-flight jobs as failed after a process restart.

        This preserves truthful state and metadata. It does not pretend that a
        non-durable worker resumed work; durable queue recovery is a later phase.
        """
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE jobs
                SET status = ?, error_message = ?, completed_at = ?, progress = MIN(progress, 99)
                WHERE status IN (?, ?)
                """,
                (
                    JobStatus.FAILED.value,
                    "Backend restarted before the job completed; retry is required.",
                    now,
                    JobStatus.QUEUED.value,
                    JobStatus.PROCESSING.value,
                ),
            )
            return cursor.rowcount

    def healthcheck(self) -> dict[str, Any]:
        with self._lock, self._connect() as connection:
            connection.execute("SELECT 1").fetchone()
        return {"backend": "sqlite", "path": str(self.path), "jobs": self.count()}
