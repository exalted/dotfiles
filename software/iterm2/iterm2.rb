#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

cask 'iterm2'

# TODO: save its settings

# https://iterm2.com/documentation-shell-integration.html
Kernel.system "curl -L https://iterm2.com/shell_integration/bash -o #{__dir__}/bashrc"

bash_source_relative
