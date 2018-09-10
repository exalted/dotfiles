cask() {
  if [[ "${1:-}" = search ]]; then
    brew "$@"
    return
  fi

  brew cask "$@"
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
  # `open` command won't recognize custom protocols, such as `chrome://` and
  # passing URLs after `--arg` argument doesn't seem to open links in relevant
  # browsers, so don't even bother to do smart things like `"$url" ~= [a-z]+://`
  if [[ "$url" != http* ]]; then
      url="http://$url"
  fi
  open "$url" "$@"
}

alias safari='browse "$@" -a /Applications/Safari.app/'
alias chrome='browse "$@" -a /Applications/Google\ Chrome.app/'
alias firefox='browse "$@" -a /Applications/Firefox.app/'

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
    browse "https://www.google.com/?gws_rd=ssl#safe=off&q=$search";
  fi
}

serve() {
  python -m SimpleHTTPServer "${1:-8080}"
}

reset-open-with() {
  /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -r -domain local -domain system -domain user
}

kebab() {
  echo "$*" \
  | tr '[:upper:]' '[:lower:]' \
  | tr -C -d ' [:alnum:]./-' \
  | tr -s '-' \
  | tr -s ' ' '-' \
  | sed -E 's/^-(.*)$/\1/' \
  | sed -E 's/^(.*)-$/\1/' \
  | sed -E 's/^-(.*)-$/\1/'
}

alias balsamiq-agenda='open /Users/ali/Library/Mobile\ Documents/74ZAFF46HB~jp~informationarchitects~Writer/Documents/Balsamiq\ Agenda/0-Current.md -a /Applications/iA\ Writer\ Classic.app/'
alias balsamiq-acetaia='browse "https://acetaia.balsamiq.com/#/u31-ali"'
alias balsamiq-wiki='browse "https://balsamiq.atlassian.net/wiki/my/saved-for-later"'

alias balsamiq-ssh-jenkins-master='ssh ubuntu@ec2-46-137-119-50.eu-west-1.compute.amazonaws.com'
alias balsamiq-ssh-logs-prod='ssh ubuntu@ec2-52-201-211-94.compute-1.amazonaws.com'

alias balsamiq-db-acetaia-production='convox resources proxy acetaia-mysql --port 3319'
alias balsamiq-db-bottega-production='convox resources proxy bottega-mysql --port 3329'
alias balsamiq-db-swag-production='convox resources proxy swag-mysql --port 3339'

alias balsamiq-ci-acetaia='balsamiq-ci-internaltools'
alias balsamiq-ci-bottega='balsamiq-ci-internaltools'
alias balsamiq-ci-swag='balsamiq-ci-internaltools'
alias balsamiq-ci-b.com='browse "https://jenkins.balsamiq.com/job/balsamiq.com/"'
alias balsamiq-ci-influencers='balsamiq-ci-internaltools'
alias balsamiq-ci-internaltools='browse "https://jenkins.balsamiq.com/job/Internal_Tools/"'
alias balsamiq-ci-ops='browse "https://jenkins.balsamiq.com/job/Ops/"'
alias balsamiq-ci-pivotalvotes='balsamiq-ci-internaltools'
alias balsamiq-ci-support='browse "https://jenkins.balsamiq.com/job/support.balsamiq.com/"'
alias balsamiq-ci-uxapprentice='browse "https://jenkins.balsamiq.com/job/ux_apprentice/"'
alias balsamiq-ci='browse "https://jenkins.balsamiq.com"'

alias dns-flush='sudo killall -HUP mDNSResponder'
