cask() {
  case "${1:-}" in
    search)
      command brew search --cask "${@:2}"
      ;;
    install)
      command brew install --yes --cask "${@:2}"
      ;;
    *)
      >&2 echo 'Usage: cask search|install ...'
      return 1
      ;;
  esac
}

brew() {
  case "${1:-}" in
    instal | install | reinstall | upgrade)
      command brew "$1" --yes "${@:2}"
      ;;
    *)
      command brew "$@"
      ;;
  esac
}

# Offers to upgrade a Homebrew cask at most once per 24 hours; meant to wrap a CLI
# that the cask installs, e.g.
# `foo() { _foo_starts_session "$@" && upgrade-cask-daily foo; command foo "$@"; }`.
# The caller decides which invocations start an interactive session; without a
# terminal to ask on, this does nothing and leaves the stamp alone, so the next
# interactive start asks. The stamp is written before the question, so a "no"
# or a failed upgrade (offline) counts for the day, and a second terminal opened
# meanwhile does not ask again. A failure never blocks the wrapped CLI.
upgrade-cask-daily() {
  local cask="$1"
  local stamp="${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles/upgrade-cask-daily/$cask"
  local now last=0 answer

  [[ -t 0 && -t 1 ]] || return 0
  [ -d "${HOMEBREW_PREFIX:-/opt/homebrew}/Caskroom/$cask" ] || return 0

  printf -v now '%(%s)T' -1
  [ -r "$stamp" ] && read -r last < "$stamp"
  (( now - last >= 24 * 60 * 60 )) || return 0

  command mkdir -p "${stamp%/*}" && printf '%s\n' "$now" > "$stamp"
  # One key, so Esc skips at once; Esc sequences (arrow keys) are drained so
  # their tail does not reach the wrapped CLI.
  printf 'upgrade-cask-daily: upgrade %s now? [Y/n, Esc skips] ' "$cask"
  IFS= read -rsn1 answer || answer=n
  [[ $answer == $'\e' ]] && while IFS= read -rsn1 -t 0.05 _; do :; done
  if [[ -z $answer || $answer == [Yy] ]]; then
    echo yes
  else
    echo no
    >&2 echo "upgrade-cask-daily: skipped; next question in 24 hours"
    return 0
  fi
  command brew upgrade --cask "$cask" \
    || >&2 echo "upgrade-cask-daily: could not upgrade $cask; running the installed version, next attempt in 24 hours"
  return 0
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
  python3 -m http.server "${1:-8080}"
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

idea() { open -n -a "IntelliJ IDEA" --args "$@"; }

date() {
  cat <<EOF | node -
const now = new Date();
console.log(\`\
Human :  \${now.toString()}
ISO   :  \${now.toISOString()}
\`);
EOF
}

# alias redis-start="$HOMEBREW_PREFIX/opt/redis/bin/redis-server $HOMEBREW_PREFIX/etc/redis.conf"
alias redis-start='brew services run redis'
alias redis-stop='brew services stop redis'
