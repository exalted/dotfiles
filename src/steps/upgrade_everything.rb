require_relative '../common'

def upgrade_everything
  ohai "Upgrading existing software…"
  Upgrade.brew
  Upgrade.cask
  Upgrade.mas
  # TODO: these are not system-wide enough to belong here, so consider moving
  #       them out (read "better idea" section of the NOTE in `software/atom.rb`)
  #       and replace with something like `Upgrade.existing`.
  Upgrade.gibo
  Upgrade.apm

  ohai "Upgrade successful!"
  puts
end

module Upgrade
  def self.brew
    system "brew upgrade"
  end

  def self.cask
    system "brew cask upgrade"
  end

  def self.mas
    puts "Updating App Store Applications…"
    system "mas upgrade"
  end

  def self.gibo
    return unless cmd_exists?('gibo')
    puts "Updating gitignore boilerplates…"
    system "gibo --upgrade"
  end

  def self.apm
    return unless cmd_exists?('apm')
    puts "Updating Atom packages…"
    system "apm upgrade --no-confirm"
  end
end
