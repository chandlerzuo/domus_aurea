#!/usr/bin/env bash
# Build the install bundle for the Tencent Cloud server: dist/board_games-<rev>.tar.gz.
# It holds only what the online game needs (no tools, no WeChat files, no git history).
# Run it on your computer from a clean, committed checkout; the bundle is built from the last commit.
#   deploy/make_bundle.sh
#   scp dist/board_games-<rev>.tar.gz ubuntu@<server-ip>:~
#   (on the server)  tar xzf board_games-<rev>.tar.gz && sudo bash board_games-<rev>/deploy/setup_tencent.sh
set -euo pipefail
cd "$(dirname "$0")/.."
die() { echo "error: $*" >&2; exit 1; }
git rev-parse --git-dir >/dev/null 2>&1 || die "run this inside the git checkout"
[ -z "$(git status --porcelain)" ] || die "commit your changes first (the bundle is built from the last commit)"
REV=$(git rev-parse --short HEAD)
NAME=board_games-$REV
rm -rf "dist/$NAME" "dist/$NAME.tar.gz"
mkdir -p "dist/$NAME"
git archive HEAD -- index.html engine.js client.js cards.js themes.js texts.js \
  'theme-*-art.js' 'board-*.svg' server deploy | tar -x -C "dist/$NAME"
tar -czf "dist/$NAME.tar.gz" -C dist "$NAME"
rm -rf "dist/$NAME"
echo "wrote dist/$NAME.tar.gz ($(du -h "dist/$NAME.tar.gz" | cut -f1))"
