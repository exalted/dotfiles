#!/usr/bin/env ruby
require_relative '../../src/helpers'

brew 'rustup'

if cmd_exists?('rustup')
  debounce(period: '1d') { system "rustup update --no-self-update" }
else
  system "rustup-init --verbose -y --component rust-analyzer --no-modify-path"
end

bash_source_relative
