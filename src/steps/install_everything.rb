require_relative '../common'

def install_everything
  ohai "Installing new software..."
  Dir.glob("#{__dir__}/../../software/*") { |file| system file }

  ohai "New software installation successful!"
  puts
end
