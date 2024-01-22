#!/bin/bash
set -euo pipefail
trap "echo 'error: Script failed: see failed command above'" ERR

defaults write com.apple.desktopservices DSDontWriteNetworkStores true
defaults write com.apple.finder QLEnableTextSelection -bool true
