#!/usr/bin/env ruby
require_relative '../../src/helpers'

cask 'iterm2'

# https://iterm2.com/documentation-shell-integration.html
system "curl -fsSL https://iterm2.com/shell_integration/bash -o #{__dir__}/shell_integration"

# Sourced from `software/zed/bashrc` instead of here, since whether to load
# it depends on not running inside Zed's own integrated terminal.

#
# Sync settings across machines via iTerm2's native "custom folder" feature
# (https://iterm2.com/documentation-preferences-general.html): iTerm2 loads its
# settings from the folder on launch and (per the save-mode below) writes them
# back on quit, excluding its own `NoSync*` machine-local keys — so, unlike a raw
# plist copy, only portable settings land in `com.googlecode.iterm2.plist` here.
#
# `PrefsCustomFolder` is derived from `__dir__` so each machine points at its own
# clone wherever it lives; the path is kept only in this machine's local
# `~/Library/Preferences` copy and is never the file we commit.
#
# iTerm2 writes that plist as XML (readable diffs). If it ever regresses to
# binary, normalize before committing: `plutil -convert xml1 <that plist>`.
system %(defaults write com.googlecode.iterm2 PrefsCustomFolder -string "#{__dir__}")
system "defaults write com.googlecode.iterm2 LoadPrefsFromCustomFolder -bool true"

# Write changes back to the folder automatically on quit (no per-quit prompt).
# `_selection` 2 == "Save automatically"; these are `NoSync*` (machine-local), so
# they're set here per machine and never travel in the committed plist.
system "defaults write com.googlecode.iterm2 NoSyncNeverRemindPrefsChangesLostForFile -bool true"
system "defaults write com.googlecode.iterm2 NoSyncNeverRemindPrefsChangesLostForFile_selection -int 2"
