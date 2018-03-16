require_relative '../common'
require_relative '../helpers'

def install_homebrew
  # Don't attempt to install if already installed
  return if cmd_exists?('brew')
  system "/usr/bin/ruby -e \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)\""
  system 'brew tap caskroom/cask'
  system 'brew tap caskroom/drivers'
end
