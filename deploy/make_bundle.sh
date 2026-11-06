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

echo "==> wheels for $PLATFORM, Python $PYVER"
case "$PLATFORM" in
  linux-x86_64) TAGS=(manylinux_2_28_x86_64 manylinux_2_17_x86_64 manylinux2014_x86_64) ;;
  linux-aarch64) TAGS=(manylinux_2_28_aarch64 manylinux_2_17_aarch64 manylinux2014_aarch64) ;;
  native) TAGS=() ;;
  *) echo "unknown platform: $PLATFORM" >&2; exit 2 ;;
esac
if [ "$PLATFORM" = native ]; then
  PYVER=$("$PY" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
  "$PY" -m pip download -q --dest "$WHEELS" "numpy>=1.26" "torch>=2.2"
else
  PLAT_ARGS=()
  for t in "${TAGS[@]}"; do PLAT_ARGS+=(--platform "$t"); done
  COMMON=(--dest "$WHEELS" --only-binary=:all: --python-version "$PYVER" --implementation cp "${PLAT_ARGS[@]}")
  # CPU-only torch (~200 MB) from PyTorch's own index; PyPI's Linux torch pulls ~2 GB of CUDA libraries.
  "$PY" -m pip download -q "${COMMON[@]}" --index-url https://download.pytorch.org/whl/cpu "torch>=2.2" \
    || "$PY" -m pip download -q "${COMMON[@]}" --index-url https://download.pytorch.org/whl/cpu \
         --extra-index-url https://pypi.org/simple "torch>=2.2"
  "$PY" -m pip download -q "${COMMON[@]}" "numpy>=1.26"
fi
echo "$PYVER $PLATFORM" > "$WHEELS/TARGET"
ls "$WHEELS" | grep -q '^torch-' || { echo "no torch wheel was downloaded" >&2; exit 1; }

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
