#!/usr/bin/env bash
# Put the offline Python wheels (numpy, CPU-only torch, and the Rust core built for the server)
# into an unpacked copy of the guandan tree: <TREE>/wheels/.
#
#   deploy/build_wheels.sh --tree DIR [--python X.Y] [--platform P]
#
# Used by deploy/make_bundle.sh (guandan alone) and by the repository-level deploy/make_bundle.sh.
# Options:
#   --tree DIR          the unpacked guandan directory (has rust/ and deploy/); wheels/ is created inside
#   --python X.Y        Python version on the server (Ubuntu 24.04 ships 3.12)
#   --platform P        linux-x86_64 (Lighthouse default), linux-aarch64, or native (this machine; for testing)
# Environment: PYTHON = the interpreter with pip (and maturin/ziglang for the Rust core).
set -euo pipefail
PYVER=3.12
PLATFORM=linux-x86_64
TREE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --tree) TREE="$2"; shift 2 ;;
    --python) PYVER="$2"; shift 2 ;;
    --platform) PLATFORM="$2"; shift 2 ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
[ -d "$TREE/rust" ] || { echo "--tree must be the unpacked guandan directory (no rust/ in '$TREE')" >&2; exit 2; }
TREE=$(cd "$TREE" && pwd)
HERE=$(cd "$(dirname "$0")/.." && pwd)
PY="${PYTHON:-}"
for cand in "$PY" "$HERE/.venv/bin/python" "$HERE/../../.venv/bin/python"; do
  [ -n "$cand" ] && [ -x "$cand" ] && { PY="$cand"; break; }
done
[ -x "$PY" ] || PY=python3
case "$PY" in /*) ;; */*) PY="$PWD/$PY" ;; esac
WHEELS="$TREE/wheels"
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

# The Rust core (rules engine, fast self-play, and the search behind the "PPO+搜索" AI) is built from
# rust/ for the server's platform. Cross-compiling needs maturin and ziglang in the same Python
# environment (pip install maturin ziglang) and a Rust toolchain with the target installed. If any is
# missing the bundle still works: the server then runs the (slower) Python engine, without ppo+.
echo "==> Rust core wheel for $PLATFORM"
[ -f "$HOME/.cargo/env" ] && . "$HOME/.cargo/env"
MATURIN="$(dirname "$PY")/maturin"; [ -x "$MATURIN" ] || MATURIN=$(command -v maturin || true)
rust_wheel() {
  [ -n "$MATURIN" ] && command -v cargo >/dev/null 2>&1 || return 1
  case "$PLATFORM" in
    linux-x86_64) TRIPLE=x86_64-unknown-linux-gnu ;;
    linux-aarch64) TRIPLE=aarch64-unknown-linux-gnu ;;
    native) (cd "$TREE/rust" && "$MATURIN" build --release -q -i "$PY" -o "$WHEELS"); return ;;
  esac
  rustup target add "$TRIPLE" >/dev/null 2>&1 || return 1
  (cd "$TREE/rust" && PATH="$(dirname "$PY"):$PATH" "$MATURIN" build --release -q --target "$TRIPLE" --zig \
      --manylinux 2_28 -i "python$PYVER" -o "$WHEELS")
}
if rust_wheel >/dev/null 2>&1 && ls "$WHEELS" | grep -q '^guandan_core-'; then
  ls "$WHEELS" | grep '^guandan_core-'
else
  echo "warning: could not build the Rust core; the bundle will run the Python engine (no ppo+ search)" >&2
fi

