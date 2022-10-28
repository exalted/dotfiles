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

    >&2 echo 'Usage: browse example.com'
    return 1
  fi

  # `open` command won't recognize custom protocols, such as `chrome://` and
  # passing URLs after `--arg` argument doesn't seem to open links in relevant
  # browsers, so don't even bother doing "smart" things like `"$url" ~= [a-z]+://`
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
    >&2 echo 'Usage: google something'
    return 1
  else
    browse "https://www.google.com/search?q=$search";
  fi
}

alias mdn='google mdn'

serve() {
  "$(brew --prefix)/bin/python3" -m http.server "${1:-8080}"
}

reset-open-with() {
  /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -r -domain local -domain system -domain user
}

compact() {
  hdiutil compact "$@"
}
alias shrink=compact

alias dns-flush='sudo killall -HUP mDNSResponder'

# Ref: https://oauth2-proxy.github.io/oauth2-proxy/docs/configuration/overview
# Python: `python -c 'import os,base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())'`
# Bash: `dd if=/dev/urandom bs=32 count=1 2>/dev/null | base64 | tr -d -- '\n' | tr -- '+/' '-_'; echo`
# OpenSSL: `openssl rand -base64 32 | tr -- '+/' '-_'`
random-cookie-secret() {
  openssl rand -base64 32 | tr -- '+/' '-_'
}

b-ssh-jenkins-master() {
  cat <<EOF
Once logged to become Jenkins user do this:
  $ sudo -s
  # su jenkins

Read more: https://balsamiq.atlassian.net/wiki/x/ToQuEw

EOF
  ssh ubuntu@ec2-46-137-119-50.eu-west-1.compute.amazonaws.com
}

# TODO: remove hard-coded path
alias b-convox-production='envchain convox-production $HOME/Development/balsamiq/convox-ops/bin/convox-wrapper'
alias b-convox-rtc-production='envchain convox-rtc-production $HOME/Development/balsamiq/convox-ops/bin/convox-wrapper'
alias b-convox-staging='envchain convox-staging $HOME/Development/balsamiq/convox-ops/bin/convox-wrapper'
alias b-convox-ondeck='envchain convox-eu-6 $HOME/Development/balsamiq/convox-ops/bin/convox-wrapper'

alias b-db-acetaia-production='b-convox-production rack resources proxy acetaia-mysql --port 3319'
alias b-db-bottega-production='b-convox-production rack resources proxy bottega-mysql --port 3329'
alias b-db-swag-production='b-convox-production rack resources proxy swag-mysql --port 3339'
alias b-db-olio-staging='(cd olio/ && ./ssh-tunnel-staging.sh -i ~/.ssh/keys/balsamiq-olio-staging.pem)'
alias b-db-olio-feature='(cd olio/ && ./ssh-tunnel-feature.sh -i ~/.ssh/keys/balsamiq-olio-feature.pem)'
alias b-db-olio-production='(cd olio/ && ./ssh-tunnel-production.sh -i ~/.ssh/keys/balsamiq-olio-production.pem)'

alias node16="$(brew --prefix)/opt/node@16/bin/node"
alias node14="$(brew --prefix)/opt/node@14/bin/node"
alias node12="$(brew --prefix)/opt/node@12/bin/node"

b-node() {
  envchain balsamiq-private-npm-registry /bin/bash -ic 'export PRIVATE_NPM_AUTH_TOKEN=$BALSAMIQ_NPM_AUTH_TOKEN; node'" $*"
}
b-node16() {
  envchain balsamiq-private-npm-registry /bin/bash -ic 'export PRIVATE_NPM_AUTH_TOKEN=$BALSAMIQ_NPM_AUTH_TOKEN; node16'" $*"
}
b-node14() {
  envchain balsamiq-private-npm-registry /bin/bash -ic 'export PRIVATE_NPM_AUTH_TOKEN=$BALSAMIQ_NPM_AUTH_TOKEN; node14'" $*"
}
b-node12() {
  envchain balsamiq-private-npm-registry /bin/bash -ic 'export PRIVATE_NPM_AUTH_TOKEN=$BALSAMIQ_NPM_AUTH_TOKEN; node12'" $*"
}

alias node16-npm="$(brew --prefix)/opt/node@16/bin/npm"
alias node14-npm="$(brew --prefix)/opt/node@14/bin/npm"
alias node12-npm="$(brew --prefix)/opt/node@12/bin/npm"
alias npm-node16=node16-npm
alias npm-node14=node14-npm
alias npm-node12=node12-npm

b-npm() {
  envchain balsamiq-private-npm-registry /bin/bash -ic 'export PRIVATE_NPM_AUTH_TOKEN=$BALSAMIQ_NPM_AUTH_TOKEN; npm'" $*"
}
b-node16-npm() {
  envchain balsamiq-private-npm-registry /bin/bash -ic 'export PRIVATE_NPM_AUTH_TOKEN=$BALSAMIQ_NPM_AUTH_TOKEN; node16-npm'" $*"
}
alias b-npm-node16=b-node16-npm
b-node14-npm() {
  envchain balsamiq-private-npm-registry /bin/bash -ic 'export PRIVATE_NPM_AUTH_TOKEN=$BALSAMIQ_NPM_AUTH_TOKEN; node14-npm'" $*"
}
alias b-npm-node14=b-node14-npm
b-node12-npm() {
  envchain balsamiq-private-npm-registry /bin/bash -ic 'export PRIVATE_NPM_AUTH_TOKEN=$BALSAMIQ_NPM_AUTH_TOKEN; node12-npm'" $*"
}
alias b-npm-node12=b-node12-npm

is-git() {
  git rev-parse --git-dir > /dev/null 2>&1
}

bootstrap--bw-jira() {
  source "$HOME/.sdkman/bin/sdkman-init.sh"
  sdk use java 8.0.332-tem
}

workon--bw-jira() {
  cd ~/Development/balsamiq/bw-jira/

  bootstrap--bw-jira

  envchain balsamiq-private-npm-registry /bin/bash -c 'export PRIVATE_NPM_AUTH_TOKEN=$BALSAMIQ_NPM_AUTH_TOKEN; npx concurrently --names "database,front-end,back-end,logs,reload" --kill-others \
    "/opt/homebrew/opt/postgresql@11/bin/postgres -D /opt/homebrew/var/postgresql@11" \
    "npx onchange '"'"'src/main/js/**'"'"' --initial --kill -- \"$(brew --prefix)/opt/node@14/bin/node\" ./node_modules/.bin/grunt build" \
    "./launchJira.sh" \
    "npx wait-on http-get://localhost:2990/jira/ && tail -f ./target/jira/home/log/atlassian-jira.log" \
    "npx wait-on http-get://localhost:2990/jira/ && npx onchange '"'"'**'"'"' --exclude-path .gitignore --kill -- time atlas-package -DskipTests -Datlassian.webresource.disable.minification=true"' \
  || true
}

alias idea='open -n -a /Applications/IntelliJ\ IDEA.app --args "$@"'
