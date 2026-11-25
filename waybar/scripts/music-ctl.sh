#!/bin/bash
# picks the music player (spotify or soundcloud): the one playing, else the last one that played
# no args: print the player; with args: run playerctl on it (music-ctl.sh next)

state=$XDG_RUNTIME_DIR/music-player
last=$(cat "$state" 2>/dev/null)

# both playing: stay on the last one
player=$(playerctl -a -p spotify,soundcloud_desktop status --format '{{status}} {{playerName}}' 2>/dev/null |
  awk -v last="$last" '
    $1 == "Playing" { if ($2 == last) keep = 1; else if (!p) p = $2 }
    $2 == last { alive = 1 }
    !any { any = $2 }
    END { print keep ? last : p ? p : alive ? last : any }')
[ -z "$player" ] && exit 1
[ "$player" != "$last" ] && echo "$player" > "$state"

[ $# -eq 0 ] && { echo "$player"; exit 0; }
# soundcloud ignores mpris volume: use its pipewire stream instead (gone while paused)
if [ "$player" = soundcloud_desktop ] && [ "$1" = volume ]; then
  # pw-cli instead of pw-dump: ~6x faster, and this runs on every waybar tick
  id=$(pw-cli ls Node 2>/dev/null | awk '$1 == "id" { id = $2 + 0 } /node.name = "alsa_playback.soundcloud-desktop"/ { print id; exit }')
  [ -z "$id" ] && exit 1
  if [ -n "$2" ]; then wpctl set-volume -l 1 "$id" "$2"; else wpctl get-volume "$id" | awk '{ print $2 }'; fi
  exit
fi

playerctl -p "$player" "$@"
