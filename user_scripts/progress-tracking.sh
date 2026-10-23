#!/usr/bin/env bash

URL=''
CURTIME=0
STEP=5
DELAY=0.02 

while true; do
  curl -s "$URL" \
    -H 'Accept: application/json, text/javascript, */*; q=0.01' \
    -H 'Accept-Language: en-US,en;q=0.9' \
    -H 'Connection: keep-alive' \
    -H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' \
    -H 'Origin: https://.' \
    -H 'Referer: https://' \
    -H 'X-Requested-With: XMLHttpRequest' \
    -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) Chrome/143.0.0.0' \
    --data-raw "ajax=1&curtime=${CURTIME}&play=0" \
    >/dev/null

  CURTIME=$((CURTIME + STEP))
  sleep "$DELAY"
done

