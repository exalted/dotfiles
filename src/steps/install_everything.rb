require_relative '../common'

def install_everything
  ohai "Installing new software..."
  Dir.glob("#{__dir__}/../../software/*") { |file| system file }

  ohai "Installation successful!"
  puts
end
