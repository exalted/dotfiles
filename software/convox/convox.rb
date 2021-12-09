#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

unless cmd_exists?('convox')
  # https://docsv2.convox.com/introduction/installation#os-x
  Kernel.system "curl -fsSL https://convox.com/cli/macos/convox -o /tmp/convox"
  Kernel.system "sudo mv /tmp/convox /usr/local/bin/convox"
  Kernel.system "sudo chown root /usr/local/bin/convox"
  Kernel.system "sudo chmod 755 /usr/local/bin/convox"
end

debounce { Kernel.system "convox update" }

bash_source_relative
