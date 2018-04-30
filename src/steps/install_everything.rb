require_relative '../common'

# TODO: instead of searching executables by file extension, execute all files
#       that are actually executable (although there may be other executables
#       that are part of a software, but not software itself (e.g.,
#       `software/git/bin/git-*`), so only execute executable `software/foo`s
#       or `software/foo/foo`s, and nothing else.)
def install_everything
  ohai "Installing new software…"
  Dir.glob("#{__dir__}/../../software/**/*.{sh,rb,py,js}") { |file| system file }

  ohai "New software installation successful!"
  puts
end
