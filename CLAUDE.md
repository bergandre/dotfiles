# CLAUDE.md — dotfiles

Personal dotfiles for Arch Linux (Hyprland/Wayland) and macOS (skhd + yabai).
Content is mostly shell scripts and config files — no build, no tests.

## Workflow rules

- **Agree on approach first.** Before editing or creating anything, propose what
  you plan to do and why, and wait for confirmation. No unrequested changes.
- For non-trivial plans or design decisions, use the `grilling` skill to
  stress-test the idea before implementing (the user may also trigger it
  manually via `/grill-me`).
- ask before deleting files not managed by version control
## Repo layout

- `zsh/` — zsh config: `.zshrc`, `.zshenv`, `.zprofile`, `.aliases`,
  `.functions`, `.p10k.zsh` (powerlevel10k).
- `hypr/` — Hyprland configs for the Arch machine (`hyprland.conf`,
  `hypridle.conf`, `hyprlock.conf`, `hyprback.conf`).
- `nvim/` — Neovim config (lazy.nvim, `init.lua`).
- `mac_stuff/` — macOS hotkeys/tiling: skhd configs and `.yabairc`;
  `switchstuff.sh` swaps home/office skhd profiles by renaming files.
- `browser-app-shortcuts/` — script launching chromium instances as app windows
  with separate profiles.
- `claude/` — Claude Code global config mirrored into the repo.

## Conventions

- **Consistency over preference:** when editing a file, match its existing
  style — comment density, naming, indentation, quoting. Don't reformat or
  "clean up" surrounding code.
- Shell scripts use `#!/bin/bash`, are short and imperative; keep new ones in
  the same spirit.
- Arch package management is `pacman`/`yay`; Hyprland variables use the
  `$name = value` style already present in `hyprland.conf`.
- Configs reference absolute paths (`/home/supernova/...`, `$HOME/...`) — keep
  whichever form the surrounding file already uses.
- Machine- and work-specific files are gitignored (see `.gitignore`, e.g.
  `zsh/.work*`). Before adding a new file, check it doesn't belong in that
  category, and never commit secrets or work-related config.
