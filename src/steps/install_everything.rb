require_relative '../common'

SOFTWARE_DIR = File.expand_path("#{__dir__}/../../software").freeze
SOFTWARE_EXTENSIONS = %w[rb sh py js].freeze

def resolve_software(name)
  stems =
    if name.include?("/")
      ["#{SOFTWARE_DIR}/#{name}"]
    else
      ["#{SOFTWARE_DIR}/#{name}", "#{SOFTWARE_DIR}/#{name}/#{name}"]
    end
  candidates = stems.flat_map { |stem| SOFTWARE_EXTENSIONS.map { |ext| "#{stem}.#{ext}" } }
  relative = ->(path) { path.sub("#{SOFTWARE_DIR}/", "software/") }

  found = candidates.find { |path| File.file?(path) }
  abort "profiles.rb lists #{name.inspect}, but no entry script exists " \
        "(looked for: #{candidates.map(&relative).join(", ")})" unless found
  abort "#{relative.call(found)} is listed in profiles.rb but is not " \
        "executable — run `chmod +x` on it" unless File.executable?(found)

  found
end

def install_everything
  ohai "Installing any new software…"

  for name in BOOTSTRAP
    file = resolve_software(name)
    system file
  end

  manifest = (COMMON + PROFILES.fetch(@current_profile)).sort
  manifest.each do |name|
    file = resolve_software(name)
    puts "#{Tty.blue}>#{Tty.bold} #{name}#{Tty.reset}"

    started_at = Time.now
    system file
    elapsed = Time.now - started_at
    puts "#{Tty.cyan}(Took #{elapsed.round(2)}s)#{Tty.reset}" if elapsed > 1
  end
end
