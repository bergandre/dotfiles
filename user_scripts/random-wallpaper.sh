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
## terminal colors come from the first connected monitor in this list
COLOR_PRIORITY=( "DP-3" "DP-2" "HDMI-A-1" "DP-1" )
declare -A MON_WP

# on login hyprpaper may not be up yet, wait up to 10s for its socket
HYPRPAPER_SOCK="$XDG_RUNTIME_DIR/hypr/$HYPRLAND_INSTANCE_SIGNATURE/.hyprpaper.sock"
for i in {1..20}; do
  [ -S "$HYPRPAPER_SOCK" ] && break
  sleep 0.5
done

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
  echo "$WP"
  hyprctl hyprpaper wallpaper "$MON,$WP"
  MON_WP[$MON]="$WP"
done


hyprctl hyprpaper wallpaper "$PORTRAIT_MONITOR, $PORTRAIT_WP"
hyprctl hyprpaper wallpaper "$TELEVISION_MONITOR, $TELEVISION_WP"
MON_WP[$PORTRAIT_MONITOR]="$PORTRAIT_WP"
MON_WP[$TELEVISION_MONITOR]="$TELEVISION_WP"

ACTIVE_MONITORS=$(hyprctl monitors -j | jq -r '.[].name')
for MON in "${COLOR_PRIORITY[@]}";
do
  if grep -qx "$MON" <<< "$ACTIVE_MONITORS"; then
    # grayscale wallpapers have no source color, matugen would fall back to google blue
    SATURATION=$(magick "${MON_WP[$MON]}" -colorspace HSL -channel G -separate +channel -format '%[fx:mean]' info:)
    SCHEME="scheme-tonal-spot"
    if awk "BEGIN { exit !($SATURATION < 0.08) }"; then
      SCHEME="scheme-monochrome"
    fi
    matugen image "${MON_WP[$MON]}" -m dark --prefer saturation -t "$SCHEME"
    pkill -SIGUSR2 ghostty
    pkill -SIGUSR1 -x nvim
    break
  fi
done
