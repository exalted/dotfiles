require_relative '../common'

def upgrade_everything
  ohai "Upgrading existing software..."
  system 'brew upgrade'

  ohai "Upgrade successful!"
  puts
end
