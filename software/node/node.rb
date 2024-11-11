#!/usr/bin/env ruby
require_relative '../../src/helpers'

# Default version is set in `software/node/bashrc` via `PATH`
brew 'node'
brew 'node@18'
# brew 'node@16'
# brew 'node@14'
# brew 'node@12'

#
# Node Version Manager
#
brew 'nvm'
system "mkdir -p #{ENV["HOME"]}/.nvm"
# See `brew info nvm` to learn about how to load nvm:
LOAD_NVM_CMD = 'export NVM_DIR="$HOME/.nvm" && [ -s "/opt/homebrew/opt/nvm/nvm.sh" ] && \. "/opt/homebrew/opt/nvm/nvm.sh"'
system "#{LOAD_NVM_CMD} && nvm alias default system" # make sure nvm to not "interfere" unless explicitely `nvm use`'d

link_to_home_relative 'npmrc', '.npmrc'

bash_source_relative
