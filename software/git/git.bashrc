# For the settings below, read the docs for `git-prompt.sh`

# unstaged (*) and staged (+) changes will be shown next to the branch name
export GIT_PS1_SHOWDIRTYSTATE=true
# if something is stashed, then a '$' will be shown next to the branch name
export GIT_PS1_SHOWSTASHSTATE=true
# if there're untracked files, then a '%' will be shown next to the branch name
export GIT_PS1_SHOWUNTRACKEDFILES=true
# see the difference between HEAD and its upstream:
#   - "<" indicates you are behind
#   - ">" indicates you are ahead
#   - "<>" indicates you have diverged
#   - "=" indicates that there is no difference
export GIT_PS1_SHOWUPSTREAM=auto
