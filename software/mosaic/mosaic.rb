#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

cask 'mosaic'

# TODO: The technique below is copied over in `software/vlc.rb` as well, no bueno…

# Linking Mosaic's preferences file won't work, because it will overwrite it
# with a real file; hence the link will be broken. Here's what we do instead:
#
# - Whenever `dotfiles` is run, we check if is there a preferences file already
#   in the system.
# - If it's there, then copy that file over ours (because we want to keep
#   those changes)
# - If it's _not_ there, then we make a copy of our file to create an initial
#   preferences file, so to speak…
#
# The only downside of this approach is that we may loose latest changes to
# Mosaic's preferences if we haven't run `dotfiles` in a while.

filename = "MosaicCoreData.storedata"
src = "#{__dir__}/#{filename}"
dest = "#{ENV["HOME"]}/Library/Application Support/com.lightpillar.Mosaic/#{filename}"

if File.exists?(dest)
  FileUtils.copy_file(dest, src, preserve: true)
else
  FileUtils.mkdir_p Pathname.new(dest).dirname
  FileUtils.copy_file(src, dest, preserve: true)
end
