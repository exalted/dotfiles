require_relative '../common'

# TODO: instead of searching executables by file extension, execute all files
#       that are actually executable
def install_everything
  ohai "Installing new software…"
  Dir.glob("#{__dir__}/../../software/**/*.{sh,rb,py,js}") { |file| system file }

  ohai "New software installation successful!"
  puts
end
