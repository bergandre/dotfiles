#!/usr/bin/env bash
# Restores SteamVR 2.15.6 from Steam console depot downloads.
# SteamVR >= 2.16.6 breaks ALVR v20.14.1 (error 303, frozen frame, "Desync detected"),
# see https://github.com/alvr-org/ALVR/issues/3296
#
# If the depots are gone, download them in the Steam console (steam://open/console):
#   download_depot 250820 250823 6872847796886137069
#   download_depot 250820 250824 8448055372836238157
#   download_depot 250820 250827 2190029673101935499
# AUTHOR : CLAUDE


set -euo pipefail

STEAM_DIR="$HOME/.local/share/Steam"
STEAMVR_DIR="$STEAM_DIR/steamapps/common/SteamVR"
DEPOT_DIR="${DEPOT_DIR:-$STEAM_DIR/ubuntu12_32/steamapps/content/app_250820}"
DEPOTS=( 250823 250824 250827 )
ALVR_WRAPPER=$(ls -d "$HOME"/.local/share/ALVR-Launcher/installations/*/alvr_streamer_linux/libexec/alvr/vrcompositor-wrapper 2>/dev/null | sort -V | tail -n 1 || true)

if pgrep -f "SteamVR/bin/linux64/(vrserver|vrmonitor|vrcompositor)" >/dev/null; then
  echo "SteamVR is running, close it first"
  exit 1
fi

for D in "${DEPOTS[@]}"; do
  if [ ! -d "$DEPOT_DIR/depot_$D/" ]; then
    echo "Missing $DEPOT_DIR/depot_$D, download it in the Steam console (see header of $0)"
    exit 1
  fi
done

if [ -z "$ALVR_WRAPPER" ]; then
  echo "ALVR vrcompositor-wrapper not found, install ALVR via the launcher first"
  exit 1
fi

# keep the replaced install instead of deleting it, the user removes it after checking
if [ -e "$STEAMVR_DIR" ]; then
  BACKUP="$STEAMVR_DIR.replaced-$(date +%Y%m%d-%H%M%S)"
  mv "$STEAMVR_DIR" "$BACKUP"
  echo "Old SteamVR moved to $BACKUP"
fi

mkdir -p "$STEAMVR_DIR"
for D in "${DEPOTS[@]}"; do
  cp -a "$DEPOT_DIR/depot_$D/." "$STEAMVR_DIR/"
done

# ALVR swaps the compositor for its wrapper (DRM lease on Wayland), the real binary goes to .real
cd "$STEAMVR_DIR/bin/linux64"
mv vrcompositor vrcompositor.real
ln -s "$ALVR_WRAPPER" vrcompositor

# without CAP_SYS_NICE the compositor can't raise thread priority
sudo setcap CAP_SYS_NICE=eip "$STEAMVR_DIR/bin/linux64/vrcompositor-launcher"

echo "SteamVR 2.15.6 restored, wrapper -> $ALVR_WRAPPER"
getcap "$STEAMVR_DIR/bin/linux64/vrcompositor-launcher"
[ -n "${BACKUP:-}" ] && echo "If VR works, remove the backup: rm -rf '$BACKUP'"
exit 0
