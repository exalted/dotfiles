require_relative '../common'

def setup
  ohai "Initial setup…"
  Create.bash_profile
  Create.bashrc

  ohai "Ready!"
  puts
end

def cleanup
  ohai "Cleaning up…"
  Kernel.system "brew cleanup"

  ohai "All good."
  puts
end

module Create
  def self.bash_profile
    File.open("#{ENV["HOME"]}/.bash_profile", 'w') do |f|
      f << <<-EOF
# This file is generated automatically and will be overridden every time
# `dotfiles` is run. So, do yourself a favor and don't modify it manually or
# you will be upset!

# (Ref.: http://www.joshstaiger.org/archives/2005/07/bash_profile_vs.html)
source $HOME/.bashrc
EOF
    end
  end

  def self.bashrc
    File.open("#{ENV["HOME"]}/.bashrc", 'w') do |f|
      f << <<-EOF
# This file is generated automatically and will be overridden every time
# `dotfiles` is run. So, do yourself a favor and don't modify it manually or
# you will be upset!

EOF
    end
  end
end
