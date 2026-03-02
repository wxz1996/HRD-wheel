from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Tuple


class StatusMemoryStore:
    def __init__(self, db_path: str = "mvp/data/cloud_memory.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS nav_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                msg_id TEXT NOT NULL,
                robot_id TEXT NOT NULL,
                cmd_id TEXT NOT NULL,
                ts INTEGER NOT NULL,
                status TEXT NOT NULL,
                detail TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def save_status(self, msg: dict) -> None:
        self.conn.execute(
            "INSERT INTO nav_status(msg_id, robot_id, cmd_id, ts, status, detail) VALUES (?, ?, ?, ?, ?, ?)",
            (
                msg["msg_id"],
                msg["robot_id"],
                msg["cmd_id"],
                msg["ts"],
                msg["status"],
                str(msg["detail"]),
            ),
        )
        self.conn.commit()

    def list_statuses(self, robot_id: str) -> List[Tuple]:
        cur = self.conn.execute(
            "SELECT msg_id, robot_id, cmd_id, ts, status, detail FROM nav_status WHERE robot_id = ? ORDER BY id",
            (robot_id,),
        )
        return cur.fetchall()
