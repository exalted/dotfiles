#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

cask 'vlc'

# TODO: The technique below is copied from `software/mosaic.rb`, no bueno…

filename = "vlcrc"
src = "#{__dir__}/#{filename}"
dest = "#{ENV["HOME"]}/Library/Preferences/org.videolan.vlc/#{filename}"

if File.exists?(dest)
  FileUtils.copy_file(dest, src, preserve: true)
else
  FileUtils.mkdir_p Pathname.new(dest).dirname
  FileUtils.copy_file(src, dest, preserve: true)
end
