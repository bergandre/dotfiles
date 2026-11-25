#!/bin/bash
# media keys with a toast: runs the playerctl command, then shows the result through mako
# media-toast.sh music next | media-toast.sh firefox position 5+
# music = spotify / soundcloud via music-ctl.sh, anything else is a playerctl player name

ctl=~/.config/waybar/scripts/music-ctl.sh
target=$1; shift
if [ "$target" = music ]; then
  player=$($ctl) || exit 1
  run() { $ctl "$@"; }
else
  player=$target
  run() { playerctl -p "$player" "$@"; }
fi
meta() { playerctl -p "$player" metadata --format "$1" 2>/dev/null; }
esc() { local s=${1//&/&amp;}; s=${s//</&lt;}; echo "${s//>/&gt;}"; }

before=$(meta '{{status}}{{mpris:trackid}}{{title}}')
run "$@" || exit 1

# players update mpris a moment after the command: wait (max 1s) for status / track to change
case $1 in
  play-pause|next|previous)
    for _ in {1..10}; do
      [ "$(meta '{{status}}{{mpris:trackid}}{{title}}')" != "$before" ] && break
      sleep 0.1
    done ;;
esac

# \x1f as separator: tab is IFS whitespace, so an empty artist would shift fields
IFS=$'\x1f' read -r status artist title art vol < <(
  meta $'{{status}}\x1f{{artist}}\x1f{{title}}\x1f{{mpris:artUrl}}\x1f{{volume}}'
)

# nerd font glyphs: play, pause, next, previous, volume, rewind, fast-forward
hints=()
case $1 in
  play-pause)
    if [ "$status" = Playing ]; then head=$'\U000f040a  Playing'; else head=$'\U000f03e4  Paused'; fi ;;
  next)     head=$'\U000f04ad  Next' ;;
  previous) head=$'\U000f04ae  Previous' ;;
  volume)
    [ "$target" = music ] && v=$($ctl volume) && vol=$v
    vol=$(awk "BEGIN { printf \"%d\", $vol * 100 + 0.5 }")
    head=$'\U000f057e'"  Volume $vol%"
    # int:value makes mako draw the toast as a progress bar
    hints=(-h "int:value:$vol") ;;
  position)
    case $2 in
      *-) head=$'\U000f045f'"  Back ${2%-}s" ;;
      *)  head=$'\U000f0211'"  Forward ${2%+}s" ;;
    esac ;;
  *) head=$1 ;;
esac

# cover: firefox gives a local file, spotify a url (fetched once, kept in the runtime dir)
case $art in
  file://*) img=${art#file://} ;;
  http*)
    img=$XDG_RUNTIME_DIR/media-art/${art##*/}
    [ -f "$img" ] || { mkdir -p "${img%/*}"; curl -sf --max-time 2 -o "$img" "$art" || img=; } ;;
esac

# x-canonical-private-synchronous: a new toast replaces the previous one instead of stacking
notify-send -a media -h "string:x-canonical-private-synchronous:media-$target" "${hints[@]}" \
  ${img:+-i "$img"} "$head" "$(esc "$title")"$'\n'"$(esc "$artist")"
