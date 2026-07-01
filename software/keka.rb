#!/usr/bin/env ruby
require_relative '../src/helpers'

cask 'keka'
cask 'kekaexternalhelper'

# Sandboxing keeps Keka from registering itself as the default extraction
# app, so its helper has to do it instead:
# https://github.com/aonez/Keka/wiki/Default-application
#
# The helper relocates itself out of /Applications into this container path
# once it's run, so check both locations for wherever it currently lives.
helper_paths = [
  '/Applications/KekaExternalHelper.app/Contents/MacOS/KekaExternalHelper',
  "#{ENV["HOME"]}/Library/Containers/com.aone.keka/Data/Library/Application Support/Keka/KekaExternalHelper.app/Contents/MacOS/KekaExternalHelper",
]
helper_path = helper_paths.find { |path| File.exist?(path) }
system(helper_path, '--set-as-default') if helper_path
