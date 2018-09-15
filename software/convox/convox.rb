#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

unless cmd_exists?('convox')
  # https://convox.com/docs/installation/#os-x
  Kernel.system "curl -fsSL https://convox.com/cli/osx/convox -o /tmp/convox"
  Kernel.system "mv /tmp/convox /usr/local/bin/convox"
  Kernel.system "chmod 755 /usr/local/bin/convox"
end

# TODO: update convox only if not updated in the last hour or so
Kernel.system "convox update"
