#!/usr/bin/env bash
set -euo pipefail
trap "echo 'error: Script failed: see failed command above'" ERR

# Even quicker keyboard "delay until repeat" and "key repeat rate" than what you
# can achieve via System Preferences GUI
defaults write -g InitialKeyRepeat -int 10
defaults write -g KeyRepeat -int 1

# Prevent creating .DS_Store files on network volumes
defaults write com.apple.desktopservices DSDontWriteNetworkStores -bool true

# Enable selection of text within Quick Look previews
defaults write com.apple.finder QLEnableTextSelection -bool true
