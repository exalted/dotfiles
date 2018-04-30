#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

link_to_home_relative(
  'com.apple.Terminal.plist',
  'Library/Preferences/com.apple.Terminal.plist',
  backup: true,
)
