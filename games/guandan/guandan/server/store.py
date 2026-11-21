"""SQLite storage for finished deals (replays) and their reviews."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path


def ai_name(model: str) -> str:
    """How an AI seat is listed: by the version of the model that played (see tables.model_id)."""
    return "AI " + (model.split("/")[0] if model else "未标记版本")


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
            # One row per player per deal, for the ranking and the player pages. Humans are identified by name (case sensitive),
            # AI seats by the model version that played.
            self.db.execute("""CREATE TABLE IF NOT EXISTS placements (
                deal_id INTEGER NOT NULL, seat INTEGER NOT NULL, finished REAL NOT NULL, name TEXT NOT NULL, ai INTEGER NOT NULL,
                model TEXT NOT NULL DEFAULT '', points INTEGER NOT NULL, place INTEGER NOT NULL, PRIMARY KEY (deal_id, seat))""")
            self.db.execute("CREATE INDEX IF NOT EXISTS placements_player ON placements (ai, name, finished)")
            self.db.execute("CREATE INDEX IF NOT EXISTS placements_time ON placements (finished)")
            for deal_id, finished, rec in self.db.execute(
                    "SELECT id, finished, record FROM deals WHERE id NOT IN (SELECT DISTINCT deal_id FROM placements)").fetchall():
                self._add_placements(deal_id, finished, json.loads(rec))

    def _add_placements(self, deal_id: int, finished: float, record: dict) -> None:
        win, up = record["result"]["win_team"], record["result"]["up"]
        order = record.get("finished") or []
        for seat in range(4):
            human = record["kinds"][seat] == "human"
            models = record.get("models") or []
            model = (models[seat] if seat < len(models) and models[seat] else record.get("model", ""))   # per seat since two AI variants run at once
            name = record["names"][seat] if human else ai_name(model)
            if seat not in order:
                continue
            self.db.execute(
                "INSERT OR REPLACE INTO placements (deal_id, seat, finished, name, ai, model, points, place) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (deal_id, seat, finished, name, 0 if human else 1, "" if human else model,
                 up if seat % 2 == win else -up, order.index(seat) + 1))

    def save_deal(self, record: dict) -> int:
        with self.lock, self.db:
            now = time.time()
            cur = self.db.execute(
                "INSERT INTO deals (table_id, match_id, deal_no, finished, humans, assisted, result, record) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (record["table"], record["match"], record["deal_no"], now, json.dumps(record["humans"]),
                 json.dumps(record["assisted"]), team0_result(record), json.dumps(record)))
            self._add_placements(int(cur.lastrowid), now, record)
            return int(cur.lastrowid)

    # ---- ranking and player history ------------------------------------------------------------------------------

    def leaderboard(self, days: float = 7, limit: int = 10, min_games: int = 5, now: float | None = None) -> list[dict]:
        """Players of the last `days` days by average points per deal (the levels their team gained, negative when it lost),
        with how often they finished 1st-4th. A player needs `min_games` deals to be listed."""
        since = (time.time() if now is None else now) - days * 86400
        with self.lock:
            rows = self.db.execute(
                "SELECT ai, name, COUNT(*), AVG(points), SUM(place = 1), SUM(place = 2), SUM(place = 3), SUM(place = 4), MAX(model) "
                "FROM placements WHERE finished >= ? GROUP BY ai, name HAVING COUNT(*) >= ? "
                "ORDER BY AVG(points) DESC, COUNT(*) DESC, name LIMIT ?", (since, min_games, limit)).fetchall()
        return [{"rank": i + 1, "ai": bool(r[0]), "name": r[1], "games": r[2], "avg": round(r[3], 3),
                 "places": [round(r[4 + k] / r[2], 4) for k in range(4)], "model": r[8]} for i, r in enumerate(rows)]

    def player(self, name: str, ai: bool, limit: int = 100, now: float | None = None) -> dict:
        """History of one player: totals, the last 7 days, a per-day summary and the most recent deals."""
        now = time.time() if now is None else now
        with self.lock:
            def agg(since: float) -> dict:
                r = self.db.execute(
                    "SELECT COUNT(*), AVG(points), SUM(place = 1), SUM(place = 2), SUM(place = 3), SUM(place = 4) "
                    "FROM placements WHERE ai = ? AND name = ? AND finished >= ?", (int(ai), name, since)).fetchone()
                n = r[0]
                return {"games": n, "avg": round(r[1], 3) if n else None, "places": [round((r[2 + k] or 0) / n, 4) for k in range(4)] if n else [0] * 4}
            total, week = agg(0), agg(now - 7 * 86400)
            days = self.db.execute(
                "SELECT date(finished, 'unixepoch', 'localtime') d, COUNT(*), AVG(points) FROM placements "
                "WHERE ai = ? AND name = ? AND finished >= ? GROUP BY d ORDER BY d DESC", (int(ai), name, now - 14 * 86400)).fetchall()
            mine = self.db.execute(
                "SELECT p.deal_id, p.seat, p.finished, p.points, p.place, p.model, d.table_id, d.deal_no FROM placements p "
                "JOIN deals d ON d.id = p.deal_id WHERE p.ai = ? AND p.name = ? ORDER BY p.finished DESC LIMIT ?",
                (int(ai), name, limit)).fetchall()
            others: dict[int, list] = {}
            for deal_id in {r[0] for r in mine}:
                others[deal_id] = self.db.execute("SELECT seat, name, ai FROM placements WHERE deal_id = ?", (deal_id,)).fetchall()
        deals = []
        for deal_id, seat, finished, points, place, model, table_id, deal_no in mine:
            people = others.get(deal_id, [])
            deals.append({"deal": deal_id, "time": finished, "table": table_id, "deal_no": deal_no, "seat": seat, "points": points,
                          "place": place, "model": model,
                          "partner": [n for s, n, a in people if s == (seat + 2) % 4],
                          "opponents": [n for s, n, a in people if s % 2 != seat % 2]})
        return {"name": name, "ai": bool(ai), "total": total, "week": week,
                "days": [{"day": d, "games": n, "avg": round(a, 3)} for d, n, a in days], "deals": deals}

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
