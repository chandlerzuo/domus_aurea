"""Load test: how many tables can one server process carry?

Starts the real server in a subprocess with N tables. Each table gets one
scripted human (with AI suggestions on, the costliest case), three PPO AIs at
the normal pace, and W watchers; every client polls like the browser does
(every 0.7 s). Reports request latency, the server's CPU (100% = one core),
memory, and whether the AIs kept their pace.

  python scripts/loadtest.py --tables 10 20 40 --watchers 2 --seconds 40
"""
import argparse
import json
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLL = 0.7


def call(base, path, body=None, token=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data, method="GET" if body is None else "POST")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("X-Seat-Token", token)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def ps(pid):
    """(cumulative CPU seconds, RSS MB) of the server process."""
    out = subprocess.run(["ps", "-o", "time=,rss=", "-p", str(pid)], capture_output=True, text=True).stdout.split()
    t = 0.0
    for part in out[0].split(":"):
        t = t * 60 + float(part)
    return t, int(out[1]) / 1024


def run(tables: int, watchers: int, seconds: float, port: int) -> dict:
    db = f"/tmp/gd_load_{tables}.db"
    Path(db).unlink(missing_ok=True)
    srv = subprocess.Popen([sys.executable, "-m", "guandan.server", "--port", str(port), "--tables", str(tables),
                            "--db", db], cwd=ROOT, stdout=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            call(base, "/api/lobby")
            break
        except OSError:
            time.sleep(0.1)
    lat, moves, stop = [], [0], threading.Event()
    lock = threading.Lock()

    def timed(*a, **k):
        t = time.perf_counter()
        r = call(*a, **k)
        with lock:
            lat.append(time.perf_counter() - t)
        return r

    def player(tid):
        tok = timed(base, f"/api/table/{tid}/sit", {"seat": 0, "name": "bot", "suggestions": True})["token"]
        for seat in (1, 2, 3):
            timed(base, f"/api/table/{tid}/seat", {"seat": seat, "kind": "ppo"}, tok)
        timed(base, f"/api/table/{tid}/start", {}, tok)
        seen = (0, 0)
        while not stop.is_set():
            s = timed(base, f"/api/table/{tid}/state", token=tok)
            now = (s["deal_no"], s["moves_in_deal"])
            with lock:
                moves[0] += now[1] - seen[1] if now[0] == seen[0] else now[1]
            seen = now
            if s["phase"] == "deal_over":
                timed(base, f"/api/table/{tid}/next", {}, tok)
            elif s["phase"] == "return" and 0 in s["waiting_on"]:
                timed(base, f"/api/table/{tid}/return", {"card": s["return_options"][0]}, tok)
            elif s["phase"] == "human_turn" and 0 in s["waiting_on"]:
                pick = s["suggestions"][0]["cards"]  # follow the AI's suggestion, as fast as a quick human
                timed(base, f"/api/table/{tid}/play", {"cards": pick}, tok)
            time.sleep(POLL)

    def watcher(tid, seat):
        while not stop.is_set():
            timed(base, f"/api/table/{tid}/state?seat={seat}")
            time.sleep(POLL)

    threads = [threading.Thread(target=player, args=(t,), daemon=True) for t in range(1, tables + 1)]
    threads += [threading.Thread(target=watcher, args=(t, 1 + w % 3), daemon=True)
                for t in range(1, tables + 1) for w in range(watchers)]
    for th in threads:
        th.start()
    time.sleep(5)  # warm-up: model loading, tables starting
    with lock:
        lat.clear()
        moves[0] = 0
    cpu, rss, t0 = [], [], time.time()
    last_c, last_t = ps(srv.pid)[0], t0
    while time.time() - t0 < seconds:
        time.sleep(2)
        c, r = ps(srv.pid)
        now = time.time()
        cpu.append(100 * (c - last_c) / (now - last_t))  # % of one core over the interval
        last_c, last_t = c, now
        rss.append(r)
    stop.set()
    elapsed = time.time() - t0
    srv.terminate()
    srv.wait()
    lat.sort()
    pct = lambda q: 1000 * lat[min(len(lat) - 1, int(q * len(lat)))] if lat else float("nan")
    return {"tables": tables, "clients": tables * (1 + watchers), "req_per_s": len(lat) / elapsed,
            "p50_ms": pct(0.5), "p95_ms": pct(0.95), "p99_ms": pct(0.99),
            "cpu_pct": sum(cpu) / len(cpu), "cpu_max": max(cpu), "rss_mb": max(rss),
            "moves_per_table_per_s": moves[0] / elapsed / tables}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tables", type=int, nargs="+", default=[2, 10, 20, 40])
    ap.add_argument("--watchers", type=int, default=2)
    ap.add_argument("--seconds", type=float, default=40)
    ap.add_argument("--port", type=int, default=8790)
    a = ap.parse_args()
    print(f"{'tables':>6} {'clients':>7} {'req/s':>6} {'p50ms':>6} {'p95ms':>6} {'p99ms':>6} "
          f"{'cpu%':>5} {'max%':>5} {'MB':>5} {'moves/t/s':>9}")
    for n in a.tables:
        r = run(n, a.watchers, a.seconds, a.port)
        print(f"{r['tables']:>6} {r['clients']:>7} {r['req_per_s']:>6.0f} {r['p50_ms']:>6.1f} {r['p95_ms']:>6.1f} "
              f"{r['p99_ms']:>6.1f} {r['cpu_pct']:>5.0f} {r['cpu_max']:>5.0f} {r['rss_mb']:>5.0f} "
              f"{r['moves_per_table_per_s']:>9.2f}", flush=True)
