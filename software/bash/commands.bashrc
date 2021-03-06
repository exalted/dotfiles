cask() {
  if [[ "${1:-}" = search ]]; then
    # Prefer `brew search` to `brew search --cask` as former will show results
    # from both, whilst latter will only show cask results
    brew search "${@:2}"
    return
  fi

  brew "$1" --cask "${@:2}"
}

spider() {
  wget \
    --force-directories \
    --recursive \
    --level=inf \
    --page-requisites \
    --convert-links \
    --adjust-extension \
    --no-remove-listing
}

diskusage() { du -sh "$@" | sort --human-numeric-sort --reverse; }

browse() {
  local url="$1" && shift

  if [[ -z "$url" ]]; then
    if is-git; then
      # Try to open the PR, if there's one, else try to open the repository
      { gh pr view --web 2> /dev/null || gh repo view --web 2> /dev/null; } && return 0
    fi

    echo 'Usage: browse example.com' >&2
    return 1
  fi

  # `open` command won't recognize custom protocols, such as `chrome://` and
  # passing URLs after `--arg` argument doesn't seem to open links in relevant
  # browsers, so don't even bother to do smart things like `"$url" ~= [a-z]+://`
  if [[ "$url" != http* ]]; then
      url="http://$url"
  fi

  open "$url" "$@"
}

alias safari='browse "$@" -a /Applications/Safari.app'
alias chrome='browse "$@" -a /Applications/Google\ Chrome\ Dev.app'
alias firefox='browse "$@" -a /Applications/Firefox\ Developer\ Edition.app'

google() {
  local search=""
  for term in "$@"; do
    if [[ -z "${search:-}" ]]; then
        search="$term"
    else
        search="$search%20$term"
    fi
  done
  if [[ -z "${search:-}" ]]; then
    echo 'Usage: google something' >&2
    return 1
  else
    browse "https://www.google.com/search?q=$search";
  fi
}

serve() {
  python -m SimpleHTTPServer "${1:-8080}"
}

reset-open-with() {
  /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -r -domain local -domain system -domain user
}

compact() {
  hdiutil compact "$@"
}
alias shrink=compact

alias dns-flush='sudo killall -HUP mDNSResponder'

b-ssh-jenkins-master() {
  cat <<EOF
Once logged in run:
  $ sudo -s
  # su jenkins

... to become Jenkins user (ref: https://balsamiq.atlassian.net/wiki/x/ToQuEw).

EOF
  ssh ubuntu@ec2-46-137-119-50.eu-west-1.compute.amazonaws.com
}

alias b-convox-production='envchain convox-production convox-wrapper'
alias b-convox-rtc-production='envchain convox-rtc-production convox-wrapper'
alias b-convox-staging='envchain convox-staging convox-wrapper'
alias b-convox-ondeck='envchain convox-ondeck convox-wrapper'

alias b-db-acetaia-production='b-convox-production rack resources proxy acetaia-mysql --port 3319'
alias b-db-bottega-production='b-convox-production rack resources proxy bottega-mysql --port 3329'
alias b-db-swag-production='b-convox-production rack resources proxy swag-mysql --port 3339'
alias b-db-olio-staging='ssh -L 33060:olio-staging.ciuzowupcgac.eu-west-1.rds.amazonaws.com:3306 -L 36379:olio-staging-redis.si22bk.0001.euw1.cache.amazonaws.com:6379 -i ~/.ssh/keys/balsamiq-olio-gateway.pem ubuntu@ec2-54-228-238-179.eu-west-1.compute.amazonaws.com'
alias b-db-olio-production='ssh -L 33306:olio-rds.ciuzowupcgac.eu-west-1.rds.amazonaws.com:3306 -i ~/.ssh/keys/balsamiq-olio-gateway.pem ubuntu@ec2-54-228-238-179.eu-west-1.compute.amazonaws.com'

is-git() {
  git rev-parse --git-dir > /dev/null 2>&1
}
