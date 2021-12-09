require_relative '../common'

def upgrade_everything
  ohai "Upgrading existing software…"
  Upgrade.brew
  Upgrade.mas
  # TODO: these are not system-wide enough to belong here, so consider moving
  #       them out.
  Upgrade.gibo

  ohai "Upgrade successful!"
  puts
end

module Upgrade
  def self.brew
    system "brew upgrade --cask --greedy --greedy-latest --greedy-auto-updates"
  end

  def self.mas
    puts "Updating App Store Applications…"
    system "mas upgrade"
  end

  def self.gibo
    return unless cmd_exists?('gibo')
    puts "Updating gitignore boilerplates…"
    system "gibo update"
  end
end
