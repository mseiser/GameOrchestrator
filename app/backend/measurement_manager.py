"""Measurement event persistence — separate DB from game_droplets to avoid
lock contention with frequent heartbeat writes."""

import json
import os
import sqlite3
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

_DEFAULT_DB = "/data/physicsquest_measurements.db"
_ENV_MEASUREMENTS_DB_PATH = os.getenv("MEASUREMENTS_DB_PATH", _DEFAULT_DB)


def _get_connection(db_path: str) -> sqlite3.Connection:
    """Return a WAL-mode connection to the measurements DB, creating schema if needed."""
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS measurement_events (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id       TEXT    NOT NULL,
            share_tag       TEXT    NOT NULL,
            event_type      TEXT    NOT NULL,
            payload         TEXT    NOT NULL,
            event_timestamp REAL    NOT NULL,
            received_at     TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_measurement_events_share_tag
        ON measurement_events (share_tag)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_measurement_events_client_id
        ON measurement_events (client_id)
    """)
    conn.commit()
    return conn


class MeasurementManager:
    """Handles storage of gameplay measurement events."""

    def __init__(self, db: str | None = None) -> None:
        self.db = db or _ENV_MEASUREMENTS_DB_PATH
        # Ensure schema exists at startup
        conn = _get_connection(self.db)
        conn.close()

    def insert_events(self, client_id: str, share_tag: str, events: list[dict]) -> int:
        """Batch-insert measurement events. Returns the number of rows inserted."""
        if not events:
            return 0

        rows = []
        for event in events:
            event_type = str(event.get("type", "unknown"))
            event_timestamp = float(event.get("timestamp", 0.0))
            # Unity client sends: {"type": "...", "timestamp": ..., "payload": {...}}
            # Extract the nested payload dict directly; fall back to everything else
            # if the client flattens the payload into the top level.
            raw_payload = event.get("payload")
            if isinstance(raw_payload, dict):
                payload_dict = raw_payload
            else:
                payload_dict = {k: v for k, v in event.items() if k not in ("type", "timestamp")}
            rows.append((
                client_id,
                share_tag,
                event_type,
                json.dumps(payload_dict, ensure_ascii=False),
                event_timestamp,
            ))

        conn = _get_connection(self.db)
        cur = conn.cursor()
        cur.executemany(
            """
            INSERT INTO measurement_events
                (client_id, share_tag, event_type, payload, event_timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )
        inserted = cur.rowcount
        conn.commit()
        conn.close()
        return inserted

    def get_events_by_share_tag(self, share_tag: str) -> list[dict]:
        """Return all events for a session (useful for debugging/export)."""
        conn = _get_connection(self.db)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, client_id, share_tag, event_type, payload,
                   event_timestamp, received_at
            FROM measurement_events
            WHERE share_tag = ?
            ORDER BY event_timestamp ASC
            """,
            (share_tag,),
        )
        rows = cur.fetchall()
        conn.close()
        return [
            {
                "id": row[0],
                "client_id": row[1],
                "share_tag": row[2],
                "event_type": row[3],
                "payload": json.loads(row[4]),
                "event_timestamp": row[5],
                "received_at": row[6],
            }
            for row in rows
        ]
