DOTFILES="${DOTFILES:-$HOME/repositories/dotfiles}"
export PATH="$HOME/.local/bin:$HOME/.pyenv/bin:$PATH"

[[ -f "$DOTFILES/zsh/.work_variables" ]] && source "$DOTFILES/zsh/.work_variables"
[[ -f "$DOTFILES/zsh/.zshrc_arch" ]] && source "$DOTFILES/zsh/.zshrc_arch"
[[ -f "$DOTFILES/zsh/.zshrc_work" ]] && source "$DOTFILES/zsh/.zshrc_work"

### Zinit
ZINIT_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/zinit/zinit.git"
[[ ! -d $ZINIT_HOME ]] && git clone https://github.com/zdharma-continuum/zinit.git "$ZINIT_HOME"
source "$ZINIT_HOME/zinit.zsh"
compdef() { zicompdef "$@" } # queue completions until compinit runs (see last plugin)

zinit ice depth=1; zinit light romkatv/powerlevel10k
zinit light zdharma-continuum/zinit-annex-bin-gem-node # needed for node'' below
zinit snippet OMZL::history.zsh # not turbo: history has to be set before the first prompt

### Lists — add stuff here
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
  as'null' id-as'angular-cli' node'ng <- !@angular/cli -> ng' atload'source <(ng completion script)' \
    zdharma-continuum/null \
  atload'!_zsh_autosuggest_start' \
    zsh-users/zsh-autosuggestions \
  atinit'ZINIT[COMPINIT_OPTS]=-C; zicompinit; zicdreplay' \
    zdharma-continuum/fast-syntax-highlighting # must stay last: runs compinit

### Settings
setopt correct
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

source "$DOTFILES/zsh/.aliases"
source "$DOTFILES/zsh/.functions"

### MANAGED BY RANCHER DESKTOP START (DO NOT EDIT)
export PATH="/Users/taavaanj/.rd/bin:$PATH"
### MANAGED BY RANCHER DESKTOP END (DO NOT EDIT)
