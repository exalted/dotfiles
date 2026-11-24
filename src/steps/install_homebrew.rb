require_relative '../common'
require_relative '../helpers'

def install_homebrew
  _load_homebrew_env
  return if cmd_exists?('brew')

  system '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
  _load_homebrew_env
  system 'brew tap homebrew/cask-versions'
  system 'brew tap homebrew/cask-drivers'
end
