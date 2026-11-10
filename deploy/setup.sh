#!/usr/bin/env bash
# Install both games on a Tencent Cloud Lighthouse machine (Ubuntu 24.04) behind one HTTPS address
# with one shared login. After signing in, players see the portal and pick Guandan or the board game.
#
#   tar xzf xanadu-<rev>.tar.gz && sudo bash xanadu-<rev>/deploy/setup.sh
#
# What it does, in order:
#   1. games/guandan/deploy/setup_lighthouse.sh    -> Guandan on 127.0.0.1:8770 (service "guandan")
#   2. games/boardgames/deploy/setup_tencent.sh    -> board game on 127.0.0.1:8765 (service "boardgames")
#   3. copies portal/ to /opt/xanadu/portal
#   4. deploy/public_access.sh                     -> nginx on 443: HTTPS, shared login, one site:
#                                                       /            portal
#                                                       /guandan/    Guandan
#                                                       /boardgames/ board game
# Both game servers stay on loopback; nginx is the only public listener.
#
# Options:
#   --tables N          Guandan tables (default 10)
#   --guandan-port P    default 8770          --boardgames-port P   default 8765
#   --no-public         steps 1-3 only (services on loopback; reach them with an SSH tunnel). No login, no portal.
#   --password PW  --login-user NAME  --public-ip IP  --domain D --email E     (passed to public_access.sh)
# Re-running upgrades both games in place; the Guandan database and the shared password are kept.
set -euo pipefail
trap 'echo "setup failed (line $LINENO)" >&2' ERR

TABLES=10
GPORT=8770
BPORT=8765
PUBLIC=1
PUB_ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --tables) TABLES="$2"; shift 2 ;;
    --guandan-port) GPORT="$2"; shift 2 ;;
    --boardgames-port) BPORT="$2"; shift 2 ;;
    --no-public) PUBLIC=0; shift ;;
    --password) PUB_ARGS+=(--password "$2"); shift 2 ;;
    --login-user) PUB_ARGS+=(--user "$2"); shift 2 ;;
    --public-ip) PUB_ARGS+=(--public-ip "$2"); shift 2 ;;
    --domain) PUB_ARGS+=(--domain "$2"); shift 2 ;;
    --email) PUB_ARGS+=(--email "$2"); shift 2 ;;
    -h|--help) sed -n '2,24p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
die() { echo "error: $*" >&2; exit 1; }
[ "$(id -u)" -eq 0 ] || die "run with sudo"
[ "$PUBLIC" = 1 ] || [ ${#PUB_ARGS[@]} -eq 0 ] || die "--password/--login-user/--public-ip/--domain/--email need public access (drop --no-public)"
SRC=$(cd "$(dirname "$0")/.." && pwd)
[ -f "$SRC/games/guandan/guandan/server/server.py" ] && [ -f "$SRC/games/boardgames/server/server.js" ] \
  || die "run this from the unpacked bundle ($SRC does not look like the xanadu tree)"

echo "################ 1/4 Guandan"
bash "$SRC/games/guandan/deploy/setup_lighthouse.sh" --tables "$TABLES" --port "$GPORT"

echo; echo "################ 2/4 board game"
bash "$SRC/games/boardgames/deploy/setup_tencent.sh" --service-only --app-port "$BPORT"

echo; echo "################ 3/4 portal"
PORTAL=/opt/xanadu/portal
rm -rf "$PORTAL.new"; mkdir -p "$PORTAL.new"
cp -r "$SRC/portal/." "$PORTAL.new/"
chown -R root:root "$PORTAL.new"; chmod -R go-w "$PORTAL.new"; chmod -R a+rX "$PORTAL.new"
rm -rf "$PORTAL.old"
[ ! -d "$PORTAL" ] || mv "$PORTAL" "$PORTAL.old"
mv "$PORTAL.new" "$PORTAL"; rm -rf "$PORTAL.old"
echo "portal installed in $PORTAL"

if [ "$PUBLIC" = 1 ]; then
  echo; echo "################ 4/4 HTTPS, login and the combined site"
  bash "$SRC/deploy/public_access.sh" --guandan-port "$GPORT" --boardgames-port "$BPORT" --portal "$PORTAL" ${PUB_ARGS[@]+"${PUB_ARGS[@]}"}
else
  cat <<EOF

Done (no public access). Guandan is on 127.0.0.1:$GPORT and the board game on 127.0.0.1:$BPORT.
Reach them with an SSH tunnel, e.g.  ssh -N -L $GPORT:127.0.0.1:$GPORT -L $BPORT:127.0.0.1:$BPORT <user>@<server-ip>
The portal and the shared login need nginx: re-run without --no-public.
EOF
fi
