require_relative '../common'
require_relative '../helpers'

def install_homebrew
  unless cmd_exists('brew')
    system "/usr/bin/ruby -e \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)\""
  end

  brew 'mas'
end
