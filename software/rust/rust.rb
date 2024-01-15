#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

brew 'rustup-init'

if cmd_exists?('rustup')
  system "rustup update --no-self-update"
else
  system "rustup-init --verbose -y --component rust-analyzer --no-modify-path"
end

bash_source_relative
