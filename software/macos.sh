#!/usr/bin/env bash
set -euo pipefail
trap "echo 'error: Script failed: see failed command above'" ERR

# Even quicker keyboard "delay until repeat" and "key repeat rate" than what you
# can achieve via System Preferences GUI
defaults write -g InitialKeyRepeat -int 10
defaults write -g KeyRepeat -int 1

# Prevent creating .DS_Store files on network volumes
defaults write com.apple.desktopservices DSDontWriteNetworkStores -bool true

# Prevent Spotlight indexing external volumes by default
# When you actually want a specific drive indexed you can re-enable it later with
# `sudo mdutil -i on /Volumes/DriveName`
sudo defaults write /Library/Preferences/com.apple.SpotlightServer.plist ExternalVolumesDefaultOff -bool true

# Enable selection of text within Quick Look previews
defaults write com.apple.finder QLEnableTextSelection -bool true
