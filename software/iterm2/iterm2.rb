#!/usr/bin/env ruby
require_relative '../../src/helpers'

cask 'iterm2'

# https://iterm2.com/documentation-shell-integration.html
system "curl -fsSL https://iterm2.com/shell_integration/bash -o #{__dir__}/shell_integration"

bash_source_relative
