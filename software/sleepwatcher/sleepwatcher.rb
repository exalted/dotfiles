#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

# Read more: /usr/local/opt/sleepwatcher/ReadMe.rtf

brew 'sleepwatcher'

link_to_home_relative 'sleep', '.sleep'
link_to_home_relative 'wakeup', '.wakeup'

Kernel.system "brew services start sleepwatcher"
