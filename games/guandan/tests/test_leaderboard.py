import time

from guandan.server.store import Store


def record(names, kinds, finished, win_team, up, model="abcd1234/w32k4b1/eg28", table=1, deal_no=1):
    return {"table": table, "match": "m", "deal_no": deal_no, "humans": [s for s in range(4) if kinds[s] == "human"], "assisted": [],
            "names": names, "kinds": kinds, "finished": finished, "result": {"win_team": win_team, "up": up}, "model": model,
            "moves": [], "hands": [[], [], [], []]}


def seed(store, now):
    # Ann (seat 0, team 0) with an AI partner beats two AIs three times; "ann" (another person) loses twice
    for k in range(3):
        store.save_deal(record(["Ann", "ai", "ai2", "ai3"], ["human", "ppo+", "ppo+", "ppo+"], [0, 1, 2, 3], 0, 3, deal_no=k))
    for k in range(2):
        store.save_deal(record(["ann", "ai", "ai2", "ai3"], ["human", "ppo+", "ppo+", "ppo+"], [1, 3, 0, 2], 1, 2, deal_no=k))


def test_ranking_is_by_average_points_and_names_are_case_sensitive(tmp_path):
    s = Store(tmp_path / "g.db")
    seed(s, time.time())
    board = s.leaderboard(min_games=2)
    names = [p["name"] for p in board]
    assert "Ann" in names and "ann" in names                      # two different players
    ann = next(p for p in board if p["name"] == "Ann")
    assert ann["games"] == 3 and ann["avg"] == 3.0 and ann["places"] == [1.0, 0.0, 0.0, 0.0]
    low = next(p for p in board if p["name"] == "ann")
    assert low["avg"] == -2.0 and low["places"] == [0.0, 0.0, 1.0, 0.0] and not low["ai"]   # seat 0 finished 3rd both times
    assert board[0]["name"] == "Ann" and [p["rank"] for p in board] == list(range(1, len(board) + 1))
    for p in board:
        assert abs(sum(p["places"]) - 1) < 1e-3


def test_ai_seats_are_listed_by_model_version_and_minimum_games_applies(tmp_path):
    s = Store(tmp_path / "g.db")
    seed(s, time.time())
    board = s.leaderboard(min_games=1, limit=50)
    ai = [p for p in board if p["ai"]]
    assert [p["name"] for p in ai] == ["AI abcd1234"] and ai[0]["model"].startswith("abcd1234")
    assert ai[0]["games"] == 15                                        # three AI seats in each of five deals
    assert s.leaderboard(min_games=6, limit=50)[0]["name"] == "AI abcd1234"   # only the AI has that many games
    assert all(p["games"] >= 6 for p in s.leaderboard(min_games=6, limit=50))


def test_only_the_last_seven_days_count(tmp_path):
    s = Store(tmp_path / "g.db")
    seed(s, time.time())
    old = time.time() - 10 * 86400
    with s.lock, s.db:
        s.db.execute("UPDATE placements SET finished = ? WHERE name = 'Ann'", (old,))
    assert "Ann" not in [p["name"] for p in s.leaderboard(min_games=1)]
    assert "Ann" in [p["name"] for p in s.leaderboard(days=30, min_games=1)]
    assert s.player("Ann", False)["total"]["games"] == 3 and s.player("Ann", False)["week"]["games"] == 0


def test_player_history(tmp_path):
    s = Store(tmp_path / "g.db")
    seed(s, time.time())
    h = s.player("ann", False)
    assert h["total"]["games"] == 2 and len(h["deals"]) == 2
    d = h["deals"][0]
    assert d["points"] == -2 and d["place"] == 3 and d["partner"] == ["AI abcd1234"] and sorted(d["opponents"]) == ["AI abcd1234", "AI abcd1234"]
    assert s.player("nobody", False)["total"]["games"] == 0


def test_existing_deals_are_backfilled(tmp_path):
    path = tmp_path / "g.db"
    s = Store(path)
    seed(s, time.time())
    with s.lock, s.db:
        s.db.execute("DROP TABLE placements")
    t = Store(path)                                                   # opening the database rebuilds the table
    assert t.leaderboard(min_games=3)[0]["name"] == "Ann"


def test_ai_seats_are_listed_by_their_own_variant(tmp_path):
    s = Store(tmp_path / "g.db")
    models = ["", "abcd1234/w32k4b1/eg28", "", "abcd1234+s99887766/w32k4b1/eg28"]      # seat 1: v5, seat 3: v5 + sequence guesser
    r = record(["Ann", "x", "y", "z"], ["human", "ppo+", "ppo+", "ppo+"], [0, 1, 2, 3], 0, 3)
    r["models"] = ["", models[1], models[1], models[3]]
    for k in range(6):
        s.save_deal(r)
    names = {p["name"] for p in s.leaderboard(min_games=1, limit=50) if p["ai"]}
    assert names == {"AI abcd1234", "AI abcd1234+s99887766"}
    by = {p["name"]: p for p in s.leaderboard(min_games=1, limit=50) if p["ai"]}
    assert by["AI abcd1234"]["games"] == 12 and by["AI abcd1234+s99887766"]["games"] == 6     # two seats use v5, one the guesser
