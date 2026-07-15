"""SQLite persistence for dispatch log and unit status."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiosqlite

from .models import LogEntry, Priority, UnitState, UnitStatus, utc_now

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "dispatch.db"


class DispatchStore:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path

    async def connect(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(
                """
                CREATE TABLE IF NOT EXISTS dispatch_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    unit_id TEXT,
                    transcript TEXT NOT NULL,
                    response TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    incident_type TEXT,
                    location TEXT,
                    meta_json TEXT
                );

                CREATE TABLE IF NOT EXISTS units (
                    unit_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    last_location TEXT,
                    last_heard TEXT NOT NULL,
                    notes TEXT
                );
                """
            )
            await db.commit()

    async def add_log(
        self,
        *,
        channel: str,
        direction: str,
        unit_id: Optional[str],
        transcript: str,
        response: str,
        intent: str,
        priority: Priority,
        incident_type: Optional[str],
        location: Optional[str],
        meta: Optional[dict] = None,
        timestamp: Optional[datetime] = None,
    ) -> LogEntry:
        ts = timestamp or utc_now()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO dispatch_log (
                    timestamp, channel, direction, unit_id, transcript, response,
                    intent, priority, incident_type, location, meta_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ts.isoformat(),
                    channel,
                    direction,
                    unit_id,
                    transcript,
                    response,
                    intent,
                    priority.value,
                    incident_type,
                    location,
                    json.dumps(meta or {}),
                ),
            )
            await db.commit()
            log_id = cursor.lastrowid
        return LogEntry(
            id=int(log_id),
            timestamp=ts,
            channel=channel,
            direction=direction,
            unit_id=unit_id,
            transcript=transcript,
            response=response,
            intent=intent,
            priority=priority,
            incident_type=incident_type,
            location=location,
        )

    async def list_logs(self, limit: int = 100) -> list[LogEntry]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM dispatch_log
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = await cursor.fetchall()
        entries: list[LogEntry] = []
        for row in rows:
            entries.append(
                LogEntry(
                    id=row["id"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    channel=row["channel"],
                    direction=row["direction"],
                    unit_id=row["unit_id"],
                    transcript=row["transcript"],
                    response=row["response"],
                    intent=row["intent"],
                    priority=Priority(row["priority"]),
                    incident_type=row["incident_type"],
                    location=row["location"],
                )
            )
        return entries

    async def upsert_unit(
        self,
        unit_id: str,
        status: UnitStatus,
        location: Optional[str] = None,
        notes: Optional[str] = None,
        heard_at: Optional[datetime] = None,
    ) -> UnitState:
        ts = heard_at or utc_now()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO units (unit_id, status, last_location, last_heard, notes)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(unit_id) DO UPDATE SET
                    status = excluded.status,
                    last_location = COALESCE(excluded.last_location, units.last_location),
                    last_heard = excluded.last_heard,
                    notes = COALESCE(excluded.notes, units.notes)
                """,
                (unit_id, status.value, location, ts.isoformat(), notes),
            )
            await db.commit()
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM units WHERE unit_id = ?",
                (unit_id,),
            )
            row = await cursor.fetchone()
        return UnitState(
            unit_id=row["unit_id"],
            status=UnitStatus(row["status"]),
            last_location=row["last_location"],
            last_heard=datetime.fromisoformat(row["last_heard"]),
            notes=row["notes"],
        )

    async def list_units(self) -> list[UnitState]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM units ORDER BY unit_id ASC"
            )
            rows = await cursor.fetchall()
        return [
            UnitState(
                unit_id=row["unit_id"],
                status=UnitStatus(row["status"]),
                last_location=row["last_location"],
                last_heard=datetime.fromisoformat(row["last_heard"]),
                notes=row["notes"],
            )
            for row in rows
        ]

    async def clear_all(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM dispatch_log")
            await db.execute("DELETE FROM units")
            await db.commit()
