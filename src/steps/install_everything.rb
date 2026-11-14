require_relative '../common'

def install_everything
  ohai "Installing any new software…"

  software_manifest.each do |name|
    file = resolve_software(name)
    puts "#{Tty.blue}>#{Tty.bold} #{name}#{Tty.reset}"

    started_at = Time.now
    system file
    elapsed = Time.now - started_at
    puts "#{Tty.cyan}(Took #{elapsed.round(2)}s)#{Tty.reset}" if elapsed > 1
  end
end
