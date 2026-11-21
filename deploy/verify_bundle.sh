#!/usr/bin/env bash
# Check a finished bundle before copying it to the server (works on macOS and Linux):
#   deploy/verify_bundle.sh dist/domus_aurea-<rev>.tar.gz
# It fails (exit 1) if the Rust core for the server is missing or too old, a wheel is for the wrong platform, or a model file is missing.
# It prints SHA-256 checksums of the model files: they come straight from git, so a rebuild at the same commit must print the same ones.
set -euo pipefail
B="${1:?usage: deploy/verify_bundle.sh <bundle.tar.gz>}"
[ -f "$B" ] || { echo "no such file: $B" >&2; exit 1; }
W=$(mktemp -d); trap 'rm -rf "$W"' EXIT
NAME=$(tar tzf "$B" | head -1 | cut -d/ -f1)
echo "bundle $B ($NAME)"
LIST=$(tar tzf "$B")
need() { printf '%s\n' "$LIST" | grep -q "$1" && echo "  ok   $2" || { echo "  MISSING  $2" >&2; FAIL=1; }; }
FAIL=0
need "games/guandan/wheels/TARGET" "wheel target file"
need "games/guandan/wheels/torch-" "PyTorch wheel"
need "games/guandan/wheels/numpy-" "NumPy wheel"
need "games/guandan/runs/ppo/model.pt" "policy model"
need "games/guandan/runs/ppo/seq_guesser.pt" "sequence guesser"
need "games/boardgames/server/server.js" "board game server"
need "portal/index.html" "portal"
need "deploy/setup.sh" "installer"
if printf '%s\n' "$LIST" | grep -q "rust/target/"; then echo "  WARNING  the Rust build directory is inside the bundle" >&2; fi
CORE=$(printf '%s\n' "$LIST" | grep -E "wheels/guandan_core-.*\.whl$" || true)
if [ -z "$CORE" ]; then
  echo "  MISSING  the Rust core wheel (guandan_core): the server would run the slow Python engine and have no ppo+ search." >&2
  echo "           Install what the build needs (see README: maturin, ziglang, a Rust toolchain with the linux target) and rebuild." >&2
  exit 1
fi
tar xzf "$B" -C "$W" "$CORE" "$NAME/games/guandan/wheels/TARGET" "$NAME/games/guandan/runs/ppo/model.pt" "$NAME/games/guandan/runs/ppo/seq_guesser.pt"
PY=python3; command -v python3 >/dev/null || PY=python
"$PY" - "$W/$CORE" "$W/$NAME/games/guandan/wheels/TARGET" <<'PYEOF' || FAIL=1
import re, sys, zipfile
wheel, target = sys.argv[1], sys.argv[2]
name = wheel.rsplit("/", 1)[-1]
py, plat = open(target).read().split()
ok = True
m = re.match(r"guandan_core-([\d.]+)-cp(\d)(\d+)-", name)
ver = tuple(int(x) for x in m.group(1).split("."))
if ver < (0, 2, 0):
    print(f"  WRONG   core version {m.group(1)} is older than 0.2.0"); ok = False
if f"{m.group(2)}.{m.group(3)}" != py:
    print(f"  WRONG   core built for Python {m.group(2)}.{m.group(3)}, the bundle targets {py}"); ok = False
if plat.startswith("linux-x86_64") and "x86_64" not in name or "linux" not in name and plat.startswith("linux"):
    print(f"  WRONG   core wheel {name} is not for {plat}"); ok = False
so = [n for n in zipfile.ZipFile(wheel).namelist() if n.endswith((".so", ".dylib"))][0]
data = zipfile.ZipFile(wheel).read(so)
for feature in (b"STATE_DIM_V5", b"min_sets", b"ACTION_DIM_V5"):
    if feature not in data:
        print(f"  WRONG   the Rust core lacks {feature.decode()} (an old build)"); ok = False
print(f"  {'ok  ' if ok else 'FAIL'} Rust core {name}: version {m.group(1)}, platform {plat}, newest features {'present' if ok else 'check above'}")
sys.exit(0 if ok else 1)
PYEOF
for f in runs/ppo/model.pt runs/ppo/seq_guesser.pt; do
  printf '  sha256 %-24s %s\n' "$(basename $f)" "$( (shasum -a 256 "$W/$NAME/games/guandan/$f" 2>/dev/null || sha256sum "$W/$NAME/games/guandan/$f") | cut -c1-16)"
done
[ "$FAIL" = 0 ] && echo "bundle OK" || { echo "bundle NOT OK" >&2; exit 1; }
