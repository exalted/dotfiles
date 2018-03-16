#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

brew 'ack'

link_to_home_relative 'ackrc', '.ackrc'
