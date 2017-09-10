require 'pathname'
require 'fileutils'

require_relative './common'

def brew(formula)
  return if Kernel.system "brew ls --versions #{formula} > /dev/null"
  system "brew install #{formula}"
end

def link(src, dest, backup: false)
  src = "#{__dir__}/../dotfiles/#{src}"
  dest = "#{ENV["HOME"]}/#{dest}"

  if backup && File.exists?(dest)
    dest_backup = "#{dest}.backup"
    FileUtils.copy_file(dest, dest_backup, preserve: true) unless File.exists?(dest_backup)
  end

  FileUtils.mkdir_p Pathname.new(dest).dirname
  FileUtils.ln_sf src, dest
end
