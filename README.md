# Xanadu

> In Xanadu did Kubla Khan a stately pleasure-dome decree.

One home for two games, served together behind one login:

| | Game | Folder |
|---|---|---|
| **掼蛋** | Guandan, the four-player partnership card game, with AI players trained by self-play (`ppo+` search) | [`games/guandan`](games/guandan) |
| **天下** | 英雄擲天下, a Three Kingdoms / Water Margin / … property-and-siege board game | [`games/boardgames`](games/boardgames) |

After signing in, players land on a portal with two big buttons, 掼蛋 and 天下, and pick a game.

## Layout

```
portal/            the landing page (static HTML)
games/guandan/     Python + Rust; its own README, tests, deploy scripts, docs
games/boardgames/  Node.js + browser JS; its own README, deploy script, WeChat mini game
deploy/            deploys both games together (make_bundle.sh, setup.sh, public_access.sh)
dev/serve.py       runs everything locally on one address
```

The games share nothing but the portal and the deployment. Each keeps its own code, tests and README
and still works on its own (`games/guandan/deploy/setup_lighthouse.sh`, `games/boardgames/deploy/setup_tencent.sh`).
Each game's pages use relative URLs (`api/...`), so they work under any path prefix: `/guandan/` and `/boardgames/`.

## Run locally

```bash
python3.12 -m venv .venv && .venv/bin/pip install -e 'games/guandan[dev]'
(cd games/guandan/rust && ../../../.venv/bin/pip install maturin && ../../../.venv/bin/maturin develop --release)   # optional, enables ppo+
.venv/bin/python dev/serve.py        # http://127.0.0.1:8780/   (needs Node.js 18+ for the board game)
```

## Deploy to a Tencent Cloud Lighthouse server

```bash
deploy/make_bundle.sh                # on your computer, from a committed checkout -> dist/xanadu-<rev>.tar.gz
scp dist/xanadu-<rev>.tar.gz ubuntu@<server-ip>:~
ssh ubuntu@<server-ip> 'tar xzf xanadu-<rev>.tar.gz && sudo bash xanadu-<rev>/deploy/setup.sh'
```

`deploy/setup.sh` installs both games as hardened systemd services that listen on loopback only
(Guandan on 8770, the board game on 8765), copies the portal, and puts nginx in front on 443:
HTTPS, one shared password, rate limiting, and one site (`/` portal, `/guandan/`, `/boardgames/`).
Open TCP 80 and 443 in the Lighthouse firewall; never the game ports. Options: `--tables N`,
`--password`, `--domain/--email` (Let's Encrypt), `--no-public` (services only). Re-running upgrades in place and
keeps the Guandan database and the password. If you used the old separate deployments, setup carries the login
over and retires the old nginx sites (you can then close TCP 8443).

See [`games/guandan/docs/DEPLOY.md`](games/guandan/docs/DEPLOY.md) for capacity numbers and
[`games/guandan/docs/SERVER_SPEC.md`](games/guandan/docs/SERVER_SPEC.md) for the Guandan server in detail
(written for the standalone setup; the combined setup differs only in the nginx site and the login file names:
`/etc/nginx/xanadu.htpasswd`, `/root/xanadu-login.txt`).
