#!/bin/bash
# Symlink dotfiles into $HOME on a fresh machine. Safe to re-run.
# Real files/dirs in the way are moved to <name>.bak.<timestamp> first.

# repo = directory of this script, wherever it was cloned
DOTFILES="$(dirname "$(realpath "$0")")"

link() {
  SRC="$DOTFILES/$1"
  DST="$2"
  if [ ! -e "$SRC" ]; then
    echo "skip $DST ($1 missing, gitignored?)"
    return
  fi
  mkdir -p "$(dirname "$DST")"
  if [ -e "$DST" ] && [ ! -L "$DST" ]; then
    mv "$DST" "$DST.bak.$(date +%s)"
    echo "backup $DST"
  fi
  # -n: replace an existing link to a dir instead of creating a link inside it
  ln -sfn "$SRC" "$DST"
  echo "link $DST -> $SRC"
}

## zsh
link zsh/.zshrc "$HOME/.zshrc"
link zsh/.zshenv "$HOME/.zshenv"
link zsh/.zprofile "$HOME/.zprofile"
link zsh/.aliases "$HOME/.aliases"

## git
link git/.gitconfig "$HOME/.gitconfig"
link git/ignore "$HOME/.config/git/ignore"

## ~/.config
for DIR in ghostty hypr lsd mako matugen nvim uwsm waybar; do
  link "$DIR" "$HOME/.config/$DIR"
done

## pipewire
link pipewire/client.conf.d/app-routing.conf "$HOME/.config/pipewire/client.conf.d/app-routing.conf"
link pipewire/pipewire.conf.d/music-sink.conf "$HOME/.config/pipewire/pipewire.conf.d/music-sink.conf"
link pipewire/pipewire-pulse.conf.d/app-routing.conf "$HOME/.config/pipewire/pipewire-pulse.conf.d/app-routing.conf"

## claude
for ITEM in agents commands settings.json skills statusline.sh themes; do
  link "claude/$ITEM" "$HOME/.claude/$ITEM"
done

## user scripts
link user_scripts/backlog-watcher.py "$HOME/.local/bin/backlog-watcher.py"
link user_scripts/random-wallpaper.sh "$HOME/.local/bin/random-wallpaper.sh"

## systemd user units
SYSTEMD_USER="$HOME/.config/systemd/user"
link systemd-services/random-wallpaper.service "$SYSTEMD_USER/random-wallpaper.service"
link systemd-services/random-wallpaper.timer "$SYSTEMD_USER/random-wallpaper.timer"
link systemd-services/random-wallpaper.timer "$SYSTEMD_USER/graphical-session.target.wants/random-wallpaper.timer"
link systemd-services/wayland-wm@hyprland.desktop.service.d/oom.conf "$SYSTEMD_USER/wayland-wm@hyprland.desktop.service.d/oom.conf"
systemctl --user daemon-reload 2>/dev/null

## /etc (needs root): not run here, copy-paste these
echo
echo "# keyd, run as root:"
echo "sudo mkdir -p /etc/keyd"
for CONF in "$DOTFILES"/keyd/*.conf; do
  echo "sudo ln -sfn \"$CONF\" /etc/keyd/$(basename "$CONF")"
done
echo "sudo systemctl enable --now keyd"

echo
echo "# tty1 autologin (replaces sddm), run as root:"
echo "sudo install -Dm644 \"$DOTFILES/etc/systemd/system/getty@tty1.service.d/autologin.conf\" /etc/systemd/system/getty@tty1.service.d/autologin.conf"
echo "sudo systemctl disable sddm"
