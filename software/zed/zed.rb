#!/usr/bin/env ruby
require_relative '../../src/helpers'

# Brew quits Zed to upgrade it, and Zed does not restore text typed in its
# terminal panel but not yet submitted.
cask 'zed@preview', confirm_before_quit: true

link_to_home_relative 'settings.json', '.config/zed/settings.json'
link_to_home_relative 'keymap.json', '.config/zed/keymap.json'
