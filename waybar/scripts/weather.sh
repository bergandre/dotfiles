#!/bin/bash
# Riga weather from open-meteo (no api key): condition, feels-like, wind
# every bar runs its own copy, so the api response is cached and fetched at most every 10 min
# notifies when precipitation starts or stops (checked only by the copy that fetched)
# colors: rain blue, wind grey/white/yellow/orange/red by strength (from matugen's colors.css)

url='https://api.open-meteo.com/v1/forecast?latitude=56.95&longitude=24.11&timezone=Europe%2FRiga&wind_speed_unit=ms&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m,wind_gusts_10m,relative_humidity_2m,is_day'
cache=$XDG_RUNTIME_DIR/waybar-weather.json
wet=$XDG_RUNTIME_DIR/waybar-weather.wet
colors=~/.config/waybar/colors.css

# hex of an @define-color from colors.css (pango spans can't use gtk css colors)
color_of() { sed -n "s/^@define-color $1 \(#[0-9a-fA-F]*\);/\1/p" "$colors"; }

# WMO weather codes -> nerd font glyph, papirus icon, short word ($'\U...' so the glyphs survive any editor)
icon_of() {
  case $1 in
    0|1)        word=clear;    icon=$'\Uf0599'; img=weather-clear
                (( day )) || { icon=$'\Uf0594'; img=weather-clear-night; } ;;
    2)          word=cloudy;   icon=$'\Uf0595'; img=weather-few-clouds
                (( day )) || { icon=$'\Uf0f31'; img=weather-few-clouds-night; } ;;
    3)          word=overcast; icon=$'\Uf0590'; img=weather-overcast ;;
    45|48)      word=fog;      icon=$'\Uf0591'; img=weather-mist ;;
    51|53|55)   word=drizzle;  icon=$'\Uf0597'; img=weather-showers-scattered ;;
    56|57|66|67) word=sleet;   icon=$'\Uf067f'; img=weather-snow-rain ;;
    61|63)      word=rain;     icon=$'\Uf0597'; img=weather-showers ;;
    65|80|81|82) word=showers; icon=$'\Uf0596'; img=weather-showers ;;
    71|73|75|77|85|86) word=snow; icon=$'\Uf0598'; img=weather-snow ;;
    95|96|99)   word=storm;    icon=$'\Uf067e'; img=weather-storm ;;
    *)          word="code $1"; icon=$'\Uf0590'; img=weather-overcast ;;
  esac
}

# wind strength by Beaufort scale (m/s, rounded):
# weak 0-3 (calm..light breeze), normal 4-7 (gentle/moderate), mild 8-10 (fresh),
# strong 11-16 (strong breeze..near gale), extreme 17+ (gale and up)
wind_of() {
  if   (( $1 >= 17 )); then level=extreme
  elif (( $1 >= 11 )); then level=strong
  elif (( $1 >= 8 ));  then level=mild
  elif (( $1 >= 4 ));  then level=normal
  else                      level=weak
  fi
}

# WMO codes 51+ are drizzle/rain/sleet/snow/showers/storm, below that is dry
# state file holds "wet|dry word" so "stopped" can name what stopped
notify_change() {
  local now was waswet wasword head
  now=dry; (( code >= 51 )) && now=wet
  [ -f "$wet" ] && read -r waswet wasword < "$wet"
  echo "$now $word" > "$wet"
  # no notification on the very first run (nothing to compare with)
  [[ -z $waswet || $waswet == "$now" ]] && return
  # title color/border per category: mako config (matugen template mako-colors)
  if [ "$now" = wet ]; then
    head="${word^} started"
  else
    head="${wasword:-Rain}"; head="${head^} stopped"
  fi
  notify-send -a weather -c "weather-$now" -i "$img" "$head" \
    "Riga · now $word"$'\n'"${temp}°C · feels ${feels}°"$'\n'"<span color='$windc'>$windicon $wind m/s $level</span> · gusts $gusts"
}

# refetch when stale; on failure keep showing the old data
# flock -n: when several bars tick at once only one fetches, the others use the cache
if [[ ! -f $cache ]] || (( EPOCHSECONDS - $(stat -c %Y "$cache") > 600 )); then
  exec 9> "$cache.lock"
  if flock -n 9; then
    curl -sf --max-time 10 "$url" > "$cache.$$" && mv -f "$cache.$$" "$cache" && fetched=1 || rm -f "$cache.$$"
  fi
fi
[ -f "$cache" ] || exit 0

IFS=$'\t' read -r code day feels temp wind gusts hum < <(
  jq -r '.current | [.weather_code, .is_day, (.apparent_temperature | round),
    .temperature_2m, (.wind_speed_10m | round), (.wind_gusts_10m | round), .relative_humidity_2m] | @tsv' "$cache"
)
[ -z "$code" ] && exit 0

icon_of "$code"
wind_of "$wind"
windicon=$'\Uf059d'
rain=$(color_of rain)
windc=$(color_of "wind_$level")

# condition is blue while it rains/snows, wind takes its strength color
cond="$icon $word"
(( code >= 51 )) && cond="<span color='$rain'>$cond</span>"

[ -n "$fetched" ] && notify_change

jq -cn --arg text "$cond ${feels}° <span color='$windc'>$windicon $wind m/s</span>" \
  --arg tooltip "Riga: $word"$'\n'"${temp}°C, feels like ${feels}°"$'\n'"Wind $wind m/s ($level), gusts $gusts m/s"$'\n'"Humidity $hum%" \
  '{text: $text, tooltip: $tooltip}'
