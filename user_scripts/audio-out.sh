#!/bin/bash
# Switch the default audio output: audio-out.sh arctis|razer|soundbar|hdmi
SOUNDBAR=1C:86:9A:E2:7C:EB

case "$1" in
	arctis) PATTERN=SteelSeries_Arctis ;;
	razer) PATTERN=Razer_Leviathan ;;
	soundbar)
		PATTERN=bluez_output.${SOUNDBAR//:/_}
		bluetoothctl info "$SOUNDBAR" | grep -q 'BREDR.Connected: yes' || bluetoothctl connect "$SOUNDBAR" >/dev/null
		;;
	hdmi) PATTERN=pci-0000_01_00.1.hdmi ;;
	*) echo "usage: $0 arctis|razer|soundbar|hdmi" >&2; exit 1 ;;
esac

# a bluetooth sink appears a few seconds after connect, so poll for it
for _ in $(seq 20); do
	SINK=$(pactl list short sinks | awk -v p="$PATTERN" '$2 ~ p { print $2; exit }')
	[ -n "$SINK" ] && break
	sleep 0.5
done

if [ -z "$SINK" ]; then
	notify-send -t 2000 "Audio" "$1: output not found"
	exit 1
fi

pactl set-default-sink "$SINK"

# the soundbar also holds an LE link that goes stale and stalls audio every minute;
# dropping it makes the soundbar reopen a fresh one
if [ "$1" = soundbar ]; then
	busctl call org.bluez "/org/bluez/hci0/dev_${SOUNDBAR//:/_}" org.bluez.Bearer.LE1 Disconnect 2>/dev/null
fi
notify-send -t 1500 "Audio" "→ $1"
