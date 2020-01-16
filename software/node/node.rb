#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

brew 'node'
brew 'node@8'
brew 'node@10'
brew 'node@12'

link_to_home_relative 'npmrc', '.npmrc'

bash_source_relative
