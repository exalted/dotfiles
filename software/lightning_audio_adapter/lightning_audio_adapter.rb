#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

brew 'switchaudio-osx'

Kernel.system "brew tap mvp/uhubctl https://github.com/mvp/uhubctl"
brew 'uhubctl'

link_relative 'org.pittle.lightning_audio_adapter.plist', "#{ENV["HOME"]}/Library/LaunchAgents/"
Kernel.system "launchctl load -w #{ENV["HOME"]}/Library/LaunchAgents/org.pittle.lightning_audio_adapter.plist"
# Kernel.system "launchctl unload #{ENV["HOME"]}/Library/LaunchAgents/org.pittle.lightning_audio_adapter.plist"

bash_source_relative
