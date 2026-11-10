#!/usr/bin/env bash
# Build an offline install bundle for a server that cannot reach GitHub or PyPI.
#
# The bundle holds the committed code and trained models (git HEAD) plus Python
# wheels for numpy and a CPU-only PyTorch built for the server's platform, so
# the server only needs its own apt mirror. Copy it over and run the setup:
#
#   deploy/make_bundle.sh                       # -> dist/guandan-<rev>.tar.gz (Linux x86-64, Python 3.12)
#   scp dist/guandan-<rev>.tar.gz ubuntu@<server-ip>:~
#   ssh ubuntu@<server-ip> 'tar xzf guandan-<rev>.tar.gz && sudo bash guandan-<rev>/deploy/setup_lighthouse.sh'
#
# Options:
#   --python X.Y        Python version on the server (Ubuntu 24.04 ships 3.12)
#   --platform P        linux-x86_64 (Lighthouse default), linux-aarch64, or native (this machine; for testing)
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
    -h|--help) sed -n '2,17p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

PY="${PYTHON:-.venv/bin/python}"
[ -x "$PY" ] || PY=python3
# Make PY absolute (repo root, after the cd above) so MATURIN stays valid
# after rust_wheel() cds into the temp bundle copy.
case "$PY" in /*) ;; */*) PY="$PWD/$PY" ;; esac
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "warning: uncommitted changes are not included; the bundle is built from HEAD" >&2
fi
REV=$(git rev-parse --short HEAD)
NAME="guandan-$REV"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

echo "==> code and models from HEAD ($REV)"
git archive --format=tar --prefix="$NAME/" HEAD | tar -x -C "$WORK"
WHEELS="$WORK/$NAME/wheels"
mkdir -p "$WHEELS"

export PYTHON="$PY"
bash "$(dirname "$0")/build_wheels.sh" --tree "$WORK/$NAME" --python "$PYVER" --platform "$PLATFORM"

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
  tar xzf $NAME.tar.gz && sudo bash $NAME/deploy/setup_lighthouse.sh
EOF
