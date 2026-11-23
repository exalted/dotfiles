#!/usr/bin/env ruby
require_relative '../../src/helpers'

cask 'claude-code@latest'
bash_source_relative

link_to_home_relative 'CLAUDE.md',             '.claude/CLAUDE.md'
link_to_home_relative 'settings.json',         '.claude/settings.json'
link_to_home_relative 'statusline-command.sh', '.claude/statusline-command.sh'

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

# Unattended night shift, its weekly security analysis its morning fetch check and its Monday team question; see skills/work/night-shift.
if _resolve_profile == 'work'
  link_to_home_relative 'night-shift.sh', '.claude/night-shift.sh'
  launch_agent_relative 'com.dotfiles.night-shift.plist'
  launch_agent_relative 'com.dotfiles.night-shift-security.plist'
  launch_agent_relative 'com.dotfiles.night-shift-check.plist'
launch_agent_relative 'com.dotfiles.night-shift-team.plist'
  launch_agent_relative 'com.dotfiles.night-shift-power.plist'
else
  launch_agent_remove_relative 'com.dotfiles.night-shift.plist'
  launch_agent_remove_relative 'com.dotfiles.night-shift-security.plist'
  launch_agent_remove_relative 'com.dotfiles.night-shift-check.plist'
launch_agent_remove_relative 'com.dotfiles.night-shift-team.plist'
  launch_agent_remove_relative 'com.dotfiles.night-shift-power.plist'
  trash "#{ENV["HOME"]}/.claude/night-shift.sh"
end

# Weekly ai-capacity refresh, then model-steward; see skills/work/ai-capacity and skills/work/model-steward.
if _resolve_profile == 'work'
  link_to_home_relative 'ai-capacity-refresh.sh', '.claude/ai-capacity-refresh.sh'
  launch_agent_relative 'com.dotfiles.ai-capacity-refresh.plist'
else
  launch_agent_remove_relative 'com.dotfiles.ai-capacity-refresh.plist'
  trash "#{ENV["HOME"]}/.claude/ai-capacity-refresh.sh"
end

# One link per skill, never one for ~/.claude/skills itself: Claude Code writes
# the skills it syncs from claude.ai into that directory too.
%W[common #{_resolve_profile}].each do |group|
  Dir.glob("#{__dir__}/skills/#{group}/*").select { |path| File.directory?(path) }.each do |skill|
    link_directory skill, "#{ENV["HOME"]}/.claude/skills/#{File.basename(skill)}"
  end
end

# Plugins live in plugins/<group>/ and reach Claude Code through the marketplace file in
# plugins/.claude-plugin/. settings.json is shared by every machine but the clone path is not,
# so settings.json declares the marketplace at this link instead of at the clone.
marketplace_link = "#{ENV["HOME"]}/.claude/dotfiles-plugins"
link_directory "#{__dir__}/plugins", marketplace_link

# The CLI does not register a marketplace that settings.json only declares, so `plugin install`
# fails until `marketplace add` runs once per machine. That command also rewrites the declared
# path in settings.json to an absolute, per-user one; this repo is public, so it is put back.
unless `claude plugin marketplace list --json 2>/dev/null`.include? '"name": "dotfiles"'
  settings = "#{__dir__}/settings.json"
  declared = File.read settings
  system "claude plugin marketplace add #{marketplace_link}"
  File.write settings, declared
end

if _resolve_profile == 'work'
  system "claude plugin install lsp-servers@dotfiles --scope user" unless Kernel.system "claude plugin list 2>/dev/null | grep -q lsp-servers@dotfiles"

  # Official LSP plugins whose language lsp-servers already covers. Claude Code still offers each
  # one on first use of its files, and it remembers a "Never" answer in ~/.claude.json, which is
  # app state, not settings.json, so the answer is recorded here. Extend this list together with
  # `enabledPlugins` in settings.json; see "LSP servers live in dotfiles" in CLAUDE.md.
  covered_lsp_plugins = %w[gopls-lsp pyright-lsp ruby-lsp swift-lsp typescript-lsp]
  ensure_json_array_entries "#{ENV["HOME"]}/.claude.json", 'lspRecommendationNeverPlugins',
                            covered_lsp_plugins.map { |name| "#{name}@claude-plugins-official" }
end

# The style plugin redraws the chat and ships the color theme, so it installs on every profile.
system "claude plugin install my-claude-code-style@dotfiles --scope user" unless Kernel.system "claude plugin list 2>/dev/null | grep -q my-claude-code-style@dotfiles"

# Hooks that settings.json runs, and the module they share; see each script for what it enforces.
link_to_home_relative 'hooks/require-command-prefix.py', '.claude/hooks/require-command-prefix.py'
link_to_home_relative 'hooks/guard-paths.py',            '.claude/hooks/guard-paths.py'
link_to_home_relative 'hooks/deny-deletions.py',         '.claude/hooks/deny-deletions.py'
link_to_home_relative 'hooks/guard-git-history.py',      '.claude/hooks/guard-git-history.py'
link_to_home_relative 'hooks/story-not-ticket.py',       '.claude/hooks/story-not-ticket.py'
link_to_home_relative 'hooks/shell_commands.py',         '.claude/hooks/shell_commands.py'
link_to_home_relative 'hooks/notify.sh',                 '.claude/hooks/notify.sh'
# software/herdr writes this hook script and skill on profiles that also have herdr.
unless software_manifest.include?('herdr')
  trash "#{ENV["HOME"]}/.claude/hooks/herdr-agent-state.sh"
  trash "#{ENV["HOME"]}/.claude/skills/herdr"
end
