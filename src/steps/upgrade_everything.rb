require 'json'
require 'optparse'
require_relative '../common'

def upgrade_everything
  options = Upgrade.parse_flags
  Upgrade.macos if options[:with_macos]
  Upgrade.homebrew
  Upgrade.appstore if options[:with_appstore]
end

module Upgrade
  def self.parse_flags
    options = { with_macos: false, with_appstore: false }
    OptionParser.new do |opts|
      opts.on("--with-macos") { options[:with_macos] = true }
      opts.on("--with-appstore") { options[:with_appstore] = true }
    end.parse(ARGV.dup)
    options
  end

  def self.macos
    ohai "Upgrading macOS software…"
    system "softwareupdate --install --all"
  end

  def self.homebrew
    ohai "Upgrading software installed via Homebrew…"
    entry_scripts = software_manifest.map { |name| resolve_software(name) }
    # Must use the same greedy flags as the upgrade below, or it asks about
    # casks the upgrade skips (or misses ones it quits).
    outdated = `brew outdated --cask --greedy-latest --quiet`.lines.map(&:strip)
    confirm_quits(confirm_before_quit_casks(entry_scripts) & outdated)
    # system "brew upgrade --greedy"
    system "brew upgrade --yes --greedy-latest"
  end

  # Brew quits a running cask app to replace its bundle, which loses any state
  # the app does not restore. Waits for Enter so that work can be finished.
  def self.confirm_quits(casks)
    casks.each do |cask|
      next unless quit_bundle_ids(cask).any? { |bundle_id| running?(bundle_id) }
      print "#{Tty.bold}#{cask}#{Tty.reset} is running and brew will quit it to upgrade. " \
            "Finish your work in it, then press Enter (Ctrl-C aborts): "
      $stdin.gets
    end
  end

  # Matched on the text, not run: running an entry script installs and links
  # things. Only a one-line call with a literal name matches.
  CONFIRM_BEFORE_QUIT_CASK = /^\s*cask\s+['"]([^'"]+)['"]\s*,\s*confirm_before_quit:\s*true\b/.freeze

  def self.confirm_before_quit_casks(entry_scripts)
    entry_scripts.select { |file| file.end_with?(".rb") }
                 .flat_map { |file| File.read(file).scan(CONFIRM_BEFORE_QUIT_CASK).flatten }
                 .uniq
  end

  # The app IDs the cask's own `uninstall quit:` stanza names: exactly what
  # brew quits. The brew pty wrapper merges stderr into stdout, so skip to the
  # JSON.
  def self.quit_bundle_ids(cask)
    output = `brew info --cask --json=v2 #{cask}`
    json = output[(output.index("{") || output.length)..-1]
    artifacts = JSON.parse(json).fetch("casks").first.fetch("artifacts")
    artifacts.flat_map { |artifact| Array(artifact["uninstall"]) }
             .flat_map { |stanza| Array(stanza["quit"]) }
  rescue JSON::ParserError, KeyError, NoMethodError
    warn "#{cask}: could not read which app brew quits; it gets no confirmation"
    []
  end

  def self.running?(bundle_id)
    `osascript -e 'application id "#{bundle_id}" is running' 2>/dev/null`.strip == 'true'
  end

  def self.appstore
    ohai "Upgrading App Store Applications…"
    system "mas upgrade"
  end
end
