DOTFILES="${DOTFILES:-$HOME/repositories/dotfiles}"
[[ -f "$DOTFILES/zsh/.aliases" ]] && source "$DOTFILES/zsh/.aliases"
[[ -f "$DOTFILES/zsh/.work_variables" ]] && source "$DOTFILES/zsh/.work_variables"
[[ -f "$DOTFILES/zsh/.zshrc_arch" ]] && source "$DOTFILES/zsh/.zshrc_arch"
[[ -f "$DOTFILES/zsh/.zshrc_work" ]] && source "$DOTFILES/zsh/.zshrc_work"

export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="powerlevel10k/powerlevel10k"

ENABLE_CORRECTION="true"

plugins=(mvn git zsh-autosuggestions zsh-syntax-highlighting colored-man-pages command-not-found common-aliases brew zsh-fzf-history-search)

source $ZSH/oh-my-zsh.sh
eval "$(zoxide init zsh)"
source <(ng completion script)
# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

export PATH="$HOME/.local/bin:$HOME/.pyenv/bin:$PATH"

######## Plugins


extract () {
    if [ ! -f "$1" ]
    then
        echo "'$1' does not exist."
        return 1
    fi
    case "$1" in
        (*.tar.bz2) tar xvjf "$1" ;;
        (*.tar.xz) tar xvJf "$1" ;;
        (*.tar.gz) tar xvzf "$1" ;;
        (*.bz2) bunzip2 "$1" ;;
        (*.rar) rar x "$1" ;;
        (*.gz) gunzip "$1" ;;
        (*.tar) tar xvf "$1" ;;
        (*.tbz2) tar xvjf "$1" ;;
        (*.tgz) tar xvzf "$1" ;;
        (*.zip) unzip "$1" ;;
        (*.Z) uncompress "$1" ;;
        (*.xz) xz -d "$1" ;;
        (*.7z) 7z x "$1" ;;
        (*.a) ar x "$1" ;;
        (*) echo "Unable to extract '$1'." ;;
    esac
}

source "$DOTFILES/zsh/.functions" #I dunno, this is tem, something is overriding ls, but not sure which (on both systems different things, lmao)


### MANAGED BY RANCHER DESKTOP START (DO NOT EDIT)
export PATH="/Users/taavaanj/.rd/bin:$PATH"
### MANAGED BY RANCHER DESKTOP END (DO NOT EDIT)
