#!/usr/bin/env bash
# AUTHOR AND IMPLEMENTER : CLAUDE
# Waybar countdown to the nearest upcoming event from events.local.
set -euo pipefail

events=~/.config/waybar/events.local
now=$(date +%s)
upcoming=()

while read -r day time label; do
  [[ -z "$day" || "$day" == \#* ]] && continue
  ts=$(date -d "$day $time" +%s)
  (( ts > now )) && upcoming+=("$ts $label")
done < "$events"

if (( ${#upcoming[@]} == 0 )); then
  echo '{"text": "", "class": "empty"}'
  exit 0
fi

fmt() {
  local s=$(( $1 - now ))
  local d=$(( s / 86400 )) h=$(( s % 86400 / 3600 )) m=$(( s % 3600 / 60 ))
  if (( d > 0 )); then echo "${d}d ${h}h"
  elif (( h > 0 )); then echo "${h}h ${m}m"
  else echo "${m}m"
  fi
}

# Epoch timestamps sort numerically, so the nearest event ends up first.
mapfile -t upcoming < <(printf '%s\n' "${upcoming[@]}" | sort -n)

read -r ts _ <<<"${upcoming[0]}"
# Under 24h away gets its own class so style.css can highlight it.
if (( ts - now < 86400 )); then class=soon; else class=later; fi

text=""
tooltip=""
for e in "${upcoming[@]}"; do
  read -r t l <<<"$e"
  text+="$l $(fmt "$t") · "
  tooltip+="$(date -d "@$t" '+%a %d.%m %H:%M')  $l  ($(fmt "$t"))"$'\n'
done

jq -cn --arg text "󰃰 ${text% · }" --arg tooltip "${tooltip%$'\n'}" --arg class "$class" \
  '{text: $text, tooltip: $tooltip, class: $class}'
