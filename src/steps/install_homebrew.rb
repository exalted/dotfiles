require_relative '../common'

def install_homebrew
  return if cmd_exists('brew')
  system "/usr/bin/ruby -e \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)\""
end
