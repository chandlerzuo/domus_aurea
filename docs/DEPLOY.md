# Running the game server on a private cloud machine

The server has no accounts, so **the network is the access control**: it binds
to loopback by default and refuses `0.0.0.0`, `::` and public addresses. Players
reach it through an SSH tunnel or a private network (Tailscale / WireGuard).
Nothing is published on ports 80/443, so in mainland China no ICP filing is
needed, and strangers on the internet cannot find it.

Don't open the app port (8770) in the cloud firewall, and don't put it behind a
public reverse proxy. Doing either would make the tables, replays and the
"take a seat" buttons available to anyone who finds the address.

## Capacity and the number of tables

Measured with `scripts/loadtest.py` on an Apple-silicon laptop. Each table has one
scripted human with AI suggestions on, three PPO AIs at the normal pace (0.9 s
per move), and two watchers; every client polls every 0.7 s like the browser.

| Tables | AI agents | Clients | Requests/s | p95 latency | Server CPU (one core = 100%) | Memory |
|---|---|---|---|---|---|---|
| 50 | 150 | 150 | 227 | 17 ms | 20% | 230 MB |
| 100 | 300 | 300 | 453 | 16 ms | 28% | 233 MB |
| 200 | 600 | 600 | 911 | 11 ms | 43% | 235 MB |
| 300 | 900 | 900 | 1362 | 14 ms | 55% | 239 MB |

The AIs kept their pace (about 1.2 moves per table per second) at every load.
Memory is flat because all tables share one copy of each model. Reviews run in a
separate worker process and take 0.1-3 s of CPU each.

What limits a small cloud machine (e.g. Tencent Cloud Lighthouse, 2 vCPU / 4 GB):

- **CPU:** the server is one Python process, so it uses about one core. A
  cloud vCPU runs this kind of Python code roughly 2-2.5× slower than the
  laptop, so about 100 tables (300 AI agents) would use roughly half a core.
  That leaves headroom for bursts, and the second vCPU is left for reviews.
- **Bandwidth:** each poll is about 2.6 KB, which is about 30 kbit/s per open
  browser tab. A 6 Mbps plan carries about 140 tabs at 70% utilisation, which
  is about 45 tables with one player and two watchers each.

The bandwidth limit is the tighter one. **The default is 20 tables** (60 AI
agents, about 60 tabs, about 2 Mbps). That's well within both limits, with
room for 2-3× more watchers than the test assumed. Change it with `--tables N`.
Re-run the load test on the real machine before raising it much
(`python scripts/loadtest.py --tables 20 50 --seconds 60`). Run it on the
server itself, so the tunnel isn't part of the measurement.

## Setup on Tencent Cloud Lighthouse

1. **Create the instance:** Ubuntu 22.04 or later, 2 vCPU / 4 GB. Any region
   works; mainland regions give players in China the lowest latency.
2. **Firewall:** in the console, allow only **SSH (22) from your own IP**.
   Remove the default HTTP/HTTPS rules. Use key-based login and disable password
   SSH (`PasswordAuthentication no` in `/etc/ssh/sshd_config`).
3. **Install:**
   ```bash
   sudo apt update && sudo apt install -y python3-venv git
   git clone <your repo> guandan && cd guandan
   python3 -m venv .venv && .venv/bin/pip install -e .
   ```
   The trained models (`runs/ppo/model.pt`, `runs/dmc/model.pt`) are in the
   repo, so nothing needs training on the server.
4. **Run it as a service:** `/etc/systemd/system/guandan.service`:
   ```ini
   [Unit]
   Description=Guandan game server
   After=network-online.target

   [Service]
   User=ubuntu
   WorkingDirectory=/home/ubuntu/guandan
   ExecStart=/home/ubuntu/guandan/.venv/bin/python -m guandan.server --host 127.0.0.1 --port 8770 --db data/games.db
   Restart=on-failure

   [Install]
   WantedBy=multi-user.target
   ```
   Then `sudo systemctl enable --now guandan` and check with
   `ss -ltnp | grep 8770`. It must show `127.0.0.1:8770`.
5. **Back up the replays:** `data/games.db` holds every finished deal and review.
   Copy it off the machine now and then, e.g. a daily cron job:
   `sqlite3 data/games.db ".backup data/backup-$(date +%F).db"`.

## How players connect

**Option A: SSH tunnel** (you, or anyone you give an SSH key to)

```bash
ssh -N -L 8770:127.0.0.1:8770 ubuntu@<server-ip>
# then open http://127.0.0.1:8770
```

**Option B: Tailscale** (easiest for a group of friends)

1. Install Tailscale on the server and on each player's device, and sign them
   into the same tailnet (invite friends from the Tailscale admin console).
2. Start the server on the Tailscale address instead of loopback:
   `--host 100.x.y.z` (from `tailscale ip -4`). Add `--allow-host <machine-name>`
   if players use the MagicDNS name. The server only accepts loopback,
   Tailscale (100.64.0.0/10) and RFC 1918 private addresses.
3. Players open `http://100.x.y.z:8770`. Only devices in your tailnet can reach it.
   Tailscale encrypts the traffic, so no TLS certificate is needed.

WireGuard works the same way: bind to the server's WireGuard address
(e.g. `10.8.0.1`). In this case, open only the WireGuard UDP port in the firewall.

## Notes

- **Fair play is on the honour system among friends.** A seated player's tab is
  always shown its own seat, but nothing stops someone opening a second
  browser and watching an opponent's seat. The AI-suggestions setting is recorded
  per deal and shown in the deal list.
- **Seats are released** after 90 s without contact (closed tab). An AI takes
  over a player who hasn't acted for 5 minutes. A finished deal moves on to the
  next after 45 s.
- **Restarting the server** ends games in progress. Finished deals and reviews
  are kept in SQLite.
