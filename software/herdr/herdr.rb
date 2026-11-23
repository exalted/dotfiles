#!/usr/bin/env ruby
require_relative '../../src/helpers'

brew 'herdr'

link_to_home_relative 'config.toml', '.config/herdr/config.toml', backup: true

# Generated rather than committed: `herdr --skill` prints the copy that matches
# the installed binary, so a Homebrew upgrade of herdr refreshes it on the next run.
# The local rules go into the same file so that they load whenever the skill does.
skill = `#{brew_prefix}/bin/herdr --skill`
raise 'herdr --skill failed' unless $?.success? && !skill.empty?
skill += File.read("#{__dir__}/skill-local-rules.md")

skill_file = "#{ENV["HOME"]}/.claude/skills/herdr/SKILL.md"
unless File.exist?(skill_file) && File.read(skill_file) == skill
  FileUtils.mkdir_p(File.dirname(skill_file))
  File.write(skill_file, skill)
end
