require 'pathname'

require_relative './common'

def brew(formula)
  Kernel.system "brew ls --versions #{formula} > /dev/null"
  system "brew install #{formula}" unless $?.success?
end

def link(from, to)
  to_path = "#{ENV["HOME"]}/#{to}"

  dirname = Pathname.new(to_path).dirname.to_s
  system "/bin/mkdir", "-p", dirname unless Dir.exists?(dirname)

  system "ln -sf #{__dir__}/../config/#{from} #{to_path}"
end
