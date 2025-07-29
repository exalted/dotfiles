require_relative '../common'

def upgrade_everything
  Upgrade.os
  Upgrade.brew
  Upgrade.mas
end

module Upgrade
  def self.os
    ohai "Upgrading macOS software…"
    system "softwareupdate --install --all"
  end

  def self.brew
    ohai "Upgrading software installed via Homebrew…"
    system "brew upgrade --greedy"
  end

  def self.mas
    ohai "Upgrading App Store Applications…"
    system "mas upgrade"
  end
end
