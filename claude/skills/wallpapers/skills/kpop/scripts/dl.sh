#!/bin/bash
# usage: dl.sh <url-list.txt> <outdir> <prefix>
# Saves line N of the list as <outdir>/<prefix><N>.<ext> (N = gallery index, 1-based).
# Skips files that already exist, 8 downloads in parallel, prints "FAIL <n> <url>" for failures.
# kpopping.com pages are behind Cloudflare (curl gets 403), but the image hosts
# legacy.kpopping.com / cdn.kpopping.com serve originals to curl fine.
list=$1; out=$2; pre=$3
[ -f "$list" ] && [ -n "$out" ] && [ -n "$pre" ] || { echo "usage: $0 list outdir prefix" >&2; exit 1; }
mkdir -p "$out"
n=0
while IFS= read -r url || [ -n "$url" ]; do
  n=$((n+1)); [ "$url" = MISSING ] && { echo "FAIL $n MISSING"; continue; }
  ext="${url##*.}"; ext="${ext,,}"
  echo "$n $url $out/$pre$n.$ext"
done < "$list" | xargs -P 8 -L 1 sh -c '[ -s "$2" ] || curl -sfL --retry 3 -A "Mozilla/5.0 (X11; Linux x86_64) Chrome/130 Safari/537.36" -e https://kpopping.com/ -o "$2" "$1" || echo "FAIL $0 $1"'
