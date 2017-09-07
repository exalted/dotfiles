#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../src/helpers'

brew 'git'
brew 'hub'
brew 'gibo'

link 'gitconfig', '.config/git/config'
link 'gitattributes', '.config/git/attributes'
