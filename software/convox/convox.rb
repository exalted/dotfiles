#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

brew 'convox'

# For some reason Homebrew formula isn't usually up-to-date and
# even the official guide recommends `convox update` after `brew install`
# (ref.: https://convox.com/docs/installation/#homebrew)
Kernel.system "convox update"

bash_source_relative
