#!/usr/bin/env bash
# AUTHOR AND IMPLEMENTER : CLAUDE
# Short label of the default audio output (hyper + del/home/end/pgup switch it) + its volume.
# Runs forever: reprints on every server/sink change instead of polling.

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
  # first channel's % (left = right in practice)
  vol=$(pactl get-sink-volume @DEFAULT_SINK@ | grep -oE '[0-9]+%' | head -1)
  [ "$(pactl get-sink-mute @DEFAULT_SINK@)" = "Mute: yes" ] && vol=muted
  jq -cn --arg t "$label $vol" --arg d "$desc" '{text: $t, tooltip: $d}'
}

print
# "change on server" fires when the default sink changes, "change on sink #N" on volume/mute
pactl subscribe | grep --line-buffered -E "on (server|sink #)" | while read -r _; do print; done
