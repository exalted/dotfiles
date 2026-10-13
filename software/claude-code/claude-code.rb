#!/usr/bin/env ruby
require_relative '../../src/helpers'

cask 'claude-code@latest'

link_to_home_relative 'CLAUDE.md',             '.claude/CLAUDE.md'
link_to_home_relative 'settings.json',         '.claude/settings.json'
link_to_home_relative 'statusline-command.sh', '.claude/statusline-command.sh'
link_to_home_relative 'themes/dark-mine.json', '.claude/themes/dark-mine.json'

# Weekday unattended recap; see skills/work/comply365-recap.
if _resolve_profile == 'work'
  link_to_home_relative 'comply365-recap.sh', '.claude/recap.sh'
  launch_agent_relative 'com.dotfiles.comply365-recap.plist'
end

# One link per skill, never one for ~/.claude/skills itself: Claude Code writes
# the skills it syncs from claude.ai into that directory too.
%W[common #{_resolve_profile}].each do |group|
  Dir.glob("#{__dir__}/skills/#{group}/*").select { |path| File.directory?(path) }.each do |skill|
    link_directory skill, "#{ENV["HOME"]}/.claude/skills/#{File.basename(skill)}"
  end
end
