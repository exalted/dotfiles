#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

# Default version is set in `software/node/bashrc` via `PATH`
brew 'node'     # Latest (a.k.a. "Current")
brew 'node@18'  # LTS
brew 'node@16'  # Maintenance
brew 'node@14'  # Maintenance
# Older versions:
brew 'node@12'

#
# Node Version Manager
#
brew 'nvm'
Kernel.system "mkdir -p #{ENV["HOME"]}/.nvm"
Kernel.system "nvm alias default system"  # make sure nvm to not "interfere" unless explicitely `nvm use`'d

link_to_home_relative 'npmrc', '.npmrc'

bash_source_relative
