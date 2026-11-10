#!/usr/bin/env bash
# Build one offline install bundle for both games: dist/xanadu-<rev>.tar.gz
#
# It holds the committed code (git HEAD) of the whole repository, the trained Guandan models,
# and Python wheels (numpy, CPU-only PyTorch, the Rust core) for the server's platform, so the
# server only needs its own apt mirror.
#
#   deploy/make_bundle.sh                       # Linux x86-64, Python 3.12 (Ubuntu 24.04)
#   scp dist/xanadu-<rev>.tar.gz ubuntu@<server-ip>:~
#   ssh ubuntu@<server-ip> 'tar xzf xanadu-<rev>.tar.gz && sudo bash xanadu-<rev>/deploy/setup.sh'
#
# Options (passed through to games/guandan/deploy/build_wheels.sh):
#   --python X.Y        Python version on the server
#   --platform P        linux-x86_64 (default), linux-aarch64, or native (this machine; for testing)
#   --out DIR           output directory (default dist/)
set -euo pipefail
cd "$(dirname "$0")/.."

PYVER=3.12
PLATFORM=linux-x86_64
OUT=dist
while [ $# -gt 0 ]; do
  case "$1" in
    --python) PYVER="$2"; shift 2 ;;
    --platform) PLATFORM="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "warning: uncommitted changes are not included; the bundle is built from HEAD" >&2
fi
PY="${PYTHON:-.venv/bin/python}"
[ -x "$PY" ] || PY=python3
case "$PY" in /*) ;; */*) PY="$PWD/$PY" ;; esac
REV=$(git rev-parse --short HEAD)
NAME="xanadu-$REV"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

echo "==> code and models from HEAD ($REV)"
# Only what the server needs: no WeChat mini game, no tests, no training scripts or run logs.
git archive --format=tar --prefix="$NAME/" HEAD | tar -x -C "$WORK"
rm -rf "$WORK/$NAME/games/boardgames/wechat" "$WORK/$NAME/games/boardgames/tools"

export PYTHON="$PY"
bash games/guandan/deploy/build_wheels.sh --tree "$WORK/$NAME/games/guandan" --python "$PYVER" --platform "$PLATFORM"

mkdir -p "$OUT"
tar -czf "$OUT/$NAME.tar.gz" -C "$WORK" "$NAME"
SIZE=$(du -h "$OUT/$NAME.tar.gz" | cut -f1)
SUM=$( (shasum -a 256 "$OUT/$NAME.tar.gz" 2>/dev/null || sha256sum "$OUT/$NAME.tar.gz") | cut -d' ' -f1)
cat <<EOF

Bundle: $OUT/$NAME.tar.gz ($SIZE)
sha256: $SUM

Install on the server:
  scp $OUT/$NAME.tar.gz ubuntu@<server-ip>:~
  ssh ubuntu@<server-ip>
  tar xzf $NAME.tar.gz && sudo bash $NAME/deploy/setup.sh
EOF
