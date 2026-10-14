DOTFILES="${DOTFILES:-$HOME/repositories/dotfiles}"
export PATH="$HOME/.local/bin:$HOME/.pyenv/bin:$PATH"

[[ -f "$DOTFILES/zsh/.work_variables" ]] && source "$DOTFILES/zsh/.work_variables"
[[ -f "$DOTFILES/zsh/.zshrc_arch" ]] && source "$DOTFILES/zsh/.zshrc_arch"
[[ -f "$DOTFILES/zsh/.zshrc_work" ]] && source "$DOTFILES/zsh/.zshrc_work"

### Zinit
ZINIT_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/zinit/zinit.git"
[[ ! -d $ZINIT_HOME ]] && git clone https://github.com/zdharma-continuum/zinit.git "$ZINIT_HOME"
source "$ZINIT_HOME/zinit.zsh"
compdef() { zicompdef "$@" } #  compdef issue fix

export STARSHIP_CONFIG="$DOTFILES/starship/starship.toml"
zinit ice as'command' from'gh-r' \
  atclone'./starship init zsh > init.zsh; ./starship completions zsh > _starship' \
  atpull'%atclone' src'init.zsh' # not turbo: the prompt has to exist before it's shown
zinit light starship/starship
zinit light zdharma-continuum/zinit-annex-bin-gem-node # needed for node'' below
zinit snippet OMZL::history.zsh # not turbo: history has to be set before the first prompt

libs=(completion key-bindings directories git)
omz_plugins=(git mvn colored-man-pages command-not-found common-aliases)
[[ $OSTYPE == darwin* ]] && omz_plugins+=(brew)
programs=(junegunn/fzf) # binaries from GitHub releases
plugins=(joshskidmore/zsh-fzf-history-search)

# wait lucid = turbo: load right after the prompt shows, quietly
for lib in $libs; do zinit ice wait lucid; zinit snippet "OMZL::$lib.zsh"; done
for plugin in $omz_plugins; do zinit ice wait lucid; zinit snippet "OMZP::$plugin"; done
for program in $programs; do zinit ice wait lucid from'gh-r' as'program'; zinit light $program; done
for plugin in $plugins; do zinit ice wait lucid; zinit light $plugin; done

### Plugins that need extra setup
zinit wait lucid for \
  from'gh-r' as'program' atload'eval "$(zoxide init zsh)"' \
    ajeetdsouza/zoxide \
  from'gh-r' as'program' bpick'tree-sitter-cli-*' \
    tree-sitter/tree-sitter \
  as'null' id-as'angular-cli' node'ng <- !@angular/cli -> ng' atload'source <(ng completion script)' \
    zdharma-continuum/null \
  atload'!_zsh_autosuggest_start' \
    zsh-users/zsh-autosuggestions \
  atinit'ZINIT[COMPINIT_OPTS]=-C; zicompinit; zicdreplay' \
    zdharma-continuum/fast-syntax-highlighting # must stay last: runs compinit

### Settings
setopt correct

source "$DOTFILES/zsh/.aliases"
source "$DOTFILES/zsh/.functions"

### MANAGED BY RANCHER DESKTOP START (DO NOT EDIT) grinning teeth emoji
export PATH="/Users/taavaanj/.rd/bin:$PATH"
### MANAGED BY RANCHER DESKTOP END (DO NOT EDIT)
