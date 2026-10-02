# these get "merged" with the profile-specific list below (do *NOT* rely on the order of these)
COMMON = %w[
  ack
  diff
  emojify
  fd
  git
  grc
  grep
  httpie
  iterm2
  macos
  node
  tree
  watch
  wget
]

# these get merged with the common list above (do *NOT* rely on the order of these)
PROFILES = {}

PROFILES['personal'] = %w[
  1blocker
  apple_apps
  aws
  claude
  claude-code
  cleanshot-x
  clipy
  code-format
  cups
  cyberduck
  docker
  download_subtitles
  dropbox
  envchain
  finicky
  firefox
  gnupg
  google-chrome
  insomnia
  jq
  keka
  logi-options-plus
  mactracker
  mysql
  ngrok
  omnidisksweeper
  openjdk
  pixelmator
  pwgen
  python
  ripgrep
  rocket
  rust
  scapple
  sketch
  slack
  sourcetree
  stripe-cli
  things
  tor-browser
  transmission
  tripmode
  vlc
  whatsapp
  ynab
  zed
]

PROFILES['work'] = %w[
  claude-code
  clipy
  codex
  comply365/cortex
  comply365/jira
  comply365/web-safety
  comply365/zsh
  finicky
  jq
  keka
  logi-options-plus
  ripgrep
  rocket
  sourcetree
  ssh
  zed
]
