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

alias dns-flush='sudo killall -HUP mDNSResponder'

balsamiq-ssh-jenkins-master() {
  cat <<EOF
Once logged in run:
  $ sudo -s
  # su jenkins

... to become Jenkins user (ref: https://balsamiq.atlassian.net/wiki/x/ToQuEw).

EOF
  ssh ubuntu@ec2-46-137-119-50.eu-west-1.compute.amazonaws.com
}

alias balsamiq-ssh-tld-redirector='ssh ec2-user@ec2-54-75-234-210.eu-west-1.compute.amazonaws.com'

alias balsamiq-db-acetaia-production='convox rack resources proxy acetaia-mysql --port 3319'
alias balsamiq-db-bottega-production='convox rack resources proxy bottega-mysql --port 3329'
alias balsamiq-db-swag-production='convox rack resources proxy swag-mysql --port 3339'
alias balsamiq-db-olio-staging='ssh -L 33060:olio-staging.ciuzowupcgac.eu-west-1.rds.amazonaws.com:3306 -L 36379:olio-staging-redis.si22bk.0001.euw1.cache.amazonaws.com:6379 -i ~/.ssh/keys/balsamiq-olio-gateway.pem ubuntu@ec2-54-228-238-179.eu-west-1.compute.amazonaws.com'
alias balsamiq-db-olio-production='ssh -L 33306:olio-rds.ciuzowupcgac.eu-west-1.rds.amazonaws.com:3306 -i ~/.ssh/keys/balsamiq-olio-gateway.pem ubuntu@ec2-54-228-238-179.eu-west-1.compute.amazonaws.com'

alias balsamiq-ci-b.com='browse "https://jenkins.balsamiq.com/job/balsamiq.com/"'

alias balsamiq-ci-acetaia='browse https://jenkins.balsamiq.com/job/Internal_Tools/job/acetaia-production/'
alias balsamiq-ci-bottega='browse https://jenkins.balsamiq.com/job/Internal_Tools/job/bottega-production/'
alias balsamiq-ci-swag='browse https://jenkins.balsamiq.com/job/Internal_Tools/job/swag-production/'

alias balsamiq-ci-devops='browse https://jenkins.balsamiq.com/job/Ops/'
alias balsamiq-ci-ops=balsamiq-ci-devops

alias balsamiq-ci-olio-staging='browse https://jenkins.balsamiq.com/job/Olio/view/Staging/'
alias balsamiq-ci-olio-production='browse https://jenkins.balsamiq.com/job/Olio/view/Production/'
