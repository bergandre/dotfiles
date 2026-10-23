#!/usr/bin/env bash
# AUTHOR AND IMPLEMENTER : CLAUDE
# Click handler for the waybar pomotui module: pause/resume/start in one button.
set -euo pipefail

pomotui=~/.local/bin/pomotui
snapshot=$("$pomotui" --json status)
state=$(jq -r '.snapshot.state' <<<"$snapshot")

case "$state" in
  running) "$pomotui" pause ;;
  paused) "$pomotui" resume ;;
  # A finished round waits for review; that needs the TUI.
  pending) foot ~/.local/bin/pomotui-tui & ;;
  *)
    # next_kind is snake_case (short_break), the CLI wants kebab-case (short-break)
    next=$(jq -r '.snapshot.next_kind' <<<"$snapshot" | tr _ -)
    "$pomotui" start "$next"
    ;;
esac
