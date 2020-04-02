require_relative '../common'

def setup
  ohai "Initial setup…"
  Setup.create_bash_profile
  Setup.create_temp_bashrc

  ohai "Ready!"
  puts
end

def wrapup
  ohai "Almost there…"
  Setup.save_bashrc

  ohai "All good."
  puts
end

def cleanup
  ohai "Cleaning up…"
  Kernel.system "brew cleanup"

  ohai "Clean as a whistle."
  puts
end

module Setup
  def self.create_bash_profile
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

  def self.create_temp_bashrc
    File.open("#{ENV["HOME"]}/.bashrc.dotfiles", 'w') do |f|
      f << <<-EOF
# This file is generated automatically and will be overridden every time
# `dotfiles` is run. So, do yourself a favor and don't modify it manually or
# you will be upset!

EOF
    end
  end

  def self.save_bashrc
    FileUtils.mv(
      "#{ENV["HOME"]}/.bashrc.dotfiles",
      "#{ENV["HOME"]}/.bashrc",
      force: true,
    )
  end
end
