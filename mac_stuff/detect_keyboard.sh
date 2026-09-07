#!/bin/bash
# Detect keyboard and load appropriate skhd config

DOTFILES_DIR="$HOME/repositories/dotfiles/mac_stuff"
SKHD_CONFIG="$HOME/.skhdrc"

# Check if GMMK 3 Pro is connected (office keyboard)
if system_profiler SPUSBDataType 2>/dev/null | grep -q "GMMK3 75% ANSI"; then
    PROFILE="office"
    SOURCE="$DOTFILES_DIR/.skhdrc_office"
else
    PROFILE="home"
    SOURCE="$DOTFILES_DIR/.skhdrc"
fi

# Only update if config changed
CURRENT=""
if [ -L "$SKHD_CONFIG" ]; then
    CURRENT=$(readlink "$SKHD_CONFIG")
fi

if [ "$CURRENT" != "$SOURCE" ]; then
    echo "Switching to $PROFILE keyboard profile..."
    ln -sf "$SOURCE" "$SKHD_CONFIG"
    skhd --reload 2>/dev/null || true
    echo "Done. Using $PROFILE config."
else
    echo "Already using $PROFILE config."
fi
