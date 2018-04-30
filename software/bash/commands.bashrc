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

alias diskusage='du -sh'

browse() {
  local url="$1" && shift
  if [[ "$url" != http*  ]]; then
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

alias b-com='browse "balsamiq.com"'
alias b-cloud='browse "balsamiq.cloud"'
alias b-agenda='open /Users/ali/Library/Mobile\ Documents/74ZAFF46HB\~jp\~informationarchitects\~Writer/Documents/Balsamiq\ Agenda/Latest.md -a /Applications/iA\ Writer\ Classic.app/'
alias b-wiki='browse "https://balsamiq.atlassian.net/wiki/my/saved-for-later"'
alias b-jenkins='browse "https://jenkins.balsamiq.com"'
alias b-jenkins-com='browse "https://jenkins.balsamiq.com/job/balsamiq.com/"'
alias b-jenkins-internaltools='browse "https://jenkins.balsamiq.com/job/Internal_Tools/"'
alias b-jenkins-acetaia='b-jenkins-internaltools'
alias b-jenkins-bottega='b-jenkins-internaltools'
alias b-jenkins-pivotalvotes='b-jenkins-internaltools'
alias b-jenkins-influencers='b-jenkins-internaltools'
alias b-jenkins-support='browse "https://jenkins.balsamiq.com/job/support.balsamiq.com/"'
alias b-jenkins-uxapprentice='browse "https://jenkins.balsamiq.com/job/ux_apprentice/"'
alias b-jenkins-ops='browse "https://jenkins.balsamiq.com/job/Ops/"'
alias acetaia='browse "https://acetaia.balsamiq.com/#/u31-ali"'
alias bottega='browse "bottega.balsamiq.com"'

alias cask='brew cask'

alias dns-flush='sudo killall -HUP mDNSResponder'
