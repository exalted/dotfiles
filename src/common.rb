# Inspired by https://github.com/Homebrew/install/blob/63e779e5d6cc1cd7ddefda9c0eb404687d1a1c79/install

# Keep this file — and everything bin/dotfiles loads before software/ruby runs —
# compatible with macOS's stock /usr/bin/ruby (2.6). A brand new Mac has nothing
# newer on PATH, and the brewed ruby doesn't exist yet at this point, so 2.7+
# niceties (filter_map, tally, `_1`, …) blow up mid-bootstrap on exactly the
# machine this script exists to set up. Verify with: /usr/bin/ruby -c <file>
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

# Homebrew's prefix and PATH as software/homebrew/shellenv.sh leaves them: the
# one place that knows where Homebrew lives, which every shell and launchd job
# sources too. Returns [prefix, path]; prefix is nil without Homebrew.
def _homebrew_env
  shellenv = File.expand_path("#{__dir__}/../software/homebrew/shellenv.sh")
  out = `/bin/sh -c '. "$1" >/dev/null 2>&1; printf "%s\\n%s" "${HOMEBREW_PREFIX:-}" "$PATH"' sh "#{shellenv}"`
  prefix, path = out.split("\n", 2)
  [prefix.to_s.empty? ? nil : prefix, path]
end

# Puts Homebrew on this process's PATH and sets HOMEBREW_PREFIX, which entry
# scripts inherit. A first run on a new Mac starts from a shell without either,
# and Homebrew's installer cannot change the PATH of the process that ran it.
def _load_homebrew_env
  prefix, path = _homebrew_env
  return unless prefix
  ENV["HOMEBREW_PREFIX"] = prefix
  ENV["PATH"] = path
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
# * The wrapper is the tracked script software/homebrew/bin/brew. Only this
#   process and the entry scripts it starts get it on PATH; shells never do.
# * Read the prefix from HOMEBREW_PREFIX (brew_prefix), never from the wrapper:
#   `brew --prefix` exits before brew.sh reaches its sudo reset, so it gains
#   nothing from the pty, and the wrapper would merge any brew warning into it.
def _shadow_brew_with_pty
  wrapper_dir = "#{__dir__}/../software/homebrew/bin"
  # Keeps a copy that lost its exec bit (a ZIP download, core.fileMode=false) working.
  File.chmod(0755, "#{wrapper_dir}/brew")
  ENV["PATH"] = "#{wrapper_dir}:#{ENV["PATH"]}"
end

SOFTWARE_DIR = File.expand_path("#{__dir__}/../software").freeze
SOFTWARE_EXTENSIONS = %w[rb sh py js].freeze

def software_candidates(name)
  stems =
    if name.include?("/")
      ["#{SOFTWARE_DIR}/#{name}"]
    else
      ["#{SOFTWARE_DIR}/#{name}", "#{SOFTWARE_DIR}/#{name}/#{name}"]
    end
  stems.flat_map { |stem| SOFTWARE_EXTENSIONS.map { |ext| "#{stem}.#{ext}" } }
end

def resolve_software(name)
  candidates = software_candidates(name)
  relative = ->(path) { path.sub("#{SOFTWARE_DIR}/", "software/") }

  found = candidates.find { |path| File.file?(path) }
  abort "profiles.rb lists #{name.inspect}, but no entry script exists " \
        "(looked for: #{candidates.map(&relative).join(", ")})" unless found
  abort "#{relative.call(found)} is listed in profiles.rb but is not " \
        "executable — run `chmod +x` on it" unless File.executable?(found)

  found
end

def software_manifest
  (COMMON + PROFILES.fetch(_resolve_profile)).sort
end

# Only executable files count as entry scripts — that's resolve_software's
# contract, and it's what tells an installer apart from a support file that
# sits beside it (e.g. finicky/finicky.js, Finicky's config).
def _defined_software_names
  ext = /\.(#{SOFTWARE_EXTENSIONS.join("|")})\z/
  entry = ->(path) { File.file?(path) && File.executable?(path) && File.basename(path) =~ ext }

  Dir.children(SOFTWARE_DIR).sort.flat_map do |name|
    path = "#{SOFTWARE_DIR}/#{name}"
    next name.sub(ext, "") if entry.call(path)
    next [] unless File.directory?(path)
    Dir.children(path).sort.map do |child|
      next unless entry.call("#{path}/#{child}")
      stem = child.sub(ext, "")
      stem == name ? name : "#{name}/#{stem}"
    end.compact
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
