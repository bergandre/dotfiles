#!/usr/bin/env bash
# AUTHOR AND IMPLEMENTER : CLAUDE
# Idle override: hypridle ignores every app inhibitor, so the only way to keep
# the screen on is to stop hypridle itself. No arg prints state, "toggle" flips it.
set -euo pipefail

if [ "${1:-}" = toggle ]; then
  if systemctl --user is-active -q hypridle; then
    systemctl --user stop hypridle
  else
    systemctl --user start hypridle
  fi
  pkill -RTMIN+10 waybar || true
  exit 0
fi

if systemctl --user is-active -q hypridle; then
  echo '{"text": "󰾪", "tooltip": "Idle: screen off after 5 min", "class": "inactive"}'
else
  echo '{"text": "󰛊", "tooltip": "Idle override: screen stays on", "class": "active"}'
fi
