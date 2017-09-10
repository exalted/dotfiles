require_relative '../common'
require_relative '../helpers'

def install_homebrew
  return if cmd_exists('brew')
  system "/usr/bin/ruby -e \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)\""
  system 'brew tap caskroom/cask'
  brew 'mas'
end
