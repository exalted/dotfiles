#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

brew 'grc'

# We don't want to colourify everything (see `/usr/local/etc/grc.bashrc`)
Kernel.system "cat /usr/local/etc/grc.bashrc | grep -v 'alias diff=' > #{__dir__}/grc.bashrc"

bash_source_relative
