#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

# Default version is set in `software/node/bashrc` via `PATH`
brew 'node'     # Latest (a.k.a. "current")
brew 'node@16'  # [Active] LTS
brew 'node@14'  # Maintenance [LTS]
# Older versions:
brew 'node@12'

link_to_home_relative 'npmrc', '.npmrc'

bash_source_relative
