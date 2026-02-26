#!/usr/bin/env ruby
require_relative '../../src/helpers'

# NOTE: search for "matthewpalmer" in your Inbox to find the activation license number
cask 'rocket'

filename = "net.matthewpalmer.Rocket.plist"
src = "#{__dir__}/#{filename}"
dest = "#{ENV["HOME"]}/Library/Preferences/#{filename}"

if File.file?(dest)
  system "plutil -convert xml1 -o #{src} #{dest}"
else
  FileUtils.mkdir_p Pathname.new(dest).dirname
  system "plutil -convert binary1 -o #{dest} #{src}"
end
