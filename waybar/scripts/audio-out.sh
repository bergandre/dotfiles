#!/usr/bin/env bash
# AUTHOR AND IMPLEMENTER : CLAUDE
# Short label of the default audio output (hyper + del/home/end/pgup switch it).
# Runs forever: reprints on every server change instead of polling.

print() {
  sink=$(pactl get-default-sink)
  case "$sink" in
    *Arctis*) label="󰋋 Arctis" ;;
    *Razer*) label="󰓃 Razer" ;;
    bluez_output*) label="󰂰 Soundbar" ;;
    *hdmi*) label="󰍹 HDMI" ;;
    *) label="󰕾 ?" ;;
  esac
  desc=$(pactl -f json list sinks | jq -r --arg s "$sink" '.[] | select(.name == $s) | .description')
  jq -cn --arg t "$label" --arg d "$desc" '{text: $t, tooltip: $d}'
}

print
# "change on server" fires when the default sink changes
pactl subscribe | grep --line-buffered "on server" | while read -r _; do print; done
