#!/usr/bin/env ruby
require_relative '../../src/helpers'

brew 'switchaudio-osx'

brew 'uhubctl'

# 3 Feb 2024: I disabled this because I was having mac sleep/wake issues and I
# was suspecting this may be contribute to that. Also, I am not using the
# lightning audio adapter as much as I used to, so there's no point in keeping
# it running all the time:
# link_to_home_relative 'org.pittle.lightning_audio_adapter.plist', "Library/LaunchAgents/org.pittle.lightning_audio_adapter.plist"
# system "launchctl load -w #{ENV["HOME"]}/Library/LaunchAgents/org.pittle.lightning_audio_adapter.plist"
# # system "launchctl unload #{ENV["HOME"]}/Library/LaunchAgents/org.pittle.lightning_audio_adapter.plist"

bash_source_relative
