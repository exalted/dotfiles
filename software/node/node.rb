#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

brew 'node'     # this is the latest and greatest (aka "current")
brew 'node@14'  # this is the current LTS, also "default" in my system (see `software/node/bashrc`)
brew 'node@12'  # previous version still might be worth keeping around

link_to_home_relative 'npmrc', '.npmrc'

bash_source_relative
