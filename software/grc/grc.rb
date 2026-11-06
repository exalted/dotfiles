#!/usr/bin/env ruby
require_relative '../../src/helpers'

brew 'grc'

disable=['diff']
# enable=['env']
enable=[]

# First off, enable "colourification" feature
system "echo \"export GRC_ALIASES=true\" > \"#{__dir__}/bashrc.bash\""
system "cat \"$(brew --prefix)/etc/grc.sh\" >> \"#{__dir__}/bashrc.bash\""

# Then disable/enable some of the specific "colourify-ications"
# (see `$(brew --prefix)/etc/grc.sh` for defaults)
for d in disable do
  system "sed -i '' -E \"s/^[[:space:]]*#?[[:space:]]*(alias #{d}='colourify #{d}')$/    # alias #{d}='colourify #{d}'/g\" \"#{__dir__}/bashrc.bash\""
end
for e in enable do
  system "sed -i '' -E \"s/^[[:space:]]*#?[[:space:]]*(alias #{e}='colourify #{e}')$/    alias #{e}='colourify #{e}'/g\" \"#{__dir__}/bashrc.bash\""
end

bash_source_relative
