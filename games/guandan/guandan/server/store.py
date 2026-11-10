"""SQLite storage for finished deals (replays) and their reviews."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path


def team0_result(record: dict) -> int:
    """Levels gained by South/North in the deal (negative if East/West won)."""
    r = record["result"]
    return r["up"] if r["win_team"] == 0 else -r["up"]


class Store:
    def __init__(self, path: str | Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.lock = threading.Lock()
        with self.lock, self.db:
            self.db.execute("""CREATE TABLE IF NOT EXISTS deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT, table_id INTEGER NOT NULL, match_id TEXT NOT NULL,
                deal_no INTEGER NOT NULL, finished REAL NOT NULL, humans TEXT NOT NULL,
                assisted TEXT NOT NULL, result INTEGER NOT NULL, record TEXT NOT NULL,
                reviews TEXT NOT NULL DEFAULT '{}')""")
            self.db.execute("CREATE INDEX IF NOT EXISTS deals_match ON deals (match_id)")

    def save_deal(self, record: dict) -> int:
        with self.lock, self.db:
            cur = self.db.execute(
                "INSERT INTO deals (table_id, match_id, deal_no, finished, humans, assisted, result, record) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (record["table"], record["match"], record["deal_no"], time.time(), json.dumps(record["humans"]),
                 json.dumps(record["assisted"]), team0_result(record), json.dumps(record)))
            return int(cur.lastrowid)

    def deal(self, deal_id: int) -> dict | None:
        with self.lock:
            row = self.db.execute("SELECT record FROM deals WHERE id = ?", (deal_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def deals(self, match_id: str | None = None, limit: int = 50) -> list[dict]:
        q = "SELECT id, table_id, match_id, deal_no, finished, humans, assisted, result FROM deals"
        args: tuple = ()
        if match_id:
            q += " WHERE match_id = ?"
            args = (match_id,)
        q += " ORDER BY id DESC LIMIT ?"
        with self.lock:
            rows = self.db.execute(q, args + (limit,)).fetchall()
        keys = ("id", "table", "match", "deal_no", "finished", "humans", "assisted", "result")
        out = [dict(zip(keys, r)) for r in rows]
        for d in out:
            d["humans"], d["assisted"] = json.loads(d["humans"]), json.loads(d["assisted"])
        return out

    def review(self, deal_id: int, seat: int) -> dict | None:
        with self.lock:
            row = self.db.execute("SELECT reviews FROM deals WHERE id = ?", (deal_id,)).fetchone()
        return json.loads(row[0]).get(str(seat)) if row else None

    def save_review(self, deal_id: int, seat: int, review: dict) -> None:
        with self.lock, self.db:
            row = self.db.execute("SELECT reviews FROM deals WHERE id = ?", (deal_id,)).fetchone()
            reviews = json.loads(row[0]) if row else {}
            reviews[str(seat)] = review
            self.db.execute("UPDATE deals SET reviews = ? WHERE id = ?", (json.dumps(reviews), deal_id))
