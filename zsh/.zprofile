
[[ -f "$HOME/.zprofile.local" ]] && source "$HOME/.zprofile.local"
# TODO: MOVE STUFF TO .zprofile.local Kiro CLI pre block. Keep at the top of this file.
[[ -f "${HOME}/Library/Application Support/kiro-cli/shell/zprofile.pre.zsh" ]] && builtin source "${HOME}/Library/Application Support/kiro-cli/shell/zprofile.pre.zsh"

### JUST SOME OBSIDIAN STUFF
export OBSIDIAN="$HOME/Documents/obsidian/"
export KEYBINDS="$HOME/Documents/obsidian/setup/hotkeys"
export PROGRAMMING_KB="$OBSIDIAN/programming"

[ "$(tty)" = "/dev/tty1" ] && exec uwsm start default

# Kiro CLI post block. Keep at the bottom of this file.
[[ -f "${HOME}/Library/Application Support/kiro-cli/shell/zprofile.post.zsh" ]] && builtin source "${HOME}/Library/Application Support/kiro-cli/shell/zprofile.post.zsh"
