import json
import threading
import urllib.error
import urllib.request

import pytest

from guandan.server.server import make_server


@pytest.fixture()
def base(tmp_path):
    srv = make_server(0, tmp_path / "users.db")
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def call(base, path, body=None, cookie=None, headers=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data, method="GET" if body is None else "POST")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    if cookie:
        req.add_header("Cookie", cookie)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read()), r.headers.get("Set-Cookie")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read()), None


def login(base):
    code, _, set_cookie = call(base, "/api/register", {"username": "alice", "password": "correct horse"})
    assert code == 200 and "HttpOnly" in set_cookie and "SameSite=Strict" in set_cookie
    return set_cookie.split(";")[0]


def test_auth_required_and_wrong_password(base):
    assert call(base, "/api/me")[0] == 401
    assert call(base, "/api/new", {})[0] == 401
    login(base)
    assert call(base, "/api/login", {"username": "alice", "password": "wrong password"})[0] == 401
    assert call(base, "/api/register", {"username": "alice", "password": "another one"})[0] == 400
    assert call(base, "/api/register", {"username": "bob", "password": "short"})[0] == 400
    assert call(base, "/api/me", cookie="session=forged")[0] == 401


def test_lockout_after_repeated_failures(base):
    login(base)
    for _ in range(5):
        call(base, "/api/login", {"username": "alice", "password": "nope nope"})
    code, body, _ = call(base, "/api/login", {"username": "alice", "password": "correct horse"})
    assert code == 400 and "too many" in body["error"]


def test_rejects_foreign_host_and_non_json(base):
    cookie = login(base)
    assert call(base, "/api/me", cookie=cookie, headers={"Host": "evil.example:80"})[0] == 403
    req = urllib.request.Request(base + "/api/new", data=b"partner=random", method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded", "Cookie": cookie})
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(req)
    assert e.value.code == 415


def test_play_a_full_match_with_hints(base):
    cookie = login(base)
    code, s, _ = call(base, "/api/new", {"partner": "heuristic", "opponents": "random"}, cookie)
    assert code == 200
    for _ in range(20000):
        phase = s["phase"]
        if phase == "match_over":
            break
        if phase == "ai_turn":
            s = call(base, "/api/step", {}, cookie)[1]
        elif phase == "deal_over":
            assert "revealed" in s
            s = call(base, "/api/next", {}, cookie)[1]
        elif phase == "return":
            card = call(base, "/api/hint", {}, cookie)[1]["cards"][0]
            s = call(base, "/api/return", {"card": card}, cookie)[1]
        else:
            # Opponents' cards are never sent while the deal is live.
            assert "revealed" not in s and len(s["hand"]) == s["seats"][0]["cards_left"]
            cards = call(base, "/api/hint", {}, cookie)[1]["cards"]
            code, s, _ = call(base, "/api/play", {"cards": cards}, cookie)
            assert code == 200, s
    assert s["phase"] == "match_over"
    me = call(base, "/api/me", cookie=cookie)[1]
    assert me["stats"]["matches_won"] + me["stats"]["matches_lost"] == 1


def test_invalid_play_rejected(base):
    cookie = login(base)
    s = call(base, "/api/new", {"partner": "heuristic", "opponents": "heuristic"}, cookie)[1]
    while s["phase"] == "ai_turn":
        s = call(base, "/api/step", {}, cookie)[1]
    if s["phase"] == "your_turn":
        assert call(base, "/api/play", {"cards": [999]}, cookie)[0] == 400
