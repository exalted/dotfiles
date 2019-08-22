#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

unless cmd_exists?('convox')
  # https://convox.com/docs/installation/#os-x
  Kernel.system "curl -fsSL https://convox.com/cli/macos/convox -o /tmp/convox"
  Kernel.system "mv /tmp/convox /usr/local/bin/convox"
  Kernel.system "chmod 755 /usr/local/bin/convox"
end

debounce { Kernel.system "convox update" }

bash_source_relative
