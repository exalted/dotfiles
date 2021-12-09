#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

# Read more: $(brew --prefix)/opt/sleepwatcher/ReadMe.rtf

brew 'sleepwatcher'

link_to_home_relative 'sleep', '.sleep'
link_to_home_relative 'wakeup', '.wakeup'

unless Kernel.system "brew services list | grep -E 'sleepwatcher\s+started' > /dev/null"
  Kernel.system "brew services start sleepwatcher"
end
