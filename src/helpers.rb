require 'pathname'
require 'fileutils'

require_relative './common'

def brew(formula)
  return if Kernel.system "brew ls --versions #{formula} > /dev/null"
  system "brew install #{formula}"
end

def mas(app_id, name)
  return if File.exists? "/Applications/#{name}.app"
  system "mas install #{app_id}"
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

def login_item(name, hidden: false)
  # ref: http://hints.macworld.com/article.php?story=20111226075701552
  system "osascript -e 'tell application \"System Events\" to "\
         "make login item at end with properties "\
         "{path:\"/Applications/#{name}.app\", hidden:#{hidden}}' > /dev/null"
end
