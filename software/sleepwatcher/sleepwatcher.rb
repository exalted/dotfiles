#!/usr/bin/env ruby
require_relative '../../src/helpers'

# Read more: $(brew --prefix)/opt/sleepwatcher/ReadMe.rtf

brew 'sleepwatcher'

link_to_home_relative 'sleep', '.sleep'
link_to_home_relative 'wakeup', '.wakeup'

unless system "brew services list | grep -E 'sleepwatcher\s+started' > /dev/null"
  system "brew services start sleepwatcher"
end
