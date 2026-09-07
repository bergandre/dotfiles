#!/bin/bash

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title New Ghostty Window
# @raycast.mode silent

# Optional parameters:
# @raycast.icon 👻
# @raycast.packageName Terminal

prev_app=$(osascript -e 'tell application "System Events" to get name of first process whose frontmost is true')
/usr/bin/open -na Ghostty
sleep 0.3
osascript -e "tell application \"$prev_app\" to activate"
