#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

brew 'switchaudio-osx'

Kernel.system "brew tap mvp/uhubctl https://github.com/mvp/uhubctl"
brew 'uhubctl'

bash_source_relative
