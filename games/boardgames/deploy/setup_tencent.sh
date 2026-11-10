#!/usr/bin/env bash
# Add the board game server to a Tencent Cloud Lighthouse machine that already runs guandan
# behind its HTTPS + shared-password nginx (guandan's setup_lighthouse.sh --public).
#
# What it does:
#   - installs Node.js (18 or later) if needed, and puts the game in /opt/board_games,
#     read-only to the service
#   - runs it as the unprivileged "boardgames" user, bound to 127.0.0.1 only (the server itself
#     refuses any other address)
#   - adds one more nginx HTTPS port (default 8443) that uses guandan's certificate and
#     guandan's shared password file, so the same login protects both games
#   - checks that anonymous requests are refused (401) before it reports success; if they
#     are not, it closes the port again and stops
# It never creates a password of its own: if guandan's login isn't set up, it stops.
# The game port is never opened to the network.
#
# Run it from the unpacked bundle (see deploy/make_bundle.sh):
#   tar xzf board_games-<rev>.tar.gz && sudo bash board_games-<rev>/deploy/setup_tencent.sh
#
# Options:
#   --port P       public HTTPS port for the board games (default 8443)
#   --app-port P   port the game listens on, on 127.0.0.1 only (default 8765)
#   --service-only install and start only the loopback service: no nginx site, no login checks. The
#                  repository-level deploy/setup.sh uses this, and serves both games behind one HTTPS login.
#   --remove       take the board games off this machine again (service, nginx port, files)
set -euo pipefail
trap 'echo "setup failed (line $LINENO)" >&2' ERR

PUBLIC_PORT=8443
APP_PORT=8765
REMOVE=0
SERVICE_ONLY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --port) PUBLIC_PORT="$2"; shift 2 ;;
    --app-port) APP_PORT="$2"; shift 2 ;;
    --service-only) SERVICE_ONLY=1; shift ;;
    --remove) REMOVE=1; shift ;;
    -h|--help) sed -n '2,25p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
die() { echo "error: $*" >&2; exit 1; }
[ "$(id -u)" -eq 0 ] || die "run with sudo"
[[ "$PUBLIC_PORT" =~ ^[0-9]+$ && "$APP_PORT" =~ ^[0-9]+$ ]] || die "ports must be numbers"
for p in 22 80 443; do
  [ "$SERVICE_ONLY" = 1 ] || [ "$PUBLIC_PORT" != "$p" ] || die "--port $p is taken (22 = SSH, 80/443 = guandan); use another port such as 8443"
done
[ "$SERVICE_ONLY" = 1 ] || [ "$PUBLIC_PORT" != "$APP_PORT" ] || die "--port and --app-port must differ"

APP=/opt/board_games
SVC=boardgames
UNIT=/etc/systemd/system/$SVC.service
SITE=/etc/nginx/sites-available/boardgames
ENABLED=/etc/nginx/sites-enabled/boardgames
HTPASSWD=/etc/nginx/guandan.htpasswd     # guandan's shared login; this script only reads it
LOGIN_FILE=/root/guandan-login.txt
GSITE=/etc/nginx/sites-available/guandan

if [ "$REMOVE" = 1 ]; then
  echo "==> removing the board games"
  rm -f "$ENABLED" "$SITE"
  if command -v nginx >/dev/null && nginx -t -q 2>/dev/null; then systemctl reload nginx || true; fi
  systemctl disable --now "$SVC" 2>/dev/null || true
  rm -f "$UNIT"; systemctl daemon-reload
  rm -rf "$APP"
  id "$SVC" >/dev/null 2>&1 && userdel "$SVC" || true
  echo "done. In the Lighthouse console, remove the firewall rule for TCP $PUBLIC_PORT."
  exit 0
fi

SRC=$(cd "$(dirname "$0")/.." && pwd)
[ -f "$SRC/server/server.js" ] && [ -f "$SRC/index.html" ] || die "run this from the unpacked bundle ($SRC has no server/server.js)"

listening() { [ -n "$(ss -ltnH "sport = :$1")" ]; }   # (no pipe into grep -q: it can trip pipefail)
if [ "$SERVICE_ONLY" = 0 ]; then
echo "==> checks (stops here unless guandan's HTTPS login is already in place)"
command -v nginx >/dev/null || die "nginx is not installed; set up guandan with --public first"
[ -s "$HTPASSWD" ] || die "$HTPASSWD is missing or empty. Run guandan's setup_lighthouse.sh --public first; this script reuses its login and never makes a password of its own"
[ -f "$GSITE" ] || die "$GSITE not found; set up guandan with --public first"
CERT=$(sed -n 's/^[[:space:]]*ssl_certificate[[:space:]][[:space:]]*\([^;]*\);.*/\1/p' "$GSITE" | head -1)
KEY=$(sed -n 's/^[[:space:]]*ssl_certificate_key[[:space:]][[:space:]]*\([^;]*\);.*/\1/p' "$GSITE" | head -1)
[ -f "$CERT" ] && [ -f "$KEY" ] || die "could not find guandan's certificate files (read '$CERT' / '$KEY' from $GSITE)"
if listening "$PUBLIC_PORT" && [ ! -f "$SITE" ]; then
  die "TCP $PUBLIC_PORT is already used by another program; choose another with --port"
fi
fi
if listening "$APP_PORT" && ! systemctl is-active -q "$SVC"; then
  die "TCP $APP_PORT is already used by another program; choose another with --app-port"
fi

echo "==> Node.js"
node_major() { command -v node >/dev/null && node -p 'process.versions.node.split(".")[0]' || echo 0; }
if [ "$(node_major)" -lt 18 ]; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq nodejs >/dev/null
fi
[ "$(node_major)" -ge 18 ] || die "Node.js 18 or later is needed (apt installed $(node -v 2>/dev/null || echo none)); install a newer Node.js and run again"
NODE=$(readlink -f "$(command -v node)")
case "$NODE" in   # the sandboxed service cannot read home directories (ProtectHome=yes)
  /home/*|/root/*|/run/user/*) die "node is at $NODE, which the service cannot read; install Node.js system-wide (sudo apt install nodejs) and run again" ;;
esac

echo "==> files"
id "$SVC" >/dev/null 2>&1 || useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin "$SVC"
rm -rf "$APP.new"; mkdir -p "$APP.new"
( cd "$SRC" && cp -r index.html engine.js client.js cards.js themes.js texts.js theme-*-art.js board-*.svg server "$APP.new"/ )
chown -R root:root "$APP.new"
chmod -R go-w "$APP.new"; chmod -R a+rX "$APP.new"
rm -rf "$APP.old"
[ ! -d "$APP" ] || mv "$APP" "$APP.old"
mv "$APP.new" "$APP"; rm -rf "$APP.old"

if [ "$SERVICE_ONLY" = 0 ]; then
echo "==> nginx (the login goes in place before the game is started)"
V6=""
[ -f /proc/net/if_inet6 ] && V6="listen [::]:$PUBLIC_PORT ssl;"
cat > "$SITE" <<EOF
# Board games: HTTPS entry point on port $PUBLIC_PORT, protected by guandan's shared login.
# The game itself only listens on 127.0.0.1:$APP_PORT.
limit_req_zone \$binary_remote_addr zone=boardgames:10m rate=10r/s;

server {
    listen $PUBLIC_PORT ssl;
    $V6
    server_name _;
    server_tokens off;

    ssl_certificate $CERT;
    ssl_certificate_key $KEY;
    ssl_protocols TLSv1.2 TLSv1.3;

    client_max_body_size 64k;
    limit_req zone=boardgames burst=40 nodelay;
    limit_req_status 429;

    auth_basic "Board games";
    auth_basic_user_file $HTPASSWD;

    location / {
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_read_timeout 30s;
    }

    # Live game updates (server-sent events): must not be buffered, and stay open a long time.
    location = /api/events {
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        gzip off;
        proxy_read_timeout 1h;
    }
}
EOF
ln -sf "$SITE" "$ENABLED"
nginx -t -q
systemctl reload nginx

fi

echo "==> service (127.0.0.1:$APP_PORT only)"
cat > "$UNIT" <<EOF
[Unit]
Description=Board games server (127.0.0.1:$APP_PORT)
After=network.target

[Service]
User=$SVC
Group=$SVC
Environment=SANGUO_HOST=127.0.0.1
Environment=SANGUO_PORT=$APP_PORT
# Node's I/O library tries io_uring, which the call filter below blocks; turn it off
Environment=UV_USE_IO_URING=0
ExecStart=$NODE $APP/server/server.js
Restart=on-failure
RestartSec=3
# The game keeps everything in memory, so it needs no writable paths and no privileges.
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
RestrictNamespaces=yes
LockPersonality=yes
CapabilityBoundingSet=
SystemCallFilter=@system-service
# a blocked call returns an error instead of killing Node (newer libuv tries io_uring and falls back)
SystemCallErrorNumber=EPERM
# four tables = up to four game threads in this one process (about 50 MB each)
MemoryMax=700M

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable -q "$SVC"
systemctl restart "$SVC"

echo "==> verify"
OK=""
for _ in $(seq 1 15); do
  if listening "$APP_PORT"; then OK=1; break; fi
  sleep 1
done
fail_closed() {   # close the public port again, then stop
  rm -f "$ENABLED"; nginx -t -q 2>/dev/null && systemctl reload nginx || true
  systemctl stop "$SVC" || true
  die "$1 (the public port has been closed again)"
}
if [ -z "$OK" ]; then
  echo "--- systemctl status $SVC" >&2; systemctl status "$SVC" --no-pager -l 2>&1 | tail -n 15 >&2 || true
  echo "--- journalctl -u $SVC" >&2; journalctl -u "$SVC" -n 25 --no-pager 2>&1 >&2 || true
  fail_closed "the game is not listening on port $APP_PORT (see the log above)"
fi
# The game must listen on loopback only.
while read -r addr; do
  [ "$addr" = "127.0.0.1:$APP_PORT" ] || fail_closed "unexpected listener $addr (expected 127.0.0.1:$APP_PORT)"
done < <(ss -ltnH "sport = :$APP_PORT" | awk '{print $4}')
if [ "$SERVICE_ONLY" = 1 ]; then
  echo "board games service is listening on 127.0.0.1:$APP_PORT"
  exit 0
fi
# Anonymous requests must be refused by the login, not by anything else.
for path in / /engine.js /api/events /api/lobby; do
  HDRS=$(curl -sk --max-time 5 -o /dev/null -D - "https://127.0.0.1:$PUBLIC_PORT$path" || true)
  CODE=$(printf '%s' "$HDRS" | sed -n '1s/.* \([0-9][0-9][0-9]\).*/\1/p')
  [ "$CODE" = 401 ] || fail_closed "expected 401 for an anonymous request to $path, got '${CODE:-no answer}'"
  printf '%s' "$HDRS" | grep -qi '^www-authenticate: *basic' || fail_closed "the 401 for $path did not come from the login"
done
echo "anonymous requests: 401 with a login prompt (blocked)"
LOGIN=$(sed -n 's/^user: //p' "$LOGIN_FILE" 2>/dev/null || true)
PASSWORD=$(sed -n 's/^password: //p' "$LOGIN_FILE" 2>/dev/null || true)
if [ -n "$LOGIN" ] && [ -n "$PASSWORD" ]; then
  CODE=$(printf 'user = "%s:%s"\n' "$LOGIN" "$PASSWORD" | curl -sk -K - --max-time 5 -o /dev/null -w '%{http_code}' "https://127.0.0.1:$PUBLIC_PORT/" || true)
  [ "$CODE" = 200 ] || fail_closed "expected 200 with the shared login, got '$CODE' (journalctl -u $SVC)"
  echo "with the shared login: 200"
else
  echo "note: $LOGIN_FILE not readable, so the signed-in check was skipped (the blocked check above is the important one)"
fi

IP=$(curl -s --max-time 3 http://metadata.tencentyun.com/latest/meta-data/public-ipv4 || true)
[[ "$IP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || IP="<server-ip>"
cat <<EOF

Board games are up: https://$IP:$PUBLIC_PORT
  login: the same shared login as guandan (see $LOGIN_FILE)
  The certificate is guandan's, so each browser shows its "not private" warning once for this
  port too: choose "Advanced" -> "Proceed".

Still to do by hand in the Lighthouse console > Firewall:
  - allow TCP $PUBLIC_PORT (from anywhere, or only from your friends' IP ranges, e.g. 203.0.113.0/24)
  - never open $APP_PORT; keep SSH (22) limited to your own IP
Notes:
  - Anyone with the shared password can sit at any open seat and run the lobby. Share it like a house key.
  - There are 4 tables, so up to 4 games run at once. A player who stands up is replaced by the computer;
    when the last human leaves a table, the game ends and the table opens again.
  - Upgrade: build a new bundle, copy it over, and run this script again.
  - Take it off the machine: sudo bash $SRC/deploy/setup_tencent.sh --remove
  - Logs: journalctl -u $SVC -f      Listener check: ss -ltnp | grep $APP_PORT (must show 127.0.0.1)
EOF
