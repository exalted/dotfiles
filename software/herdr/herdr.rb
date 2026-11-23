#!/usr/bin/env ruby
require_relative '../../src/helpers'
require 'tmpdir'

brew 'herdr'

link_to_home_relative 'config.toml', '.config/herdr/config.toml', backup: true

exit unless software_manifest.include?('claude-code')

def write_if_changed(path, content, mode: nil)
  File.chmod(mode, path) if mode && File.file?(path)
  return if File.file?(path) && File.read(path) == content

  FileUtils.mkdir_p(File.dirname(path))
  File.write(path, content)
  File.chmod(mode, path) if mode
end

# Generated rather than committed: `herdr --skill` prints the copy that matches
# the installed binary, so a Homebrew upgrade of herdr refreshes it on the next run.
# The local rules go into the same file so that they load whenever the skill does.
skill = `#{brew_prefix}/bin/herdr --skill`
raise 'herdr --skill failed' unless $?.success? && !skill.empty?
skill += File.read("#{__dir__}/skill-local-rules.md")
write_if_changed "#{ENV["HOME"]}/.claude/skills/herdr/SKILL.md", skill

# The hook script, like the skill, must match the installed binary. The installer
# runs against a throwaway HOME because it would otherwise write its settings.json
# entry, with the absolute home path, through ~/.claude/settings.json into this
# repo. The tracked settings.json carries our own copy of that entry instead.
HOOK_SCRIPT = 'herdr-agent-state.sh'

def herdr_hook_entries(settings)
  settings.fetch('hooks', {}).flat_map do |event, groups|
    groups.flat_map do |group|
      group.fetch('hooks', [])
           .select { |hook| hook['command'].to_s.include?(HOOK_SCRIPT) }
           .map do |hook|
             args = hook['command'][/.*#{Regexp.escape(HOOK_SCRIPT)}'?\s+(.*)\z/, 1]
             [event, group['matcher'].to_s, hook['timeout'].to_i, args.to_s]
           end
    end
  end.sort
end

Dir.mktmpdir do |home|
  FileUtils.mkdir_p("#{home}/.claude")
  Kernel.system({ 'HOME' => home }, "#{brew_prefix}/bin/herdr", 'integration', 'install', 'claude',
                out: File::NULL, exception: true)

  installed = "#{home}/.claude/hooks/#{HOOK_SCRIPT}"
  write_if_changed "#{ENV["HOME"]}/.claude/hooks/#{HOOK_SCRIPT}", File.read(installed),
                   mode: File.stat(installed).mode & 0o777

  wanted = herdr_hook_entries(JSON.parse(File.read("#{home}/.claude/settings.json")))
  tracked = herdr_hook_entries(JSON.parse(File.read("#{__dir__}/../claude-code/settings.json")))
  unless wanted == tracked
    warn "herdr: the #{HOOK_SCRIPT} hooks in software/claude-code/settings.json differ from " \
         "what `herdr integration install claude` writes; update them to match " \
         "(event, matcher, timeout, arguments):\n  herdr wants: #{wanted.inspect}\n  tracked:     #{tracked.inspect}"
  end
end
