#!/usr/bin/env ruby
require_relative '../../src/helpers'

# Note: There are ruby versions here: `/System/Library/Frameworks/Ruby.framework/Versions/`

# https://www.fngtps.com/2018/rails-development-environment/

brew 'rbenv'
brew 'ruby-build'

bash_source_relative

link_to_home_relative 'gemrc', '.gemrc'
link_to_home_relative 'rspec', '.rspec'
