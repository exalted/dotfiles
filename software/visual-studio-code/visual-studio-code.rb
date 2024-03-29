#!/usr/bin/env ruby
require_relative '../../src/helpers'

cask 'visual-studio-code'

link_to_home_relative(
  'settings.json',
  'Library/Application Support/Code/User/settings.json',
)
link_to_home_relative(
  'keybindings.json',
  'Library/Application Support/Code/User/keybindings.json',
)

module Extension
  def self.install(name)
    return if system "code --list-extensions | grep ^#{name}$ > /dev/null"
    system "code --install-extension #{name}"
  end
end

EXTENSIONS_FILE="#{__dir__}/extensions.autogenerated"

File.readlines(EXTENSIONS_FILE).each do |package|
  Extension.install package.chomp
end

system "code --list-extensions | sort > #{EXTENSIONS_FILE}"
