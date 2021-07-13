#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

cask 'hookshot'

filename = "com.knollsoft.Hookshot.plist"
src = "#{__dir__}/#{filename}"
dest = "#{ENV["HOME"]}/Library/Preferences/#{filename}"

# "normal" size (eg for safari), which shoudl be already applied into the plist
# defaults write com.knollsoft.Hookshot almostMaximizeWidth -float 0.8
# defaults write com.knollsoft.Hookshot almostMaximizeHeight -float 1

if File.file?(dest)
  Kernel.system "plutil -convert xml1 -o #{src} #{dest}"
else
  Kernel.system "plutil -convert binary1 -o #{dest} #{src}"
  FileUtils.copy_file(src, dest, preserve: true)
end
