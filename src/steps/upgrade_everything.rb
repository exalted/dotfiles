require_relative '../common'

def upgrade_everything
  ohai "Upgrading existing software..."
  system "brew upgrade"
  system "gibo --upgrade" if cmd_exists('gibo')

  ohai "Upgrade successful!"
  puts
end
