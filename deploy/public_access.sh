#!/usr/bin/env bash
# Put both games on the public internet behind HTTPS and one shared password.
#
# nginx becomes the only public listener (443, with 80 redirecting to HTTPS). It checks a shared
# login (HTTP basic auth) and rate-limits each IP, then serves one site:
#     /             the portal (choose a game)
#     /guandan/     Guandan        -> 127.0.0.1:<guandan port>
#     /boardgames/  the board game -> 127.0.0.1:<boardgames port>
# Both game servers stay bound to 127.0.0.1. Without a domain the certificate is self-signed for
# the public IP: browsers show a one-time warning, but traffic (including the password) is
# encrypted. With --domain it uses a Let's Encrypt certificate instead.
#
# Normally run by deploy/setup.sh; it can also be run by itself, e.g. to rotate the password:
#   sudo bash deploy/public_access.sh --password 'new-password'
#   sudo bash deploy/public_access.sh --domain play.example.com --email you@example.com
#
# Options:
#   --guandan-port P     Guandan on 127.0.0.1 (default 8770)
#   --boardgames-port P  board game on 127.0.0.1 (default 8765)
#   --portal DIR         where the portal's index.html is (default /opt/xanadu/portal)
#   --user NAME          login name (default: keep the existing one, else "xanadu")
#   --password PW        shared password (default: keep the existing one, or generate a random one)
#   --public-ip IP       the server's public IP (default: ask the Tencent Cloud metadata service)
#   --domain D           use a Let's Encrypt certificate for D (D must already point at this server)
#   --email E            contact email for Let's Encrypt (required with --domain)
#
# In mainland China a public website needs an ICP filing (备案), even when reached by IP; a Hong
# Kong or Singapore server avoids this.
set -euo pipefail
trap 'echo "public access setup failed (line $LINENO)" >&2' ERR

GPORT=8770
BPORT=8765
PORTAL=/opt/xanadu/portal
LOGIN=""
PASSWORD=""
PUBLIC_IP=""
DOMAIN=""
EMAIL=""
while [ $# -gt 0 ]; do
  case "$1" in
    --guandan-port) GPORT="$2"; shift 2 ;;
    --boardgames-port) BPORT="$2"; shift 2 ;;
    --portal) PORTAL="$2"; shift 2 ;;
    --user) LOGIN="$2"; shift 2 ;;
    --password) PASSWORD="$2"; shift 2 ;;
    --public-ip) PUBLIC_IP="$2"; shift 2 ;;
    --domain) DOMAIN="$2"; shift 2 ;;
    --email) EMAIL="$2"; shift 2 ;;
    -h|--help) sed -n '2,28p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
die() { echo "error: $*" >&2; exit 1; }
[ "$(id -u)" -eq 0 ] || die "run with sudo"
[ -z "$LOGIN" ] || [[ "$LOGIN" =~ ^[A-Za-z0-9_.-]{1,32}$ ]] || die "--user: letters, digits, _ . - only"
[ -z "$DOMAIN" ] || [ -n "$EMAIL" ] || die "--domain needs --email (Let's Encrypt contact)"
[ -f "$PORTAL/index.html" ] || die "no portal at $PORTAL/index.html (run deploy/setup.sh)"

HTPASSWD=/etc/nginx/xanadu.htpasswd
LOGIN_FILE=/root/xanadu-login.txt
CERT=/etc/nginx/xanadu-selfsigned.crt
KEY=/etc/nginx/xanadu-selfsigned.key
SITE=/etc/nginx/sites-available/xanadu
# Earlier layouts (guandan alone, board game on its own port): carry the login and certificate over, then retire them.
OLD_LOGIN_FILE=/root/guandan-login.txt
OLD_CERT=/etc/nginx/guandan-selfsigned.crt
OLD_KEY=/etc/nginx/guandan-selfsigned.key

echo "==> packages"
export DEBIAN_FRONTEND=noninteractive
command -v nginx >/dev/null || apt-get update -qq
apt-get install -y -qq nginx openssl curl ${DOMAIN:+certbot} >/dev/null

echo "==> shared login"
SRC_LOGIN_FILE=""
[ -f "$LOGIN_FILE" ] && SRC_LOGIN_FILE=$LOGIN_FILE || { [ -f "$OLD_LOGIN_FILE" ] && SRC_LOGIN_FILE=$OLD_LOGIN_FILE; } || true
if [ -z "$LOGIN" ]; then
  LOGIN=$([ -n "$SRC_LOGIN_FILE" ] && sed -n 's/^user: //p' "$SRC_LOGIN_FILE" || true)
  LOGIN=${LOGIN:-xanadu}
fi
if [ -n "$PASSWORD" ]; then
  [ ${#PASSWORD} -ge 10 ] || die "--password: use at least 10 characters"
elif [ -n "$SRC_LOGIN_FILE" ] && grep -q "^user: $LOGIN$" "$SRC_LOGIN_FILE"; then
  PASSWORD=$(sed -n 's/^password: //p' "$SRC_LOGIN_FILE")   # keep the existing password on re-runs
else
  PASSWORD=$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | cut -c1-20)
fi
umask 077
printf 'user: %s\npassword: %s\n' "$LOGIN" "$PASSWORD" > "$LOGIN_FILE"
printf '%s:%s\n' "$LOGIN" "$(printf '%s\n' "$PASSWORD" | openssl passwd -6 -stdin)" > "$HTPASSWD"  # stdin: keep it out of ps
umask 022
chown root:www-data "$HTPASSWD"
chmod 640 "$HTPASSWD"

echo "==> certificate"
if [ -n "$DOMAIN" ]; then
  NAME="$DOMAIN"
  CERT=/etc/letsencrypt/live/$DOMAIN/fullchain.pem
  KEY=/etc/letsencrypt/live/$DOMAIN/privkey.pem
  if [ ! -f "$CERT" ]; then
    # Standalone mode needs port 80 for a moment; the hooks are saved for automatic renewals too.
    certbot certonly --standalone --non-interactive --agree-tos -m "$EMAIL" -d "$DOMAIN" \
      --pre-hook "systemctl stop nginx" --post-hook "systemctl start nginx"
  fi
else
  if [ -z "$PUBLIC_IP" ]; then
    PUBLIC_IP=$(curl -s --max-time 3 http://metadata.tencentyun.com/latest/meta-data/public-ipv4 || true)
  fi
  [[ "$PUBLIC_IP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "could not find the public IP; pass --public-ip <ip>"
  NAME="$PUBLIC_IP"
  if [ ! -f "$CERT" ] && [ -f "$OLD_CERT" ] && [ -f "$OLD_KEY" ]; then cp "$OLD_CERT" "$CERT"; cp "$OLD_KEY" "$KEY"; chmod 600 "$KEY"; fi
  if [ ! -f "$CERT" ] || ! openssl x509 -in "$CERT" -noout -ext subjectAltName 2>/dev/null | grep -q "IP Address:$PUBLIC_IP"; then
    openssl req -x509 -newkey rsa:2048 -sha256 -days 825 -nodes -keyout "$KEY" -out "$CERT" \
      -subj "/CN=$PUBLIC_IP" -addext "subjectAltName=IP:$PUBLIC_IP" 2>/dev/null
    chmod 600 "$KEY"
  fi
fi

echo "==> nginx"
V6_80="" V6_443=""
if [ -f /proc/net/if_inet6 ]; then   # skip IPv6 listeners on kernels booted without IPv6
  V6_80="listen [::]:80 default_server;" V6_443="listen [::]:443 ssl default_server;"
fi
HSTS=""
[ -n "$DOMAIN" ] && HSTS='add_header Strict-Transport-Security "max-age=31536000" always;'
cat > "$SITE" <<EOF
# Xanadu: one public HTTPS entry point for both games. The game servers only listen on 127.0.0.1.
limit_req_zone \$binary_remote_addr zone=xanadu:10m rate=10r/s;

server {
    listen 80 default_server;
    $V6_80
    server_name _;
    server_tokens off;
    location / { return 301 https://\$host\$request_uri; }
}

server {
    listen 443 ssl default_server;
    $V6_443
    server_name $NAME;
    server_tokens off;

    ssl_certificate $CERT;
    ssl_certificate_key $KEY;
    ssl_protocols TLSv1.2 TLSv1.3;
    $HSTS

    client_max_body_size 64k;
    limit_req zone=xanadu burst=40 nodelay;
    limit_req_status 429;

    # One login protects everything below, the portal included.
    auth_basic "Xanadu";
    auth_basic_user_file $HTPASSWD;

    # Portal: the page with the two entry buttons.
    root $PORTAL;
    location = / { try_files /index.html =404; }
    location = /index.html { try_files /index.html =404; }

    # Guandan. The trailing slash on proxy_pass strips the /guandan/ prefix; the game only accepts its loopback Host.
    location = /guandan { return 301 /guandan/; }
    location /guandan/ {
        proxy_pass http://127.0.0.1:$GPORT/;
        proxy_set_header Host 127.0.0.1:$GPORT;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_read_timeout 30s;
    }

    # Board game.
    location = /boardgames { return 301 /boardgames/; }
    location /boardgames/ {
        proxy_pass http://127.0.0.1:$BPORT/;
        proxy_set_header Host 127.0.0.1:$BPORT;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_read_timeout 30s;
    }
    # Live board-game updates (server-sent events): must not be buffered, and stay open a long time.
    location = /boardgames/api/events {
        proxy_pass http://127.0.0.1:$BPORT/api/events;
        proxy_set_header Host 127.0.0.1:$BPORT;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        gzip off;
        proxy_read_timeout 1h;
    }

    location / { return 404; }
}
EOF
rm -f /etc/nginx/sites-enabled/default
# retire the earlier sites (they would fight over port 443 or leave an extra open port)
for old in guandan boardgames; do rm -f "/etc/nginx/sites-enabled/$old" "/etc/nginx/sites-available/$old"; done
ln -sf "$SITE" /etc/nginx/sites-enabled/xanadu
nginx -t -q
systemctl enable -q nginx
systemctl restart nginx

echo "==> verify"
sleep 1
for path in / /guandan/ /guandan/api/lobby /boardgames/ /boardgames/api/events; do
  HDRS=$(curl -sk --max-time 5 -o /dev/null -D - "https://127.0.0.1$path" || true)
  CODE=$(printf '%s' "$HDRS" | sed -n '1s/.* \([0-9][0-9][0-9]\).*/\1/p')
  [ "$CODE" = 401 ] || die "expected 401 without the password for $path, got '${CODE:-no answer}'"
done
authed() { printf 'user = "%s:%s"\n' "$LOGIN" "$PASSWORD" | curl -sk -K - --max-time 5 "$@"; }
for path in / /guandan/ /guandan/api/lobby /boardgames/ /boardgames/board-sanguo.svg; do
  CODE=$(authed -o /dev/null -w '%{http_code}' "https://127.0.0.1$path" || true)
  [ "$CODE" = 200 ] || die "expected 200 with the password for $path, got '$CODE' (is the game service running? journalctl -u guandan / -u boardgames)"
done
PAGE=$(authed "https://127.0.0.1/" || true)
case "$PAGE" in *boardgames/*) ;; *) die "the portal page is not what was expected" ;; esac
echo "anonymous requests: 401 (blocked); with the shared login: portal, Guandan and the board game all answer 200"

URL="https://$NAME"
cat <<EOF

Xanadu is up: $URL
  login:    $LOGIN
  password: $PASSWORD     (saved in $LOGIN_FILE, readable by root only)
After signing in, players see the portal and pick 掼蛋 or 天下 (the board game).
EOF
if [ -z "$DOMAIN" ]; then
  cat <<EOF
  The certificate is self-signed, so each browser shows a "not private" warning once:
  choose "Advanced" -> "Proceed". To avoid it, point a domain at this server and run:
    sudo bash $(cd "$(dirname "$0")" && pwd)/public_access.sh --domain <domain> --email <you@example.com>
EOF
fi
cat <<EOF

Still to do by hand in the Lighthouse console > Firewall:
  - allow TCP 80 and 443 (from anywhere, or only from your friends' IPs if you know them)
  - the board game no longer needs its own port: remove any old rule for TCP 8443
  - keep SSH (22) limited to your own IP, and never open $GPORT or $BPORT
Share the address and the login only with people you want at the tables.
Change the password any time: sudo bash $(cd "$(dirname "$0")" && pwd)/public_access.sh --password '<new one>'
EOF
