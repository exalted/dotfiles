# we want these to be installed before everything else (order of these matter)
BOOTSTRAP = %w[
  homebrew
  bash
]

# these get "merged" with the profile-specific list below (do *NOT* rely on the order of these)
COMMON = %w[
  diff
  emojify
  fd
  finicky
  git
  google-chrome
  grc
  grep
  httpie
  iterm2
  jq
  keka
  logitech-options
  macos
  node
  ripgrep
  rocket
  ruby
  tree
  wget
  zed
]

# these get merged with the common list above (do *NOT* rely on the order of these)
PROFILES = {}

PROFILES['personal'] = %w[
  1blocker
  ack
  apple_apps
  aws
  blueutil
  carbon-copy-cloner
  cleanshot-x
  clipy
  code-format
  cups
  custom_automator/remountall
  custom_automator/unmountall
  cyberduck
  docker
  download_subtitles
  dropbox
  envchain
  firefox
  fluid
  gnupg
  grammarly
  hookshot
  ia-writer
  insomnia
  kaleidoscope
  lightning_audio_adapter
  mactracker
  mysql
  ngrok
  nosql-workbench
  omnidisksweeper
  openjdk
  pixelmator
  pwgen
  python
  reeder
  rust
  scapple
  sketch
  slack
  sleepwatcher
  sourcetree
  stripe-cli
  things
  tor-browser
  transmission
  tripmode
  virtualbox
  visual-studio-code
  vlc
  watch
  webtorrent
  whatsapp
  ynab
]
