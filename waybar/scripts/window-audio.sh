#!/usr/bin/env bash
# AUTHOR AND IMPLEMENTER : CLAUDE
# Prints a speaker icon when the focused window is playing audio, nothing otherwise.
set -euo pipefail

win=$(hyprctl activewindow -j | jq -r '.pid // empty')
[ -z "$win" ] && exit 0

# Streams often come from a child process (browser/electron audio service),
# so walk each stream's parent chain looking for the window's pid.
for pid in $(pactl -f json list sink-inputs | jq -r '.[] | select(.corked == false) | .properties["application.process.id"] // empty'); do
  while [ "$pid" -gt 1 ] 2>/dev/null; do
    if [ "$pid" = "$win" ]; then
      echo "󰕾"
      exit 0
    fi
    pid=$(awk '{print $4}' "/proc/$pid/stat" 2>/dev/null || echo 0)
  done
done
