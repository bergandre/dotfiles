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

# marquee: long "artist-title" scrolls through a fixed-width window, 2 chars per second
# (UTF-8 locale so ${s:i:n} slices characters, not bytes)
export LC_ALL=C.UTF-8
width=18
name="$artist-$title"
if [ ${#name} -gt $width ]; then
  loop="$name   ·   "
  i=$(( $(date +%s%N) / 500000000 % ${#loop} ))
  name="$loop$loop"
  name=${name:i:width}
fi

vol=$(awk "BEGIN { printf \"%d\", $vol * 100 + 0.5 }")
time="$pos/$len"

# mini equalizer: random bar heights each tick while playing, flat when paused
bars=(▁ ▂ ▃ ▄ ▅ ▆ ▇)
wave="${bars[RANDOM % 7]}${bars[RANDOM % 7]}${bars[RANDOM % 7]}"

case "$status" in
  playing) text="$wave $(esc "$name")  $time  󰕾 $vol%" ;;
  paused)  text="<span color='grey'>▁▁▁ $(esc "$name")  $time  󰕾 $vol%</span>" ;;
  *)       exit 0 ;;
esac

jq -cn --arg text "$text" --arg class "$status" --arg tooltip "$(esc "$artist - $title ($player)")" \
  '{text: $text, class: $class, tooltip: $tooltip}'
