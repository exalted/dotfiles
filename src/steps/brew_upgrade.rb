require_relative '../common'

def brew_upgrade
  ohai "Upgrading existing software..."
  system 'brew upgrade'

  ohai "Upgrade successful!"
  puts
end
