require 'pathname'
require 'fileutils'

require_relative './common'

# TODO: remember last execution time, and run again only after a certain
# period of time has passed (e.g. 1 hour)
def debounce
  yield
end

def brew(formula)
  return if Kernel.system "brew list #{formula} &> /dev/null"
  system "brew install #{formula}"
end

def cask(token)
  return if Kernel.system "brew cask list #{token} &> /dev/null"
  system "brew cask install #{token}"
end

def mas(app_id)
  return if Kernel.system(
    "mas list | cut -f 1 -d' ' -s | grep ^#{app_id}$ > /dev/null",
  )
  system "mas install #{app_id}"
end

def link(src, dest, backup: false)
  abort "#{src}: No such file or directory" unless File.exists? src

  if backup && File.exists?(dest)
    dest_backup = "#{dest}.backup"
    (
      FileUtils.copy_file(dest, dest_backup, preserve: true)
    ) unless File.exists?(dest_backup)
  end

  FileUtils.mkdir_p Pathname.new(dest).dirname
  FileUtils.ln_sf src, dest
end

def link_relative(src, dest, backup: false)
  link(
    File.absolute_path(
      "#{Pathname.new(Kernel.caller_locations.last.path).dirname}/#{src}",
    ),
    dest,
    backup: backup
  )
end

def link_to_home(src, dest, backup: false)
  link(src, "#{ENV["HOME"]}/#{dest}", backup: backup)
end

def link_to_home_relative(src, dest, backup: false)
  link_relative(src, "#{ENV["HOME"]}/#{dest}", backup: backup)
end

def bash_source(path)
  abort "#{path}: No such file or directory" unless File.exists? path
  if File.readlines("#{ENV["HOME"]}/.bashrc").grep(/^#{"source #{path}"}$/).size == 0
    File.open("#{ENV["HOME"]}/.bashrc", 'a') { |f| f.puts "\n#{"source #{path}"}" }
  end
end

def bash_source_relative(name = nil)
  name = name ? "#{name}.bashrc" : 'bashrc'

  bash_source(
    File.absolute_path(
      "#{Pathname.new(Kernel.caller_locations.last.path).dirname}/#{name}",
    ),
  )
end
