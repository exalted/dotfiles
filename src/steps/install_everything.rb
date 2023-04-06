require_relative '../common'

# TODO: instead of searching executables by file extension, execute all files
#       that are actually executable (although there may be other executables
#       that are part of a software, but not software itself (e.g.,
#       `software/git/bin/git-*`), so only execute executable `software/foo`s
#       or `software/foo/foo`s, and nothing else.)
def install_everything
  # order of these matter!
  priority = [
    'homebrew/homebrew.rb',
  ].map { |x| "#{__dir__}/../../software/#{x}" }

  ohai "Installing new software…"

  for file in priority
    system file
  end

  for file in Dir.glob("#{__dir__}/../../software/**/*.{sh,rb,py,js}") - priority
    system file if File.executable? file
  end

  ohai "New software installation successful!"
  puts
end
