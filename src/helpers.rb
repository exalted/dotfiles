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

# Memoized because every call is a `brew` process start, which is not cheap.
def brew_prefix
  @brew_prefix ||= `brew --prefix`.strip
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
#
# This is a convention of *this repo*, so it is applied only by the `*_relative`
# resolvers, which are the ones that know the path is repo-owned. Applying it in
# `link`/`bash_source` also probed absolute third-party paths (Homebrew's
# bash_completion.sh, the Stripe CLI's completion), where a `*.<profile>.*` file
# dropped by that tool would silently be picked up instead of the real one.
def profile_specific(path)
  ext = File.extname(path)
  candidate = "#{path[0...(path.length - ext.length)]}.#{_resolve_profile}#{ext}"
  File.exist?(candidate) ? candidate : path
end

# Move `path` aside to `path.backup`, once. A second run must not overwrite an
# existing backup: that would replace the user's original with whatever this
# repo has since put in its place.
def _backup_once(path)
  dest_backup = "#{path}.backup"
  FileUtils.copy_file(path, dest_backup, preserve: true) unless File.exist?(dest_backup)
end

# This checkout. A symlink under $HOME resolving inside it was put there by a
# previous dotfiles run, so its content is ours, not the user's.
DOTFILES_DIR = File.expand_path("#{__dir__}/..").freeze
def _links_into_repo?(path)
  File.exist?(path) && File.realpath(path).start_with?("#{DOTFILES_DIR}/")
end

def link(src, dest, backup: false)
  abort "#{src}: No such file or directory" unless File.exist? src

  _backup_once(dest) if backup && File.exist?(dest)

  FileUtils.mkdir_p Pathname.new(dest).dirname
  FileUtils.ln_sf src, dest
end

def link_relative(src, dest, backup: false)
  link(
    profile_specific(File.absolute_path("#{Pathname.new(Kernel.caller_locations.last.path).dirname}/#{src}")),
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

# `link` is for files only: on a re-run, ln_sf follows the existing link to a
# directory and puts a second link *inside* it, i.e. inside this repo. `-n`
# replaces the link itself instead. A real directory is never replaced, because
# what it holds may be newer than the repo.
def link_directory(src, dest)
  abort "#{src}: No such directory" unless File.directory? src
  if File.exist?(dest) && !File.symlink?(dest)
    abort "#{dest} exists and is not a link. Move what it holds into #{src}, then run again."
  end

  FileUtils.mkdir_p Pathname.new(dest).dirname
  system '/bin/ln', '-sfn', src, dest, exception: true
end

# Ensure `path` begins with `line`, preserving whatever content it already had
# beneath it (backing that up once first, like `link`'s backup: option). Used
# to add an `Include` directive to a file dotfiles doesn't own outright — e.g.
# ~/.ssh/config — instead of symlinking over it and discarding pre-existing
# entries.
#
# OpenSSH (and similarly other Include-supporting configs) keeps the *first*
# value it sees for a given keyword, so the line has to land above any
# conflicting entry already in the file for ours to win.
def ensure_first_line(path, line, backup: false, mode: nil)
  path = File.expand_path(path)
  FileUtils.mkdir_p Pathname.new(path).dirname

  # A symlink here is most likely a previous dotfiles version having linked a
  # whole file into place (e.g. ssh.rb used to symlink config.work straight
  # onto ~/.ssh/config). Writing "through" it, as File.write would, means
  # silently editing whatever it points at — which can be a file this repo
  # owns. So the link is replaced by a real file holding the same content, and
  # this function only ever edits `path` itself.
  #
  # Where that content comes from depends on where the link pointed:
  #
  # * Into this checkout — the previous version's own managed file. Inlining it
  #   would freeze a stale copy of a file we still update, and it isn't what the
  #   user lost anyway: that's in the `.backup` the same version left behind, so
  #   restore *that* and leave it in place as the backup it already is.
  # * Anywhere else — a config the user keeps elsewhere. Preserve it verbatim
  #   (backing it up first, like `link`'s backup: option).
  #
  # File.exist? is false for a dangling symlink, which is exactly the case that
  # must not reach copy_file: it follows the link and raises Errno::ENOENT,
  # aborting the whole run with a backtrace. A link left behind by a checkout
  # that has since moved is the likely way to get one.
  replaced_symlink = File.symlink?(path)
  ours = replaced_symlink && _links_into_repo?(path)
  preexisting_file = !replaced_symlink && File.exist?(path)

  existing =
    if ours
      File.exist?("#{path}.backup") ? File.read("#{path}.backup") : ''
    elsif File.exist?(path)
      File.read(path)
    else
      ''
    end

  if replaced_symlink
    _backup_once(path) if backup && !ours && File.exist?(path)
    FileUtils.rm(path)
  end

  # ssh refuses to read a config that is group- or other-writable, so the mode
  # of a file we create must not be left to the ambient umask (0002 gives 0664).
  # Creating it up front, before any File.write, is what makes the mode stick.
  File.open(path, File::WRONLY | File::CREAT, mode) {} if mode && !File.exist?(path)

  # Anywhere in the file counts as present, not just the first line. Prepending a
  # second copy of a line the user had already put further down (by hand, or
  # under a comment header they added later) would have every included file
  # parsed twice; where they chose to put it is theirs to decide.
  if existing.each_line.any? { |existing_line| existing_line.chomp == line }
    File.write(path, existing) if replaced_symlink
    return
  end

  # Only what was already there is worth keeping: a symlink's content is backed
  # up above, and the file `mode:` just created is empty — copying that over a
  # real backup, or making one out of it, is how a backup gets lost.
  _backup_once(path) if backup && preexisting_file

  File.write(path, existing.empty? ? "#{line}\n" : "#{line}\n\n#{existing}")
end

def ensure_first_line_at_home(dest, line, backup: false, mode: nil)
  ensure_first_line("#{ENV["HOME"]}/#{dest}", line, backup: backup, mode: mode)
end

# Append `line` to `path` unless it's already there. The comparison is literal,
# not a regex: a checkout or $HOME holding a regex metacharacter (`Dev+Tools`,
# `foo[1]`) would otherwise either never match — appending a duplicate on every
# run — or raise RegexpError and abort bin/dotfiles mid-install.
def ensure_line(path, line)
  return if File.exist?(path) && File.readlines(path, chomp: true).include?(line)
  File.open(path, 'a') { |f| f.puts "\n#{line}" }
end

def bash_source(path)
  abort "#{path}: No such file" unless File.file? path
  ensure_line "#{ENV["HOME"]}/.bashrc.dotfiles", "source #{path}"
end

def bash_source_relative(name = nil)
  name = name ? "#{name}.bashrc" : 'bashrc'

  bash_source(
    profile_specific(File.absolute_path("#{Pathname.new(Kernel.caller_locations.last.path).dirname}/#{name}"))
  )
end
