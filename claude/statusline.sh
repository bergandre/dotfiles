#!/bin/sh
# pane note (PANE_NOTE from `note` in zsh/.functions), drawn as the same pill as the starship prompt
[ -n "$PANE_NOTE" ] || exit 0
printf '\033[38;5;20m\356\202\266\033[48;5;20;38;5;22m 󰐃 %s \033[0m\033[38;5;20m\356\202\264\033[0m' "$PANE_NOTE"
