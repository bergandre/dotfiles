#!/bin/bash
# newsboat unread items, one at a time, as "Source: title" in a $width-char window
# the source stays put; long titles scroll start -> end (pause at both ends), then the next item comes up
# picked by clock, not a counter: every bar runs its own copy and they stay in sync
# runs twice a second, so the hot path is bash built-ins + one jq

width=65   # chars visible (left side also holds a window title of up to 50)
hold=4     # ticks (0.5s each) to pause at start and end of a scroll
short=16   # ticks to show an item that fits without scrolling
db=~/.local/share/newsboat/cache.db
urls=~/.config/newsboat/urls
cache=$XDG_RUNTIME_DIR/waybar-news.cache
cur=$XDG_RUNTIME_DIR/waybar-news-url
stamp=$XDG_RUNTIME_DIR/waybar-news-reload
us=$'\x1f'   # field separator: titles can contain tabs and pipes

# UTF-8 locale so ${#s} and ${s:i:n} count characters, not bytes
export LC_ALL=C.UTF-8

# newsboat only reloads while the TUI is open, so fetch in the background every 15 min
# (if the TUI is running this fails on its lock, harmless: the TUI reloads itself)
# after the reload, items published over 2 days ago are marked read (also while the TUI
# is open: the reload then fails on its lock, the update still runs)
[ -f "$stamp" ] && last=$(<"$stamp")
if (( EPOCHSECONDS - ${last:-0} > 900 )); then
  echo "$EPOCHSECONDS" > "$stamp"
  stale="update rss_item set unread = 0 where unread = 1 and pubDate < strftime('%s', 'now', '-2 days')"
  # db and sql go in as $1/$2: no quoting gymnastics inside the bash -c string
  setsid -f bash -c 'newsboat -x reload; sqlite3 -cmd ".timeout 2000" "$1" "$2"' _ "$db" "$stale" >/dev/null 2>&1
fi
[ -f "$db" ] || exit 0

# bar prefix from the display name: "YouTube: Kargoz" -> KargozYT, "Wowhead: Forever" -> Wowhead
source_of() {
  case "$1" in
    YouTube:*) src="${1#YouTube: }YT" ;;
    *:*)       src="${1%%:*}" ;;
    *)         src="$1" ;;
  esac
}

# rebuild the item list only when newsboat's db (or the feed names) changed
# cache: line 1 = total ticks, then per item: slot, overflow, source, url, feed name, title
build() {
  local -A name
  local u rest row feed ftitle title url feedname over slot total=0 lines=()
  # feed display names: the "~Name" from the urls file, keyed by feed url
  while read -r u rest; do
    [[ $u != \#* && $rest =~ \"~([^\"]+)\" ]] && name[$u]=${BASH_REMATCH[1]}
  done < "$urls"

  while IFS= read -r row; do
    feed=${row%%"$us"*}; rest=${row#*"$us"}
    ftitle=${rest%%"$us"*}; rest=${rest#*"$us"}
    title=${rest%%"$us"*}; url=${rest#*"$us"}
    feedname=${name[$feed]:-$ftitle}
    source_of "$feedname"
    over=$(( ${#src} + 2 + ${#title} - width ))
    slot=$(( over > 0 ? hold + over + hold : short ))
    (( total += slot ))
    lines+=("$slot$us$over$us$src$us$url$us$feedname$us$title")
  done < <(sqlite3 -separator "$us" "file:$db?mode=ro" \
    "select i.feedurl, f.title, i.title, i.url from rss_item i join rss_feed f on f.rssurl = i.feedurl
     where i.unread = 1 and i.deleted = 0 order by i.pubDate desc")

  # write + rename so the other bar never reads a half-written file
  printf '%s\n' "$total" "${lines[@]}" > "$cache.$$"
  mv -f "$cache.$$" "$cache"
}
[[ ! -f $cache || $db -nt $cache || $urls -nt $cache ]] && build

mapfile -t rows < "$cache"
total=${rows[0]}
n=$(( ${#rows[@]} - 1 ))
(( n == 0 )) && { rm -f "$cur"; exit 0; }

# walk the slots to find the item for "now" (half-second ticks; $EPOCHREALTIME is "sec.usec")
now=${EPOCHREALTIME/[.,]/}
t=$(( now / 500000 % total ))
for (( i = 1; i <= n; i++ )); do
  slot=${rows[i]%%"$us"*}
  (( t < slot )) && break
  (( t -= slot ))
done

IFS=$us read -r slot over src url feedname title <<< "${rows[i]}"
echo "$url" > "$cur"

# scroll offset: 0 during the first hold, then 1 char per tick, capped at the end
pos=0
if (( over > 0 )); then
  pos=$(( t - hold )); (( pos < 0 )) && pos=0; (( pos > over )) && pos=$over
fi

# pango-escaped in jq: a bash esc() via $(...) would fork per call
jq -cn --arg text "󰑫 $src: ${title:pos:width - ${#src} - 2}" --arg feed "$feedname" --arg title "$title" \
  --arg pos "$i / $n unread · click: open + mark read · right: newsboat" \
  'def esc: gsub("&"; "&amp;") | gsub("<"; "&lt;") | gsub(">"; "&gt;");
   {text: ($text | esc), tooltip: "\($feed | esc)\n\($title | esc)\n\n\($pos)"}'
