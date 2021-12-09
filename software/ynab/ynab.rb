#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

# TODO: Automatically set it up on Download's folder instead of manually setting
# it up using macOS built-in "Folder Actions Setup" app.

# TODO: The technique below is copied from `software/mosaic.rb`, no bueno…

filename = "Fix UniCredit QIF transactions.workflow"
src = "#{__dir__}/#{filename}"
dest = "#{ENV["HOME"]}/Library/Workflows/Applications/Folder Actions"

FileUtils.mkdir_p dest
FileUtils.cp_r(src, dest, preserve: true)
