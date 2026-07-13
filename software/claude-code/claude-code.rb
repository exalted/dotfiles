#!/usr/bin/env ruby
require_relative '../../src/helpers'

cask 'claude-code@latest'

link_to_home_relative 'CLAUDE.md',             '.claude/CLAUDE.md'
link_to_home_relative 'settings.json',         '.claude/settings.json'
link_to_home_relative 'statusline-command.sh', '.claude/statusline-command.sh'
link_to_home_relative 'themes/dark-mine.json', '.claude/themes/dark-mine.json'
