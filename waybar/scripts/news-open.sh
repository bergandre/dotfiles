#!/bin/bash
# click on custom/news: open the shown item and mark it read

db=~/.local/share/newsboat/cache.db
url=$(cat "$XDG_RUNTIME_DIR/waybar-news-url" 2>/dev/null) || exit 0

setsid -f ~/.config/newsboat/open.sh "$url" >/dev/null 2>&1

# written even while the TUI is open: .timeout waits out its write lock instead of failing
# (an open TUI keeps showing the item as unread until it reloads or restarts)
sqlite3 -cmd ".timeout 2000" "$db" "update rss_item set unread=0 where url='${url//\'/\'\'}'"
# show the next item right away instead of waiting for the tick
pkill -RTMIN+9 waybar
