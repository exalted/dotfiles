#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

brew 'ripgrep'

bash_source_relative 'ripgrep.bashrc'
