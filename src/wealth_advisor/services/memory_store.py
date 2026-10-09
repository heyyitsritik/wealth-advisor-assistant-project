
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from wealth_advisor.report_models import AdvisoryReport
from wealth_advisor.review_models import ReviewRecord, ReviewRequest


class MemoryStore:
    """Stores report summaries and human-review decisions in SQLite."""

    def __init__(self, database_path: str | Path = "data/wealth_advisor.db"):
        self.database_path = str(database_path)

        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(
                parents=True,
                exist_ok=True,
            )

        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reports (
                    report_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    report_json TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_reports_client_created
                ON reports(client_id, created_at)
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reviews (
                    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id TEXT NOT NULL,
                    client_id TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    reviewer TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    reviewed_at TEXT NOT NULL,
                    FOREIGN KEY(report_id) REFERENCES reports(report_id)
                )
                """
            )

    def save_report(self, report: AdvisoryReport) -> str:
        report_id = str(uuid4())

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO reports
                (report_id, client_id, status, created_at, report_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    report.client_id or "unknown",
                    report.status,
                    report.generated_at.isoformat(),
                    report.model_dump_json(),
                ),
            )

        return report_id

    def get_report(self, report_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM reports WHERE report_id = ?",
                (report_id,),
            ).fetchone()

        return dict(row) if row else None

    def list_reports(self, client_id: str, limit: int = 10) -> list[dict]:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT report_id, client_id, status, created_at
                FROM reports
                WHERE client_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (client_id, limit),
            ).fetchall()

        return [dict(row) for row in rows]

    def save_review(
        self,
        report_id: str,
        request: ReviewRequest,
    ) -> ReviewRecord:
        # Verify the report exists and use its stored client ID.
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT client_id
                FROM reports
                WHERE report_id = ?
                """,
                (report_id,),
            ).fetchone()

            if row is None:
                raise KeyError(f"Report not found: {report_id}")

            client_id = row["client_id"]
            reviewed_at = datetime.now(timezone.utc).isoformat()

            cursor = connection.execute(
                """
                INSERT INTO reviews
                (report_id, client_id, decision, reviewer, reason, reviewed_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    client_id,
                    request.decision,
                    request.reviewer,
                    request.reason,
                    reviewed_at,
                ),
            )

            review_id = cursor.lastrowid

        return ReviewRecord(
            review_id=review_id,
            report_id=report_id,
            client_id=client_id,
            decision=request.decision,
            reviewer=request.reviewer,
            reason=request.reason,
            reviewed_at=datetime.fromisoformat(reviewed_at),
        )

    def list_reviews(self, report_id: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT review_id, report_id, client_id, decision,
                       reviewer, reason, reviewed_at
                FROM reviews
                WHERE report_id = ?
                ORDER BY review_id ASC
                """,
                (report_id,),
            ).fetchall()

        return [dict(row) for row in rows]
