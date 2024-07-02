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
    --no-remove-listing \
    "$@"
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
      url="https://$url"
  fi

  open "$url" "$@"
}

safari() { browse "$@" -a "Safari"; }
chrome() { browse "$@" -a "Google Chrome"; }
firefox() { browse "$@" -a "Firefox"; }

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

alias speedtest=networkQuality

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

is-git() {
  git rev-parse --git-dir > /dev/null 2>&1
}

alias idea='open -n -a "IntelliJ IDEA" --args "$@"'

date() {
  cat <<EOF | node -
const now = new Date();
console.log(\`\
Human :  \${now.toString()}
ISO   :  \${now.toISOString()}
\`);
EOF
}

alias redis-start="$(brew --prefix)/opt/redis/bin/redis-server $(brew --prefix)/etc/redis.conf"
