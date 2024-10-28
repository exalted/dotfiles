require_relative '../common'

def upgrade_everything
  ohai "Upgrading existing software…"
  Upgrade.brew
  Upgrade.mas

  ohai "Upgrade successful!"
  puts
end

module Upgrade
  def self.brew
    system "brew upgrade --greedy"
  end

  def self.mas
    puts "Updating App Store Applications…"
    system "mas upgrade"
  end
end
