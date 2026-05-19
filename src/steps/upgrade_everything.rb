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
    # system "brew upgrade --greedy"
    system "brew upgrade --greedy-latest"
  end

  def self.appstore
    ohai "Upgrading App Store Applications…"
    system "mas upgrade"
  end
end
