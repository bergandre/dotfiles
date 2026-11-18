#!/bin/bash
# nvidia gpu stats: core load, vram used/total, core temp (polled by waybar)

IFS=', ' read -r util used total temp < <(
  nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu \
    --format=csv,noheader,nounits 2>/dev/null
)
[ -z "$util" ] && exit 0

# MiB -> GiB with one decimal
mem=$(awk "BEGIN { printf \"%.1f/%.0fG\", $used / 1024, $total / 1024 }")
temp=${temp%.*}

class=normal
[ "$temp" -ge 80 ] && class=hot

jq -cn --arg text "󰢮 $util%  $mem  $temp°" --arg class "$class" \
  --arg tooltip "GPU load $util%"$'\n'"VRAM $used / $total MiB"$'\n'"Core $temp°C" \
  '{text: $text, class: $class, tooltip: $tooltip}'
