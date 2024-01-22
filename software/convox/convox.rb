#!/usr/bin/env ruby
require_relative '../../src/helpers'

if cmd_exists?('convox')
  debounce { system "sudo convox update" }
else
  # https://docsv2.convox.com/introduction/installation#os-x
  # OR http://download.convox.com/cli/darwin/convox
  # OR https://convox.s3.amazonaws.com/cli/darwin/convox
  system "curl -fsSL https://convox.com/cli/macos/convox -o /tmp/convox"
  system "sudo mv /tmp/convox /usr/local/bin/convox"
  system "sudo chown root /usr/local/bin/convox"
  system "sudo chmod 755 /usr/local/bin/convox"
end

bash_source_relative
