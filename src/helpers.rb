require 'pathname'
require 'fileutils'

require_relative './common'

def debounce(period: '1h')
  seconds = period.scan(/(\d+)([smhd])/).sum { |n, u| n.to_i * { 's' => 1, 'm' => 60, 'h' => 3600, 'd' => 86_400 }[u] }
  loc = Kernel.caller_locations.first
  key = "#{loc.path}:#{loc.lineno}".gsub(%r{[^\w.-]}, '_')
  marker = File.expand_path("#{ENV["HOME"]}/.cache/dotfiles/debounce/#{key}")

  return if File.exist?(marker) && (Time.now - File.mtime(marker)) < seconds

  yield

  FileUtils.mkdir_p(File.dirname(marker))
  FileUtils.touch(marker)
end

def brew(formula)
  return if Kernel.system "brew list --formula #{formula} > /dev/null"
  system "brew install --yes --formula #{formula}"
end

def cask(token)
  return if Kernel.system "brew list --cask #{token} > /dev/null"
  system "brew install --yes --cask #{token}"
end

def mas(app_id)
  return if Kernel.system "mas list | cut -f 1 -d' ' -s | grep ^#{app_id}$ > /dev/null"
  system "mas install #{app_id}"
end

def install(name, message)
  return if app_installed?(name)
  warn message
end

# Given a source path, prefer a sibling carrying the active profile just before
# the final extension (appended when there is none), falling back to the path
# as-is. Keeping the extension last means editors/formatters still recognize the
# variant's type (e.g. settings.<profile>.json stays JSON), and a single generic
# call site can ship per-profile variants without any conditional:
#   config       -> config.<profile>       || config
#   foo.txt      -> foo.<profile>.txt       || foo.txt
#   foo.bar.md   -> foo.bar.<profile>.md    || foo.bar.md
def profile_specific(path)
  ext = File.extname(path)
  candidate = "#{path[0...(path.length - ext.length)]}.#{_resolve_profile}#{ext}"
  File.exist?(candidate) ? candidate : path
end

def link(src, dest, backup: false)
  src = profile_specific(src)
  abort "#{src}: No such file or directory" unless File.exist? src

  if backup && File.exist?(dest)
    dest_backup = "#{dest}.backup"
    FileUtils.copy_file(dest, dest_backup, preserve: true) unless File.exist?(dest_backup)
  end

  FileUtils.mkdir_p Pathname.new(dest).dirname
  FileUtils.ln_sf src, dest
end

def link_relative(src, dest, backup: false)
  link(
    File.absolute_path("#{Pathname.new(Kernel.caller_locations.last.path).dirname}/#{src}"),
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
  path = profile_specific(path)
  abort "#{path}: No such file" unless File.file? path
  if File.readlines("#{ENV["HOME"]}/.bashrc.dotfiles").grep(/^#{"source #{path}"}$/).size == 0
    File.open("#{ENV["HOME"]}/.bashrc.dotfiles", 'a') { |f| f.puts "\n#{"source #{path}"}" }
  end
end

def bash_source_relative(name = nil)
  name = name ? "#{name}.bashrc" : 'bashrc'

  bash_source(
    File.absolute_path "#{Pathname.new(Kernel.caller_locations.last.path).dirname}/#{name}"
  )
end
