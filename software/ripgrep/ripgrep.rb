#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

brew 'ripgrep'

link_to_home_relative 'ripgreprc', '.ripgreprc'

bash_source_relative
