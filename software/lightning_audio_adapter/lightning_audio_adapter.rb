#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

brew 'switchaudio-osx'

# system "brew tap mvp/uhubctl https://github.com/mvp/uhubctl"
# brew 'uhubctl'
brew 'mvp/uhubctl/uhubctl'

link_to_home_relative 'org.pittle.lightning_audio_adapter.plist', "Library/LaunchAgents/org.pittle.lightning_audio_adapter.plist"
system "launchctl load -w #{ENV["HOME"]}/Library/LaunchAgents/org.pittle.lightning_audio_adapter.plist"
# system "launchctl unload #{ENV["HOME"]}/Library/LaunchAgents/org.pittle.lightning_audio_adapter.plist"

bash_source_relative
