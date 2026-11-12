#!/bin/bash
# now playing via playerctl, replaces the built-in mpris module (it segfaults waybar)
# polled every second by waybar: --follow doesn't emit on position changes

# \x1f as separator: tab is IFS whitespace, so an empty artist would shift fields
IFS=$'\x1f' read -r status artist title pos len vol player < <(
  playerctl -i firefox,chromium,brave metadata --format \
    $'{{lc(status)}}\x1f{{artist}}\x1f{{title}}\x1f{{duration(position)}}\x1f{{duration(mpris:length)}}\x1f{{volume}}\x1f{{playerName}}' 2>/dev/null
)
[ -z "$status" ] && exit 0

esc() { local s=${1//&/&amp;}; s=${s//</&lt;}; echo "${s//>/&gt;}"; }

vol=$(awk "BEGIN { printf \"%d\", $vol * 100 + 0.5 }")
time="$pos/$len"

# mini equalizer: random bar heights each tick while playing, flat when paused
bars=(▁ ▂ ▃ ▄ ▅ ▆ ▇)
wave="${bars[RANDOM % 7]}${bars[RANDOM % 7]}${bars[RANDOM % 7]}"

case "$status" in
  playing) text="$wave $(esc "$artist-$title")  $time  󰕾 $vol%" ;;
  paused)  text="<span color='grey'>▁▁▁ $(esc "$artist-$title")  $time  󰕾 $vol%</span>" ;;
  *)       exit 0 ;;
esac

jq -cn --arg text "$text" --arg class "$status" --arg tooltip "$(esc "$artist - $title ($player)")" \
  '{text: $text, class: $class, tooltip: $tooltip}'
