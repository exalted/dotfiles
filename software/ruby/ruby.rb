#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

# https://www.fngtps.com/2018/rails-development-environment/

brew 'rbenv'
brew 'ruby-build'

bash_source_relative

link_to_home_relative 'gemrc', '.gemrc'
link_to_home_relative 'rspec', '.rspec'
