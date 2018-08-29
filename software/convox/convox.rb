#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

unless cmd_exists?('convox')
  Kernel.system "curl -Ls https://convox.com/install/osx.zip > /tmp/convox.zip"
  Kernel.system "unzip /tmp/convox.zip -d /usr/local/bin"
  Kernel.system "rm /tmp/convox.zip"
end

# TODO: update convox only if not updated in the last hour or so
Kernel.system "convox update"
