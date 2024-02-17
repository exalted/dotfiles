#!/usr/bin/env ruby
require_relative '../../src/helpers'

cask 'hookshot'

filename = "com.knollsoft.Hookshot.plist"
src = "#{__dir__}/#{filename}"
dest = "#{ENV["HOME"]}/Library/Preferences/#{filename}"

if File.file?(dest)
  system "plutil -convert xml1 -o #{src} #{dest}"
else
  system "plutil -convert binary1 -o #{dest} #{src}"
  FileUtils.copy_file(src, dest, preserve: true)
end

# "normal" size (eg for safari), which should already be applied into the plist
# defaults write com.knollsoft.Hookshot almostMaximizeWidth -float 0.8
# defaults write com.knollsoft.Hookshot almostMaximizeHeight -float 1
