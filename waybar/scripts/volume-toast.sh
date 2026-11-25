#!/bin/bash
# keyboard volume keys with a toast: changes the default sink, then shows its level through mako
# volume-toast.sh 1%+ | volume-toast.sh 1%-   (capped at 100%)

wpctl set-volume -l 1.0 @DEFAULT_AUDIO_SINK@ "$1" || exit 1

# "Volume: 0.74" or "Volume: 0.74 [MUTED]"
read -r _ vol muted < <(wpctl get-volume @DEFAULT_AUDIO_SINK@)
vol=$(awk "BEGIN { printf \"%d\", $vol * 100 + 0.5 }")
# nerd font glyphs: volume, muted
if [ -n "$muted" ]; then head=$'\U000f075f'"  Muted $vol%"; else head=$'\U000f057e'"  Volume $vol%"; fi

# node.description = the output's readable name; int:value draws the toast as a progress bar
# x-canonical-private-synchronous: a new toast replaces the previous one instead of stacking
notify-send -a media -h string:x-canonical-private-synchronous:volume -h "int:value:$vol" "$head" \
  "$(wpctl inspect @DEFAULT_AUDIO_SINK@ | sed -n 's/.*node\.description = "\(.*\)"/\1/p')"
