#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

brew 'node@12'  # this is the version I set as "default" in my system (see `software/node/bashrc`)
brew 'node@14'  # this is the current LTS
brew 'node'     # this is the latest and greatest (aka "current")

link_to_home_relative 'npmrc', '.npmrc'

bash_source_relative
