# Inspired by https://github.com/Homebrew/install/blob/63e779e5d6cc1cd7ddefda9c0eb404687d1a1c79/install

require 'fileutils'
require_relative '../profiles'

module Tty
  module_function

  def blue
    bold 34
  end

  def red
    bold 31
  end

  def cyan
    italic 36
  end

  def reset
    escape 0
  end

  def bold(n = 39)
    escape "1;#{n}"
  end

  def italic(n = 39)
    escape "3;#{n}"
  end

  def underline
    escape "4;39"
  end

  def escape(n)
    "\033[#{n}m" if STDOUT.tty?
  end
end

class Array
  def shell_s
    cp = dup
    first = cp.shift
    cp.map { |arg| arg.gsub " ", "\\ " }.unshift(first).join(" ")
  end
end

def ohai(*args)
  puts "#{Tty.blue}dotfiles:#{Tty.bold} #{args.shell_s}#{Tty.reset}"
end

def warn(warning)
  puts "#{Tty.red}Warning#{Tty.reset}: #{warning.chomp}"
end

def cmd_exists?(cmdname)
  Kernel.system "command -v #{cmdname} > /dev/null"
end

def app_installed?(name)
  Dir.exist?("/Applications/#{name}.app") || Dir.exist?("#{ENV["HOME"]}/Applications/#{name}.app")
end

# ? This overrides built-in system command
def system(*args)
  result = Kernel.system(*args)
  abort "Failed during: #{args.shell_s}" unless result
  return result
end

# Prompt for sudo upfront so the password is asked at a predictable moment,
# then refresh the timestamp every 60s so it doesn't expire (5-min default)
# during long stretches between sudo calls. Pairs with _shadow_brew_with_pty,
# which keeps brew from wiping the cache mid-run.
def _keep_sudo_alive
  Kernel.system("sudo", "--validate") or abort "sudo authentication failed"
  Thread.new do
    loop do
      sleep 60
      Kernel.system("sudo", "--non-interactive", "--validate")
    end
  end
end

# Shadow `brew` on PATH with a wrapper that runs the real brew inside its own
# pseudo-TTY (via `script`).
#
# Why: every brew invocation runs `sudo --reset-timestamp` at startup
# (brew.sh:1126) to defend against unauthorized sudo in formula code. That
# wipes whatever sudo cache `_keep_sudo_alive` is maintaining. Since sudo's
# timestamps are per-TTY, putting brew inside its own pty confines the reset
# to that pty — our terminal's timestamp keeps living.
# Ref: https://github.com/Homebrew/brew/issues/17912
#
# Caveats:
# * `script` collapses brew's stdout and stderr into a single channel (a pty
#   has only one), so `brew foo 2>err.log` won't capture anything in err.log
#   — both streams come back on stdout.
# * The wrapper is rewritten on every run, so its contents always match this
#   function; don't edit software/homebrew/bin/brew directly.
def _shadow_brew_with_pty
  wrapper_dir = "#{__dir__}/../software/homebrew/bin"
  FileUtils.mkdir_p(wrapper_dir)
  File.write("#{wrapper_dir}/brew", <<~SH)
    #!/bin/bash
    # Auto-generated each run by src/common.rb::_shadow_brew_with_pty.
    # Runs the real brew in its own pseudo-TTY so brew's `sudo --reset-timestamp`
    # only kills the timestamp inside that pty, sparing our terminal's sudo cache.
    # Ref: https://github.com/Homebrew/brew/issues/17912
    set -o pipefail
    for p in $(type -ap brew); do
      if [ "$p" != "$0" ] && [ -x "$p" ]; then
        if [ -t 1 ]; then
          # Interactive: let \\r through so brew's progress bars render properly.
          exec script -q /dev/null "$p" "$@"
        else
          # Captured (pipe / `$(...)` / backticks): strip \\r so paths like
          # `$(brew --prefix)` don't end up as `/opt/homebrew\\r`.
          script -q /dev/null "$p" "$@" | tr -d '\\r'
          exit "${PIPESTATUS[0]}"
        fi
      fi
    done
    echo "brew-pty-wrapper: real brew not found on PATH" >&2
    exit 127
  SH
  File.chmod(0755, "#{wrapper_dir}/brew")
  ENV["PATH"] = "#{wrapper_dir}:#{ENV["PATH"]}"
end

# Only executable files count as entry scripts — that's resolve_software's
# contract, and it's what tells an installer apart from a support file it
# sources (e.g. lightning_audio_adapter/index.js).
def _defined_software_names
  ext = /\.(#{SOFTWARE_EXTENSIONS.join("|")})\z/
  entry = ->(path) { File.file?(path) && File.executable?(path) && File.basename(path) =~ ext }

  Dir.children(SOFTWARE_DIR).sort.flat_map do |name|
    path = "#{SOFTWARE_DIR}/#{name}"
    next name.sub(ext, "") if entry.call(path)
    next [] unless File.directory?(path)
    Dir.children(path).sort.filter_map do |child|
      next unless entry.call("#{path}/#{child}")
      stem = child.sub(ext, "")
      stem == name ? name : "#{name}/#{stem}"
    end
  end.uniq
end

# Cross-checks software/ against profiles.rb before anything is installed, so a
# typo or a stale entry surfaces up front instead of aborting mid-install.
def _guard_profiles
  configured = (BOOTSTRAP + COMMON + PROFILES.values.flatten).uniq

  orphaned = _defined_software_names - configured
  warn "defined in software/ but not configured in any profile: #{orphaned.sort.join(", ")}" unless orphaned.empty?

  undefined = configured.reject do |name|
    found = software_candidates(name).find { |path| File.file?(path) }
    found && File.executable?(found)
  end
  abort "configured in profiles.rb but no runnable software definition found (missing or not executable): #{undefined.sort.join(", ")}" unless undefined.empty?
end

PROFILE_FILE = File.expand_path("#{ENV["HOME"]}/.config/dotfiles/profile").freeze
def _resolve_profile
  @current_profile ||= begin
    unless File.exist?(PROFILE_FILE)
      abort <<~MSG
        No profile is configured.

        Create #{PROFILE_FILE} with a single profile name in it:

            mkdir -p #{File.dirname(PROFILE_FILE)}
            echo [insert your profile name here] > #{PROFILE_FILE}

        Available profiles: #{PROFILES.keys.join(", ")}
      MSG
    end

    name = File.read(PROFILE_FILE).strip

    unless PROFILES.key?(name)
      abort "#{PROFILE_FILE} names an unknown profile #{name.inspect}. " \
            "Available profiles: #{PROFILES.keys.join(", ")}"
    end

    name
  end
end
