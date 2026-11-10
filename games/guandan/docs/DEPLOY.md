# Running the game server on a cloud machine

> **In the Xanadu repo** both games are deployed together with the top-level `deploy/setup.sh` (see the root README): one HTTPS address, one login, a portal at `/`, and this game under `/guandan/`. This document describes the standalone Guandan setup.

For the exact step-by-step setup with public browser access (Hong Kong Lighthouse,
shared password), see [SERVER_SPEC.md](SERVER_SPEC.md). This page explains the
options and the capacity measurements behind them.

The game server has no accounts and always binds to loopback (or a private
Tailscale/WireGuard address). It refuses `0.0.0.0`, `::` and public addresses.
There are two ways to let people in:

| | Private (default) | Browser access from anywhere (`--public`) |
|---|---|---|
| How players connect | SSH tunnel or Tailscale/WireGuard | type `https://<server-ip>` (or your domain) in any browser |
| Who can reach it | only people you give SSH or tailnet access | anyone on the internet can reach the login prompt; only people with the shared password get past it |
| What's public | nothing (only SSH, limited to your IP) | nginx on 443 (80 redirects to HTTPS). The game server stays on 127.0.0.1 behind it |
| Certificate | not needed (tunnel encrypts) | self-signed for the IP (one-time browser warning), or Let's Encrypt with `--domain` |
| Mainland China | no ICP filing needed | a public website needs an ICP filing (备案), even by IP; use a Hong Kong/Singapore region to avoid it |

Never open the game port (8770) itself in the firewall, and never put the game
behind a proxy without the password: the tables, the replays and the
"take a seat" buttons have no login of their own.

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

The bandwidth limit is the tighter one. **The default is 10 tables** (30 AI
agents, about 30 tabs, about 1 Mbps), far inside both limits. Change it with
`--tables N` (or `setup_lighthouse.sh --tables N`). Re-run the load test on the
real machine before raising it much
(`python scripts/loadtest.py --tables 10 30 --seconds 60`). Run it on the server
itself, so the tunnel isn't part of the measurement.

## The search AI and the Rust core

The default AI, `ppo+` ("PPO+搜索"), looks ahead with the PPO policy and needs the Rust core
(`guandan_core`). `make_bundle.sh` cross-compiles it for the server (Linux x86-64, glibc 2.28+) and
puts the wheel in the bundle; this needs `pip install maturin ziglang` and a Rust toolchain on
the machine that builds the bundle. If the wheel can't be built, or won't install on the server,
setup says so, the server runs the Python engine, and `ppo+` is not offered (hosts get `ppo`).
The setup self-check prints `engine: rust` and `search AI (ppo+): on` when it works.

Each `ppo+` move took about 30-50 ms of one core on the development laptop with the defaults (32
sampled hands, top 4 moves); expect about twice that on a cloud vCPU. Compare that with the 0.9 s
pacing between AI moves. To tune it, set these in the service environment: `GUANDAN_SEARCH_WORLDS`,
`GUANDAN_SEARCH_TOPK`, or `GUANDAN_SEARCH=0` to turn it off. Re-run `scripts/loadtest.py` on the
server before raising the table count if most seats are `ppo+`.

## Getting the code onto a server in China

Servers in mainland China often can't reach GitHub, and PyPI is slow there.
PyTorch's own download site may also be unreachable. There are three ways
around this, from most to least reliable:

1. **Offline bundle (recommended).** On your own computer,
   `deploy/make_bundle.sh` packs the committed code, the trained models and
   Linux wheels for numpy and CPU-only PyTorch into one file (about 260 MB).
   Copy it over with `scp`. The server then needs nothing from the internet
   except its own apt mirror, which Lighthouse images already point at Tencent.
   If `scp` is slow from where you are, upload the bundle to a **private** COS
   bucket and download it on the server with a short-lived presigned URL.
   Don't make the bucket or the object public.
2. **A git mirror inside China.** Push this repo to a *private* repo on Gitee
   or Tencent CNB (`git remote add gitee git@gitee.com:<you>/guandan.git && git push gitee main`),
   then run `setup_lighthouse.sh --repo <url>`. With a private repo, give the
   server a read-only deploy key or token. In this mode Python packages come
   from Tencent Cloud's PyPI mirror (`--pip-index`, default
   `https://mirrors.cloud.tencent.com/pypi/simple`) and PyTorch from
   `--torch-index` (default `https://download.pytorch.org/whl/cpu`). If that
   index is unreachable, the script falls back to the PyPI mirror, whose Linux
   PyTorch build pulls about 2 GB of CUDA libraries. It works, but it's slow
   and large, which is one more reason to prefer the bundle.
3. **A Hong Kong or Singapore region**, where GitHub and PyPI work normally.
   This costs some latency for players in mainland China.

## One-step setup on Tencent Cloud Lighthouse

1. **Create the instance:** Ubuntu **24.04** image (Python 3.12; 22.04's 3.10 is
   too old), 2 vCPU / 4 GB, x86-64. Mainland regions give players in China the
   lowest latency.
2. **Firewall** (Lighthouse console): allow only **SSH (22) from your own IP**.
   Remove the default HTTP/HTTPS rules, unless you use `--public` (then keep 80/443).
   Never add the game port.
3. **Build and copy the bundle** on your computer:
   ```bash
   deploy/make_bundle.sh                       # dist/guandan-<rev>.tar.gz
   scp dist/guandan-<rev>.tar.gz ubuntu@<server-ip>:~
   ```
4. **Run the setup** on the server:
   ```bash
   tar xzf guandan-<rev>.tar.gz && sudo bash guandan-<rev>/deploy/setup_lighthouse.sh
   ```
   It installs the Python packages offline from the bundle and puts the code
   in `/opt/guandan/app`, read-only to the service. It creates a `guandan`
   system user and a hardened systemd service bound to `127.0.0.1:8770`, and a
   daily database backup (`/var/lib/guandan/backups`, kept 14 days). It then
   checks that the port is listening **only** on the expected address and
   that the lobby answers.
   Options: `--tables N`, `--port P`, `--host tailscale` (see below),
   `--repo URL` (install from a git mirror instead of the bundle), and
   `--public` for browser access from anywhere (see below).
5. **By hand:** use key-based SSH and set `PasswordAuthentication no` in
   `/etc/ssh/sshd_config`. The script doesn't change SSH settings, so it can't
   lock you out. Copy `/var/lib/guandan/backups` off the machine now and then.

**Upgrade:** commit, build a new bundle, copy it over, and run the setup again.
The code is replaced and the database is kept. Restarting ends games in
progress; finished deals and reviews are kept.

Useful commands: `systemctl status guandan`, `journalctl -u guandan -f`,
`ss -ltnp | grep 8770` (must show `127.0.0.1:8770`).

## Browser access from anywhere (shared password)

```bash
sudo bash guandan-<rev>/deploy/setup_lighthouse.sh --public
```

On top of the normal setup, this installs nginx as the only public listener:

- **HTTPS on 443**, with port 80 redirecting to it. Without a domain, the
  certificate is self-signed for the server's public IP (found through Tencent
  Cloud's metadata service, or pass `--public-ip`). Each browser shows a "not
  private" warning once ("Advanced" → "Proceed"). Traffic, including the
  password, is still encrypted.
- **A shared login** (HTTP basic auth), checked by nginx before any request
  reaches the game. The script generates a 20-character random password unless
  you pass `--password`, prints it once, and saves it in
  `/root/guandan-login.txt` (root only). Re-runs keep it. The login name
  defaults to `guandan` (`--login-user`).
- **A per-IP rate limit** of 10 requests/s (burst 40). That's plenty for a few
  tabs behind one home router, and it makes guessing the password hopeless.
- **A check before finishing:** an anonymous request must get 401 and a
  request with the login must get 200, otherwise the script stops with an
  error.

Then, in the Lighthouse console firewall, allow TCP 80 and 443 (from anywhere,
or only your friends' IPs if you know them). Keep SSH limited to your IP, and
don't open 8770. Players open `https://<server-ip>`, accept the certificate
warning once, and enter the shared login.

- **Change the password:** `sudo bash /opt/guandan/app/deploy/public_access.sh --password '<new one>'`
  (everyone has to log in again).
- **Get rid of the certificate warning:** point a domain at the server, then run
  `sudo bash /opt/guandan/app/deploy/public_access.sh --domain play.example.com --email you@example.com`.
  On a mainland server the domain needs an ICP filing first.
- **Go back to private:** `sudo rm /etc/nginx/sites-enabled/guandan && sudo systemctl stop nginx`,
  and remove the 80/443 firewall rules.

Anyone with the password can do everything a player can, including reading all
replays. Share it like a house key, and change it if it leaks.

## How players connect (private mode)

**Option A: SSH tunnel** (you, or anyone you give an SSH key to)

```bash
ssh -N -L 8770:127.0.0.1:8770 ubuntu@<server-ip>
# then open http://127.0.0.1:8770
```

**Option B: Tailscale** (easiest for a group of friends)

1. Install Tailscale on the server and on each player's device, and sign them
   into the same tailnet (invite friends from the Tailscale admin console).
2. Bind the server to the Tailscale address instead of loopback:
   `sudo bash .../setup_lighthouse.sh --host tailscale` (or run the server with
   `--host 100.x.y.z` from `tailscale ip -4`, plus `--allow-host <machine-name>`
   if players use the MagicDNS name). The server only accepts loopback,
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
