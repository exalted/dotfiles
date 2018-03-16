#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

brew 'colordiff'
brew 'diff-so-fancy'

bash_source_relative 'diff.bashrc'
