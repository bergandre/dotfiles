#!/bin/bash
# Author : me

ROOT_WP_DIR="$HOME/repositories/wallpapers"
ULTRAWIDE_DIR="$ROOT_WP_DIR/ultrawide/3440x1440"
PORTRAIT_DIR="$ROOT_WP_DIR/portrait/2560x1440"
TELEVISION_DIR="$ROOT_WP_DIR/3840x2160"

PORTRAIT_MONITOR=( "DP-1")
ULTRAWIDE_MONITORS=( "DP-2" "DP-3" )
## Y2K vibes
TELEVISION_MONITOR=("HDMI-A-1")

PORTRAIT_WP=$(find "$PORTRAIT_DIR" -type f ! -ipath '*/archive/*' | shuf -n 1)
TELEVISION_WP=$(find "$TELEVISION_DIR" -type f ! -ipath '*/archive/*' | shuf -n 1)

mapfile -d '' FILES < <(find "$ULTRAWIDE_DIR" -type f ! -ipath '*/archive/*' ! -ipath '*.DS_Store' \( \
  -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.webp' \
\) -print0)

if [ "${#FILES[@]}" -eq 0 ]; then
  echo "No wallpapers found in $ULTRAWIDE_DIR"
  exit 1
fi

# loop monitors and assign random wallpaper per monitor
for MON in "${ULTRAWIDE_MONITORS[@]}"; 
do
	echo "$MON" 
      	WP="${FILES[RANDOM % ${#FILES[@]}]}"
  hyprctl hyprpaper preload "$WP"
  echo "$WP"
  hyprctl hyprpaper wallpaper "$MON,$WP"
done


hyprctl hyprpaper preload "$PORTRAIT_WP"
hyprctl hyprpaper preload "$TELEVISION_WP"
hyprctl hyprpaper wallpaper "$PORTRAIT_MONITOR, $PORTRAIT_WP"
hyprctl hyprpaper wallpaper "$TELEVISION_MONITOR, $TELEVISION_WP"
