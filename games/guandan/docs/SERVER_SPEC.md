# SPEC: Guandan game server on Tencent Cloud Lighthouse

> **In the Domus Aurea repo** both games are deployed together with the top-level `deploy/setup.sh` (see the root README): one HTTPS address, one login, a portal at `/`, and this game under `/guandan/`. This document describes the standalone Guandan setup.

Status: ready to deploy. The scripts have been tested end to end on macOS in
testing mode; the systemd, nginx and certificate steps have not yet been run on
a real Ubuntu server, so the first install is also their first run.
Related: [DEPLOY.md](DEPLOY.md) (background, capacity measurements, private mode),
`deploy/make_bundle.sh`, `deploy/setup_lighthouse.sh`, `deploy/public_access.sh`.

## 1. Goal

Run the Guandan web app on one cloud server, so that a group of friends can
open `https://<server-ip>` in any browser, enter a shared password, and play.
They can play with each other and against the AI players, watch tables, and
replay and review finished deals. Strangers who find the address get no further
than the password prompt.

### Requirements

| ID | Requirement |
|---|---|
| R1 | Players need only a browser: no app, VPN, or SSH tunnel. |
| R2 | Reachable by the server's public IP; no domain required. |
| R3 | Every request is checked against a shared password before it reaches the game. |
| R4 | All traffic, including the password, is encrypted (HTTPS). |
| R5 | The game server itself is never directly reachable from the network. |
| R6 | Installation must not depend on GitHub or PyPI being reachable from the server. |
| R7 | One command installs or upgrades the server; upgrades keep the data and the password. |
| R8 | Finished deals and reviews survive restarts, and are backed up daily. |
| R9 | Serve 10 tables (up to 30 AI players and about 30 open browser tabs) with headroom. |
| R10 | Operating the server complies with local hosting rules (see §3). |

### Out of scope

Individual user accounts, a trusted (warning-free) certificate without a
domain, more than one server, and serving players without the shared password.

## 2. Architecture

```
 browser ──HTTPS 443──▶ nginx ──HTTP──▶ guandan server ──▶ SQLite
 (any IP)  (80 → 301)   │ TLS (self-signed │ 127.0.0.1:8770   /var/lib/guandan/games.db
                        │   for the IP)    │ 10 tables, AI
                        │ basic auth       │ review worker (separate process)
                        │ 10 req/s per IP  │
```

| Component | Details |
|---|---|
| nginx | The only public listener: TCP 443 (TLS 1.2/1.3) and TCP 80 (redirects to HTTPS). Checks the shared login (HTTP basic auth, SHA-512 crypt hash in `/etc/nginx/guandan.htpasswd`, mode 640 root:www-data). Rate limit 10 req/s per IP, burst 40, then 429. Request body limit 64 KB. Rewrites `Host` to `127.0.0.1:8770` when proxying. Config: `/etc/nginx/sites-available/guandan`; the default site is removed. |
| Certificate | Self-signed RSA-2048 certificate for the public IP (subjectAltName = IP), valid 825 days, at `/etc/nginx/guandan-selfsigned.{crt,key}`. It is regenerated automatically if the public IP changes. With `--domain`, a Let's Encrypt certificate is used instead, renewed automatically by certbot. |
| guandan server | Python 3.12 process, `python -m guandan.server --host 127.0.0.1 --port 8770 --tables 10 --db /var/lib/guandan/games.db`. It refuses to bind wildcard or public addresses and rejects requests with an unexpected `Host` header. Seat actions require the per-seat token issued when sitting down. |
| Service | systemd unit `guandan.service`, user and group `guandan` (system user, no login shell). Restarts on failure. Hardened with `NoNewPrivileges`, `ProtectSystem=strict`, `ProtectHome`, `PrivateTmp`, kernel and cgroup protection, and `RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX`; it can only write to `/var/lib/guandan`. |
| Code | `/opt/guandan/app` (owned by root, read-only to the service); Python environment in `/opt/guandan/venv`. |
| Data | `/var/lib/guandan/games.db` (finished deals, reviews), owned by `guandan`. |
| Backups | `/etc/cron.daily/guandan-backup`: a consistent SQLite `.backup` to `/var/lib/guandan/backups/games-YYYY-MM-DD.db`, keeping 14 days. |
| Login | User `guandan` (changeable); the 20-character random password is stored in `/root/guandan-login.txt` (mode 600). |

Game behaviour relevant to operations: computer moves are made every 0.9 s. A
seat is released after 90 s without contact. An AI takes over a player who
hasn't acted for 5 minutes. A finished deal moves on after 45 s. Restarting the
service ends games in progress; finished deals and reviews are kept.

## 3. Environment

| Item | Value |
|---|---|
| Provider / product | Tencent Cloud Lighthouse (轻量应用服务器) |
| Region | **Hong Kong** (or Singapore). See the compliance note below |
| Image | **Ubuntu Server 24.04 LTS** (system image, not an app template). Python 3.12 is required; 22.04 (Python 3.10) is not supported |
| Size | 2 vCPU, 4 GB RAM, 40 GB+ disk, x86-64, about 5 Mbps or more bandwidth |
| Login | SSH key pair (no password logins) |

**Compliance (R10).** A public website on a mainland-China server must have an
ICP filing (备案), and a filing is tied to a domain, so access by bare IP from a
mainland server can never be compliant. Hong Kong and Singapore regions don't
require a filing. If a mainland server is required instead, either use private
access (SSH tunnel or Tailscale; see DEPLOY.md), or get a domain with an ICP
filing and run `public_access.sh --domain`.

**Capacity (R9).** Load tests (DEPLOY.md) ran 300 tables at 55% of one laptop
core with p95 latency of 14 ms. Estimated limits on this instance size are
about 100 tables (CPU) and about 45 tables (bandwidth, at ~30 kbit/s per open
tab). 10 tables is far below both.

## 4. Network and firewall

Lighthouse console → instance → Firewall (防火墙). The rule set must be exactly:

| Protocol / port | Source | Purpose |
|---|---|---|
| TCP 22 | the administrator's IP only | SSH administration |
| TCP 443 | 0.0.0.0/0 (or friends' IPs) | the game (HTTPS) |
| TCP 80 | 0.0.0.0/0 (or friends' IPs) | redirect to HTTPS |

Every other default rule is removed. **TCP 8770 is never opened.** The setup
script does not change the firewall; it is configured by hand.

## 5. Setup procedure

Placeholders: `<server-ip>` is the instance's public IP, `<key>` is the SSH
private key file, and `<rev>` is the bundle's commit, printed by
`make_bundle.sh`.

| Step | Where | Action |
|---|---|---|
| 1 | Console | Create the Lighthouse instance per §3 and bind the SSH key. Note the public IP. |
| 2 | Console | Configure the firewall per §4. |
| 3 | Mac | Check you can log in: `chmod 600 <key> && ssh -i <key> ubuntu@<server-ip>`. |
| 4 | Mac | Build the offline bundle from a clean, committed checkout: `cd guandan && git status && deploy/make_bundle.sh`. This gives `dist/guandan-<rev>.tar.gz` (~260 MB: code, trained models, Linux x86-64 Python 3.12 wheels for numpy and CPU-only PyTorch). |
| 5 | Mac | Copy it over: `scp -i <key> dist/guandan-<rev>.tar.gz ubuntu@<server-ip>:~`. If `scp` is slow, use a **private** COS bucket with a short-lived presigned URL instead; never a public object. |
| 6 | Server | Install: `tar xzf guandan-<rev>.tar.gz && sudo bash guandan-<rev>/deploy/setup_lighthouse.sh --public`. |
| 7 | Server | Record the printed login (`guandan` + 20-character password). It is also in `sudo cat /root/guandan-login.txt`. |
| 8 | Browser | Open `https://<server-ip>`, accept the one-time certificate warning (Advanced → Proceed), log in, and run the acceptance checks in §6. |
| 9 | Server | Harden SSH: set `PasswordAuthentication no` in `/etc/ssh/sshd_config`, then `sudo systemctl restart ssh`. Keep the current session open and confirm a new key-based login works before closing it. |
| 10 | Friends | Share the URL, the login and the password privately, and mention the one-time certificate warning. |

What the step-6 script does, in order. It stops with `error: …` at the first
failure.

1. Installs `python3-venv`, `python3-pip`, `sqlite3` and `ca-certificates` from the image's apt mirror, and checks Python ≥ 3.11.
2. Copies the code to `/opt/guandan/app`, replacing any previous version.
3. Creates `/opt/guandan/venv` and installs numpy and torch **offline** from the bundle's wheels (it fails if the wheels' Python version doesn't match).
4. Self-check: imports the server, lists the available AI agents (`ppo` must be among them), and confirms the bind address is allowed.
5. Creates the `guandan` user, writes and starts `guandan.service`.
6. Installs the daily backup job.
7. Waits until port 8770 is listening, requires it to be listening **only** on `127.0.0.1:8770`, and checks that `/api/lobby` reports 10 tables.
8. `--public`: installs nginx, openssl and curl. Creates or keeps the shared password and writes the password hash. Gets the public IP from Tencent's metadata service (or `--public-ip`), creates the self-signed certificate, writes and enables the nginx site, and checks the config with `nginx -t`.
9. Verifies that an anonymous request to `https://127.0.0.1/` gets **401** and that `/api/lobby` with the login gets **200**.

Setup options: `--tables N` (default 10), `--port P` (default 8770),
`--password PW` (at least 10 characters), `--login-user NAME`,
`--public-ip IP`, and `--domain D --email E` (Let's Encrypt instead of
self-signed). The alternative source `--repo URL` installs from a git mirror
reachable from the server (e.g. private Gitee/CNB) using Tencent's PyPI mirror.

## 6. Acceptance checks

| # | Check | Expected |
|---|---|---|
| A1 | Setup script output | Ends with "Public access is on: https://<server-ip>"; no `error:` lines |
| A2 | `ss -ltnp \| grep -E ':(80\|443\|8770)\b'` on the server | 8770 only on `127.0.0.1`; 80 and 443 owned by nginx |
| A3 | `curl -sk -o /dev/null -w '%{http_code}\n' https://<server-ip>/` from another machine | `401` |
| A4 | `curl -s -o /dev/null -w '%{http_code}\n' http://<server-ip>/` | `301` (redirect to HTTPS) |
| A5 | `curl -s --max-time 5 http://<server-ip>:8770/` from another machine | connection fails (port closed) |
| A6 | Browser with the login | Lobby (大厅) shows 10 tables (1 号桌 … 10 号桌), all text in Chinese |
| A7 | Sit at a table, add 3 AIs, start | Cards are dealt and the AIs move about once a second |
| A8 | Second browser (another device) | Can watch the table from one seat, seeing only that seat's cards |
| A9 | Finish a deal, open its replay, press "Review with the AI" | Replay steps through the deal; the review appears within about a minute |
| A10 | `sudo systemctl restart guandan`, then reload the lobby | Server comes back; the finished deal is still in "Recent deals" |
| A11 | `sudo /etc/cron.daily/guandan-backup && ls /var/lib/guandan/backups` | Today's `games-YYYY-MM-DD.db` exists |

## 7. Operations

| Task | Procedure |
|---|---|
| Upgrade | Mac: commit, `deploy/make_bundle.sh`, `scp` the new bundle. Server: `tar xzf guandan-<new>.tar.gz && sudo bash guandan-<new>/deploy/setup_lighthouse.sh --public`. The database and password are kept; games in progress end. |
| Change the password | `sudo bash /opt/guandan/app/deploy/public_access.sh --password '<new>'` (everyone has to log in again). Do this whenever the password may have leaked. |
| Change the table count | Rerun the setup with `--public --tables N`. Above about 30, re-measure first with `scripts/loadtest.py` on the server. |
| Add a domain (removes the certificate warning) | Point the domain's A record at the server, then `sudo bash /opt/guandan/app/deploy/public_access.sh --domain <d> --email <e>`. |
| Status and logs | `systemctl status guandan nginx`, `journalctl -u guandan -n 100`, `/var/log/nginx/{access,error}.log` |
| Backups off the server | `scp -i <key> -r ubuntu@<server-ip>:/var/lib/guandan/backups .` (e.g. weekly) |
| Restore | `sudo systemctl stop guandan && sudo cp games-YYYY-MM-DD.db /var/lib/guandan/games.db && sudo chown guandan:guandan /var/lib/guandan/games.db && sudo systemctl start guandan` |
| Turn public access off | `sudo rm /etc/nginx/sites-enabled/guandan && sudo systemctl stop nginx && sudo systemctl disable nginx`, then remove the 80/443 firewall rules. Use the SSH tunnel from DEPLOY.md instead. |
| OS updates | `sudo apt update && sudo apt upgrade` monthly, then reboot if a kernel update needs it. The services start automatically. |

## 8. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Browser cannot connect | Firewall is missing 80/443 (§4); the instance is stopped; on a mainland server, ICP blocking (§3) |
| Login prompt keeps reappearing | Wrong password: `sudo cat /root/guandan-login.txt` |
| 502 Bad Gateway | Game service is down: `systemctl status guandan`, `journalctl -u guandan -n 50`, then `sudo systemctl restart guandan` |
| 429 Too Many Requests | More than 10 req/s from one IP, e.g. many tabs behind one router. Close spare tabs, or raise `rate`/`burst` in `/etc/nginx/sites-available/guandan` and run `sudo systemctl reload nginx` |
| Setup: "Python 3.x found; 3.11+ is needed" | Wrong image: reinstall the instance with Ubuntu 24.04 |
| Setup: "bundle wheels are for Python X" | Rebuild the bundle with `deploy/make_bundle.sh --python <server version>` |
| Setup: "could not find the public IP" | Rerun with `--public --public-ip <server-ip>` |
| Setup: "unexpected listener" | Something else is using port 8770, or it was configured to bind elsewhere; the script stops by design |
| Certificate warning changes or reappears | The public IP changed; rerun the setup (the certificate is regenerated for the new IP) |

## 9. Security model and known limitations

- **The shared password is the only gate.** Anyone who has it can do
  everything a player can: take seats, watch any table, read every saved
  replay, and request reviews. It isn't per-person and can't be revoked for one
  person; rotating it logs everyone out.
- **The self-signed certificate** means browsers can't tell the real server
  from an impostor on a hostile network. It's acceptable for friends; a domain
  with Let's Encrypt removes the limitation.
- **Fair play is on trust.** A seated player's own tab is always shown their own
  seat, but a second browser can watch an opponent's seat. AI-suggestion use is
  recorded per deal and shown in the deal list.
- **Single server, single process.** No redundancy; a restart ends games in
  progress (finished deals are kept).
- **Not yet run on a real server.** The systemd, nginx and certbot steps are
  checked by the script itself at install time (A1–A2 and the 401/200 check),
  but they haven't been tested beforehand on a real Ubuntu machine.
