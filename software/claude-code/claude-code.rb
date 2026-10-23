#!/usr/bin/env ruby
require_relative '../../src/helpers'

cask 'claude-code@latest'
bash_source_relative

link_to_home_relative 'CLAUDE.md',             '.claude/CLAUDE.md'
link_to_home_relative 'settings.json',         '.claude/settings.json'
link_to_home_relative 'statusline-command.sh', '.claude/statusline-command.sh'
link_to_home_relative 'themes/dark-mine.json', '.claude/themes/dark-mine.json'

# Weekly unattended `/claude-code-levers refresh`; see skills/common/claude-code-levers.
# One machine refreshes the map and pushes it; every other machine takes the map
# from Git, so it drops the job and the local leftovers of earlier runs: the docs
# mirror the refresh reads, and its log.
if _resolve_profile == 'work'
  link_to_home_relative 'claude-code-levers-refresh.sh', '.claude/claude-code-levers-refresh.sh'
  launch_agent_relative 'com.dotfiles.claude-code-levers-refresh.plist'
else
  launch_agent_remove_relative 'com.dotfiles.claude-code-levers-refresh.plist'
  trash "#{ENV["HOME"]}/.claude/claude-code-levers-refresh.sh"
  trash "#{ENV["HOME"]}/Library/Logs/claude-code-levers-refresh.log"
  trash File.expand_path("#{__dir__}/../../.claude/scratchpad.local/claude-code-levers")
end

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

# Hooks that settings.json runs, and the module they share; see each script for what it enforces.
link_to_home_relative 'hooks/require-command-prefix.py', '.claude/hooks/require-command-prefix.py'
link_to_home_relative 'hooks/guard-paths.py',            '.claude/hooks/guard-paths.py'
link_to_home_relative 'hooks/deny-deletions.py',         '.claude/hooks/deny-deletions.py'
link_to_home_relative 'hooks/guard-rebase.py',           '.claude/hooks/guard-rebase.py'
link_to_home_relative 'hooks/shell_commands.py',         '.claude/hooks/shell_commands.py'
