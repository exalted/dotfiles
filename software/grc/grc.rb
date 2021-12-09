#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

brew 'grc'

disable=['diff']
enable=['env']

# We want to enable/disable some of the "colourifications"
# (see `$(brew --prefix)/etc/grc.sh` for defaults)
Kernel.system "echo \"export GRC_ALIASES=true\" > \"#{__dir__}/bashrc\""
Kernel.system "cat \"$(brew --prefix)/etc/grc.sh\" >> \"#{__dir__}/bashrc\""
for d in disable do
  Kernel.system "sed -i '' -E \"s/^[[:space:]]*#?[[:space:]]*(alias #{d}='colourify #{d}')$/    # alias #{d}='colourify #{d}'/g\" \"#{__dir__}/bashrc\""
end
for e in enable do
  Kernel.system "sed -i '' -E \"s/^[[:space:]]*#?[[:space:]]*(alias #{e}='colourify #{e}')$/    alias #{e}='colourify #{e}'/g\" \"#{__dir__}/bashrc\""
end

bash_source_relative
