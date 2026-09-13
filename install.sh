#!/usr/bin/env bash
# Install canonical skill folders for local Codex/pi. Preserve conflicting entries.
set -euo pipefail
shopt -s nullglob
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.agents/skills"
mkdir -p "$DEST"
conflicts=0
for src in "$REPO"/plugins/*/skills/*; do
  [ -f "$src/SKILL.md" ] || continue
  name="$(basename "$src")"
  dst="$DEST/$name"
  if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$src" ]; then
    printf 'ok: %s\n' "$name"
  elif [ -e "$dst" ] || [ -L "$dst" ]; then
    printf 'conflict preserved: %s\n' "$dst" >&2
    conflicts=1
  else
    ln -s "$src" "$dst"
    printf 'linked: %s\n' "$name"
  fi
done
exit "$conflicts"
