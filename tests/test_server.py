import json
import threading
import time
import urllib.error
import urllib.request

import pytest

from guandan.server.server import check_bind, make_server


@pytest.fixture()
def base(tmp_path):
    srv = make_server("127.0.0.1", 0, tmp_path / "games.db", tables=2, ai_delay=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.lobby.stop()


def call(base, path, body=None, token=None, headers=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data, method="GET" if body is None else "POST")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("X-Seat-Token", token)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def sit(base, table, seat, name):
    code, s = call(base, f"/api/table/{table}/sit", {"seat": seat, "name": name})
    assert code == 200, s
    return s["token"]


def test_bind_policy():
    for ok in ("127.0.0.1", "100.101.2.3", "10.0.0.5", "192.168.1.9"):
        check_bind(ok)
    for bad in ("0.0.0.0", "::", "8.8.8.8", "myhost"):
        with pytest.raises(SystemExit):
            check_bind(bad)


def test_rejects_foreign_host_and_non_json(base):
    assert call(base, "/api/lobby", headers={"Host": "evil.example:80"})[0] == 403
    req = urllib.request.Request(base + "/api/table/1/sit", data=b"seat=0", method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(req)
    assert e.value.code == 415


def test_host_controls_and_start(base):
    alice = sit(base, 1, 0, "Alice")
    bob = sit(base, 1, 2, "Bob")
    lobby = call(base, "/api/lobby")[1]["tables"][0]
    assert lobby["status"] == "waiting" and lobby["host"] == 0 and lobby["seats"][2]["name"] == "Bob"
    assert call(base, "/api/table/1/sit", {"seat": 2})[0] == 409            # taken
    assert call(base, "/api/table/1/seat", {"seat": 1, "kind": "heuristic"}, bob)[0] == 409  # not host
    assert call(base, "/api/table/1/start", {}, alice)[0] == 400           # seats still empty
    assert call(base, "/api/table/1/seat", {"seat": 1, "kind": "heuristic"}, alice)[0] == 200
    assert call(base, "/api/table/1/seat", {"seat": 3, "kind": "random"}, alice)[0] == 200
    assert call(base, "/api/table/1/seat", {"seat": 2, "kind": "random"}, alice)[0] == 409   # Bob is there
    assert call(base, "/api/table/1/start", {}, bob)[0] == 409
    code, s = call(base, "/api/table/1/start", {}, alice)
    assert code == 200 and s["status"] == "playing" and s["my_seat"] == 0
    assert call(base, "/api/table/1/sit", {"seat": 1})[0] == 409            # no joining mid-match


def test_host_handover_and_reset(base):
    alice = sit(base, 2, 0, "Alice")
    sit(base, 2, 3, "Carol")
    call(base, "/api/table/2/leave", {}, alice)
    t = call(base, "/api/lobby")[1]["tables"][1]
    assert t["host"] == 3 and t["seats"][0]["kind"] == "empty"
    assert call(base, "/api/table/1/sit", {"seat": 0})[0] == 200           # other table unaffected


def test_watcher_sees_only_one_hand_and_players_only_their_own(base):
    alice = sit(base, 1, 0, "Alice")
    for seat in (1, 2, 3):
        call(base, "/api/table/1/seat", {"seat": seat, "kind": "heuristic"}, alice)
    call(base, "/api/table/1/start", {}, alice)
    w = call(base, "/api/table/1/state?seat=2")[1]
    assert w["my_seat"] is None and w["view_seat"] == 2 and not w["as_player"]
    assert len(w["hand"]) == w["seats"][2]["cards_left"] and "revealed" not in w
    assert "suggestions" not in w and "return_options" not in w
    p = call(base, "/api/table/1/state?seat=2", token=alice)[1]
    assert p["view_seat"] == 0 and p["as_player"]                         # can't peek via ?seat=
    assert call(base, "/api/table/1/play", {"cards": []})[0] == 409       # watchers can't act


def play_until_done(base, tokens, deals=2, max_requests=20000):
    """Humans lead their lowest card and otherwise pass, until `deals` deals have finished."""
    s = None
    for _ in range(max_requests):
        progressed = False
        for table, tok in tokens:
            s = call(base, f"/api/table/{table}/state", token=tok)[1]
            if s.get("phase") == "match_over" or len(s.get("deal_ids", [])) >= deals:
                return s
            me = s["my_seat"]
            if s["phase"] == "deal_over":
                call(base, f"/api/table/{table}/next", {}, tok)
                progressed = True
            elif s["phase"] == "return" and me in s["waiting_on"]:
                assert call(base, f"/api/table/{table}/return", {"card": s["return_options"][0]}, tok)[0] == 200
                progressed = True
            elif s["phase"] == "human_turn" and me in s["waiting_on"]:
                cards = [s["hand"][0]["id"]] if s["leading"] else []
                code, r = call(base, f"/api/table/{table}/play", {"cards": cards}, tok)
                assert code == 200, r
                progressed = True
        if not progressed:
            time.sleep(0.02)  # the driver thread is playing AI moves
    return s


def test_two_humans_play_deals_then_replay(base):
    alice, bob = sit(base, 1, 0, "Alice"), sit(base, 1, 1, "Bob")
    call(base, "/api/table/1/seat", {"seat": 2, "kind": "heuristic"}, alice)
    call(base, "/api/table/1/seat", {"seat": 3, "kind": "heuristic"}, alice)
    call(base, "/api/table/1/start", {}, alice)
    s = play_until_done(base, [(1, alice), (1, bob)])
    assert len(s["deal_ids"]) >= 2
    deals = call(base, f"/api/deals?match={s['match']}")[1]
    assert len(deals) == len(s["deal_ids"]) and deals[0]["humans"] == [0, 1]
    rec = call(base, f"/api/deal/{s['deal_ids'][0]}")[1]
    assert rec["names"][:2] == ["Alice", "Bob"] and len(rec["leads"]) == len(rec["moves"]) and rec["leads"][0]
    assert call(base, f"/api/deal/{s['deal_ids'][0]}/review?seat=1")[1]["status"] == "none"


def test_leaving_mid_match_hands_seat_to_ai(base):
    alice, bob = sit(base, 1, 0, "Alice"), sit(base, 1, 2, "Bob")
    for seat in (1, 3):
        call(base, "/api/table/1/seat", {"seat": seat, "kind": "heuristic"}, alice)
    call(base, "/api/table/1/start", {}, alice)
    call(base, "/api/table/1/leave", {}, bob)
    t = call(base, "/api/lobby")[1]["tables"][0]
    assert t["status"] == "playing" and t["seats"][2]["kind"] != "human"
    call(base, "/api/table/1/leave", {}, alice)
    assert call(base, "/api/lobby")[1]["tables"][0]["status"] == "open"


def test_search_ai_is_offered_and_plays_a_deal(base):
    pytest.importorskip("guandan_core")
    from guandan.server.tables import MODELS
    if not MODELS["ppo"].exists():
        pytest.skip("no trained PPO model")
    assert "ppo+" in call(base, "/api/lobby")[1]["agents"]
    alice = sit(base, 1, 0, "Alice")
    for seat in (1, 2, 3):
        assert call(base, "/api/table/1/seat", {"seat": seat, "kind": "ppo+"}, alice)[0] == 200
    s = call(base, "/api/table/1/start", {}, alice)[1]
    assert [x["kind"] for x in s["seats"]] == ["human", "ppo+", "ppo+", "ppo+"]
    s = play_until_done(base, [(1, alice)], deals=1, max_requests=40000)
    assert len(s["deal_ids"]) >= 1


def test_default_ai_is_the_search_player_when_available():
    from guandan.server.tables import default_ai, search_available
    assert default_ai() == ("ppo+" if search_available() else "ppo")
