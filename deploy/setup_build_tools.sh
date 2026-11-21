#!/usr/bin/env bash
# Install (or check) everything needed to build the server bundle on this computer (macOS or Linux).
#
#   deploy/setup_build_tools.sh              # install what is missing, asking before anything big
#   deploy/setup_build_tools.sh --yes        # ... without asking
#   deploy/setup_build_tools.sh --check      # only report; change nothing
#   deploy/setup_build_tools.sh --arm        # also add the Linux ARM target (for an ARM server)
#
# It needs: git, Python 3.12 (the server's Python; wheels are built for it), a virtual environment in .venv with maturin and
# ziglang (the Rust cross-compiler), the Rust toolchain with the Linux target, and internet access. Afterwards:
#   deploy/make_bundle.sh && deploy/verify_bundle.sh dist/domus_aurea-<rev>.tar.gz
# Safe to run again. Nothing is installed system-wide except through Homebrew (Python) and rustup (Rust), and only after a question.
set -euo pipefail
cd "$(dirname "$0")/.."

YES=0; CHECK=0; ARM=0
for a in "$@"; do
  case "$a" in
    --yes|-y) YES=1 ;; --check) CHECK=1 ;; --arm) ARM=1 ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "unknown option: $a" >&2; exit 2 ;;
  esac
done
MISSING=0
ok()   { printf '  ok       %s\n' "$*"; }
miss() { printf '  MISSING  %s\n' "$*"; MISSING=$((MISSING + 1)); }
fixed() { printf '  ok       %s\n' "$*"; MISSING=$((MISSING - 1)); }          # a MISSING line that was just put right
ask()  { [ "$CHECK" = 1 ] && return 1; [ "$YES" = 1 ] && return 0; read -r -p "  $1 [y/N] " r; [ "$r" = y ] || [ "$r" = Y ]; }
[ -f "$HOME/.cargo/env" ] && . "$HOME/.cargo/env"

echo "== git"
command -v git >/dev/null && ok "$(git --version)" || miss "git (install the Xcode command line tools: xcode-select --install)"

echo "== Python 3.12"
PY312=$(command -v python3.12 || true)
if [ -z "$PY312" ] && [ -x /opt/homebrew/bin/python3.12 ]; then PY312=/opt/homebrew/bin/python3.12; fi
if [ -z "$PY312" ] && [ -x /usr/local/bin/python3.12 ]; then PY312=/usr/local/bin/python3.12; fi
if [ -z "$PY312" ]; then
  miss "python3.12"
  if command -v brew >/dev/null && ask "Install it with Homebrew (brew install python@3.12)?"; then
    brew install python@3.12
    PY312=$(command -v python3.12 || echo "$(brew --prefix python@3.12)/bin/python3.12")
    [ -x "$PY312" ] && fixed "installed $($PY312 --version)"
  elif ! command -v brew >/dev/null; then
    echo "           install Python 3.12 from https://www.python.org/downloads/ or install Homebrew first (https://brew.sh)"
  fi
else
  ok "$($PY312 --version) at $PY312"
fi

echo "== virtual environment (.venv) with maturin and ziglang"
if [ -n "$PY312" ] && { [ ! -x .venv/bin/python ] || ! .venv/bin/python -c 'import sys; sys.exit(sys.version_info[:2] != (3, 12))' 2>/dev/null; }; then
  miss ".venv (Python 3.12)"
  if ask "Create .venv here?"; then "$PY312" -m venv .venv && .venv/bin/pip install -q -U pip && fixed "created .venv"; fi
fi
if [ -x .venv/bin/python ]; then
  for pkg in maturin ziglang; do
    if .venv/bin/python -c "import importlib.metadata as m; m.version('$pkg')" 2>/dev/null; then
      ok "$pkg $(.venv/bin/python -c "import importlib.metadata as m; print(m.version('$pkg'))")"
    else
      miss "$pkg in .venv"
      if ask "pip install $pkg into .venv?"; then .venv/bin/pip install -q "$pkg" && fixed "installed $pkg"; fi
    fi
  done
fi

echo "== Rust toolchain"
if ! command -v cargo >/dev/null; then
  miss "cargo / rustup"
  if ask "Install Rust with the official rustup installer (https://sh.rustup.rs)?"; then
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain stable
    . "$HOME/.cargo/env"
    command -v cargo >/dev/null && fixed "installed $(cargo --version)"
  fi
fi
if command -v cargo >/dev/null; then
  ok "$(cargo --version)"
  TARGETS=(x86_64-unknown-linux-gnu); [ "$ARM" = 1 ] && TARGETS+=(aarch64-unknown-linux-gnu)
  for t in "${TARGETS[@]}"; do
    if rustup target list --installed 2>/dev/null | grep -qx "$t"; then ok "target $t"
    else
      miss "Rust target $t"
      if ask "rustup target add $t?"; then rustup target add "$t" >/dev/null && fixed "added $t"; fi
    fi
  done
fi

echo "== try a cross-build of the Rust core for the server"
if [ "$MISSING" -le 0 ] || [ "$CHECK" = 0 ]; then
  if command -v cargo >/dev/null && [ -x .venv/bin/maturin ] && rustup target list --installed 2>/dev/null | grep -qx x86_64-unknown-linux-gnu; then
    OUT=$(mktemp -d)
    if (cd games/guandan/rust && PATH="$PWD/../../../.venv/bin:$PATH" ../../../.venv/bin/maturin build --release -q --target x86_64-unknown-linux-gnu --zig \
          --manylinux 2_28 -i python3.12 -o "$OUT" >/dev/null 2>&1) && ls "$OUT"/guandan_core-*manylinux*x86_64.whl >/dev/null 2>&1; then
      ok "built $(basename "$(ls "$OUT"/guandan_core-*.whl | head -1)")"
    else
      miss "the test build of the Rust core failed (run it by hand to see why: cd games/guandan/rust && ../../../.venv/bin/maturin build --release --target x86_64-unknown-linux-gnu --zig --manylinux 2_28 -i python3.12)"
    fi
  else
    echo "  skipped (something above is missing)"
  fi
fi

echo
if [ "$MISSING" -le 0 ]; then
  echo "Ready. Build with:  deploy/make_bundle.sh && deploy/verify_bundle.sh dist/domus_aurea-<rev>.tar.gz"
else
  echo "Not ready yet: see the MISSING lines above$([ "$CHECK" = 1 ] && echo " (run without --check to install them)")." >&2
  exit 1
fi
