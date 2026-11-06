#!/usr/bin/env bash
# One-step setup of the Guandan server on Tencent Cloud Lighthouse (Ubuntu 24.04).
#
# From an offline bundle (recommended in mainland China, where GitHub and PyPI
# are often unreachable; build it with deploy/make_bundle.sh):
#   tar xzf guandan-<rev>.tar.gz && sudo bash guandan-<rev>/deploy/setup_lighthouse.sh
#
# From a git mirror the server can reach (e.g. a private Gitee or Tencent CNB repo):
#   sudo bash setup_lighthouse.sh --repo https://gitee.com/<you>/guandan.git
#
# Options:
#   --tables N          number of tables (default 10)
#   --port P            port (default 8770)
#   --host IP           bind address: 127.0.0.1 (default; reach it with an SSH tunnel),
#                       "tailscale" (this machine's Tailscale IP), or another private IP.
#                       Public and wildcard addresses are refused: the game has no login.
#   --repo URL          install from git instead of the bundle this script sits in
#   --branch B          git branch (default main)
#   --pip-index URL     PyPI mirror for --repo installs (default: Tencent Cloud's mirror)
#   --torch-index URL   CPU-only PyTorch index for --repo installs (default: download.pytorch.org)
#   --prefix DIR        install under DIR, without root (testing)
#   --no-systemd        don't install a service; start the server in the background (testing)
#
# Re-running upgrades the code in place and keeps the database.
#
# Layout: /opt/guandan/app (code, read-only to the service), /opt/guandan/venv,
# /var/lib/guandan (database and daily backups, owned by the "guandan" user).
set -euo pipefail
trap 'echo "setup failed (line $LINENO)" >&2' ERR

TABLES=10
PORT=8770
HOST=127.0.0.1
REPO=""
BRANCH=main
PIP_INDEX=https://mirrors.cloud.tencent.com/pypi/simple
TORCH_INDEX=https://download.pytorch.org/whl/cpu
PREFIX=""
SYSTEMD=1
while [ $# -gt 0 ]; do
  case "$1" in
    --tables) TABLES="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --host) HOST="$2"; shift 2 ;;
    --repo) REPO="$2"; shift 2 ;;
    --branch) BRANCH="$2"; shift 2 ;;
    --pip-index) PIP_INDEX="$2"; shift 2 ;;
    --torch-index) TORCH_INDEX="$2"; shift 2 ;;
    --prefix) PREFIX="$2"; shift 2 ;;
    --no-systemd) SYSTEMD=0; shift ;;
    -h|--help) sed -n '2,28p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

step() { echo; echo "==> $*"; }
die() { echo "error: $*" >&2; exit 1; }

ROOT="${PREFIX%/}"
BASE="$ROOT/opt/guandan"
APP="$BASE/app"
VENV="$BASE/venv"
DATA="$ROOT/var/lib/guandan"
SVC_USER=guandan
if [ -z "$PREFIX" ]; then
  [ "$(id -u)" -eq 0 ] || die "run with sudo"
else
  SYSTEMD=0
fi
SRC=""
if [ -z "$REPO" ]; then
  SRC=$(cd "$(dirname "$0")/.." && pwd)
  [ -f "$SRC/guandan/server/server.py" ] || die "run this from an extracted bundle, or pass --repo URL"
fi

step "1/7 system packages"
if [ -z "$PREFIX" ] && command -v apt-get >/dev/null; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq python3-venv python3-pip sqlite3 ca-certificates ${REPO:+git} >/dev/null
fi
PYV=$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))' \
  || die "Python $PYV found; 3.11+ is needed (use the Ubuntu 24.04 image)"
echo "python $PYV"

step "2/7 code"
mkdir -p "$BASE" "$DATA"
if [ -n "$REPO" ]; then
  rm -rf "$APP.new"
  git clone -q --depth 1 --branch "$BRANCH" "$REPO" "$APP.new"
  SRC="$APP.new"
elif [ "$SRC" != "$APP" ]; then
  rm -rf "$APP.new"
  mkdir -p "$APP.new"
  (cd "$SRC" && tar --exclude=./.venv --exclude=./wheels --exclude=./data --exclude=./dist -cf - .) | (cd "$APP.new" && tar -xf -)
fi
if [ -d "$APP.new" ]; then
  rm -rf "$APP.old"
  [ -d "$APP" ] && mv "$APP" "$APP.old"
  mv "$APP.new" "$APP"
  rm -rf "$APP.old"
fi
[ -f "$APP/runs/ppo/model.pt" ] || echo "warning: no trained PPO model in the code; AI players fall back to the heuristic"
echo "installed $(cd "$APP" && (git rev-parse --short HEAD 2>/dev/null || basename "$SRC")) into $APP"

step "3/7 python packages"
[ -x "$VENV/bin/python" ] || python3 -m venv "$VENV"
if [ -z "$REPO" ] && [ -d "$SRC/wheels" ]; then
  read -r WPY WPLAT < "$SRC/wheels/TARGET"
  [ "$WPY" = "$PYV" ] || die "bundle wheels are for Python $WPY but this machine has $PYV; rebuild with: deploy/make_bundle.sh --python $PYV"
  echo "offline wheels ($WPLAT, Python $WPY)"
  "$VENV/bin/pip" install -q --no-index --find-links "$SRC/wheels" numpy torch
else
  "$VENV/bin/pip" install -q --index-url "$PIP_INDEX" "numpy>=1.26"
  "$VENV/bin/pip" install -q --index-url "$TORCH_INDEX" "torch>=2.2" \
    || { echo "CPU torch index unreachable; falling back to $PIP_INDEX (large download)"; \
         "$VENV/bin/pip" install -q --index-url "$PIP_INDEX" "torch>=2.2"; }
fi

step "4/7 self-check"
if [ "$HOST" = tailscale ]; then
  command -v tailscale >/dev/null || die "--host tailscale: tailscale is not installed"
  HOST=$(tailscale ip -4 | head -n1)
  [ -n "$HOST" ] || die "tailscale has no IPv4 address (is it logged in? run: tailscale up)"
fi
(cd "$APP" && "$VENV/bin/python" - "$HOST" <<'EOF'
import sys
from guandan.server.server import check_bind
from guandan.server.tables import agent_kinds
check_bind(sys.argv[1])  # exits with an explanation for wildcard/public addresses
print("agents:", ", ".join(agent_kinds()))
EOF
)

step "5/7 service"
ARGS=(--host "$HOST" --port "$PORT" --tables "$TABLES" --db "$DATA/games.db")
if [ "$SYSTEMD" = 1 ]; then
  id "$SVC_USER" >/dev/null 2>&1 || useradd --system --home-dir "$DATA" --shell /usr/sbin/nologin "$SVC_USER"
  chown -R root:root "$BASE"
  chown -R "$SVC_USER:$SVC_USER" "$DATA"
  AFTER="network-online.target"
  [ "$HOST" != 127.0.0.1 ] && AFTER="$AFTER tailscaled.service"
  cat > /etc/systemd/system/guandan.service <<EOF
[Unit]
Description=Guandan game server
After=$AFTER
Wants=network-online.target

[Service]
User=$SVC_USER
Group=$SVC_USER
WorkingDirectory=$APP
ExecStart=$VENV/bin/python -m guandan.server ${ARGS[*]}
Restart=on-failure
RestartSec=3
Environment=PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
ReadWritePaths=$DATA
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable -q guandan
  systemctl restart guandan
  echo "systemd service guandan (re)started"
else
  if [ -f "$DATA/server.pid" ]; then kill "$(cat "$DATA/server.pid")" 2>/dev/null || true; sleep 1; fi
  (cd "$APP" && exec nohup "$VENV/bin/python" -m guandan.server "${ARGS[@]}" < /dev/null > "$DATA/server.log" 2>&1) &
  echo $! > "$DATA/server.pid"
  echo "started in the background (pid $(cat "$DATA/server.pid"), log $DATA/server.log)"
fi

step "6/7 daily backups"
if [ "$SYSTEMD" = 1 ]; then
  cat > /etc/cron.daily/guandan-backup <<EOF
#!/bin/sh
# Keep 14 days of consistent copies of the replay database.
set -e
[ -f $DATA/games.db ] || exit 0
mkdir -p $DATA/backups
sqlite3 $DATA/games.db ".backup '$DATA/backups/games-\$(date +%F).db'"
chown -R $SVC_USER:$SVC_USER $DATA/backups
find $DATA/backups -name 'games-*.db' -mtime +14 -delete
EOF
  chmod 755 /etc/cron.daily/guandan-backup
  echo "/etc/cron.daily/guandan-backup -> $DATA/backups (14 days)"
else
  echo "skipped (testing mode)"
fi

step "7/7 verify"
OK=""
for _ in $(seq 1 30); do
  if command -v ss >/dev/null; then
    LISTEN=$(ss -ltnH "sport = :$PORT" 2>/dev/null | awk '{print $4}' || true)
  else
    LISTEN=$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | awk 'NR>1 {print $9}' || true)
  fi
  [ -n "$LISTEN" ] && { OK=1; break; }
  sleep 1
done
[ -n "$OK" ] || die "server is not listening on port $PORT (logs: journalctl -u guandan, or $DATA/server.log)"
echo "listening on: $LISTEN"
for addr in $LISTEN; do
  case "$addr" in
    "$HOST:$PORT") ;;
    *) die "unexpected listener $addr (expected $HOST:$PORT); stopping"; ;;
  esac
done
"$VENV/bin/python" - "$HOST" "$PORT" "$TABLES" <<'EOF'
import json, sys, urllib.request
host, port, tables = sys.argv[1], sys.argv[2], int(sys.argv[3])
with urllib.request.urlopen(f"http://{host}:{port}/api/lobby", timeout=10) as r:
    lobby = json.load(r)
assert len(lobby["tables"]) == tables, lobby
print(f"lobby OK: {tables} tables, agents {', '.join(lobby['agents'])}")
EOF

cat <<EOF

Done. Guandan is running on http://$HOST:$PORT (only reachable from this machine
or your private network).

Connect from your computer:
EOF
if [ "$HOST" = 127.0.0.1 ]; then
  cat <<EOF
  ssh -N -L $PORT:127.0.0.1:$PORT <user>@<server-ip>
  then open http://127.0.0.1:$PORT
EOF
else
  echo "  open http://$HOST:$PORT from a device on the same Tailscale/WireGuard network"
fi
cat <<EOF

Still to do by hand (the script does not change these):
  - Lighthouse console > Firewall: allow only SSH (22) from your own IP. Remove the
    default HTTP (80) / HTTPS (443) rules and never add $PORT.
  - SSH: log in with keys and set "PasswordAuthentication no" in /etc/ssh/sshd_config.
  - Copy $DATA/backups off the machine now and then.

Upgrade: build a new bundle, copy it over, and run this script again (the database is kept).
EOF
