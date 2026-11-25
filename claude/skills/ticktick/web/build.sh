#!/usr/bin/env bash
# Build ticktick.zip for upload to claude.ai (Settings > Capabilities > Skills).
# Copies the current map from the vault so the web skill matches it.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
map="${MAP:-$HOME/Documents/obsidian/glava7/_claude/ticktick/map.md}"

cp "$map" "$here/ticktick/map.md"
rm -f "$here/ticktick.zip"
# zip from the parent dir so the archive contains the ticktick/ folder itself
(cd "$here" && zip -qr ticktick.zip ticktick)
echo "$here/ticktick.zip"
