#!/usr/bin/env ruby
require_relative '../src/helpers'

# TODO: Need to install manually, because;
# 15 Dec 2025:
# Error: No apps found in the App Store for ADAM ID 587512244
#
# TODO: save its settings
# mas '587512244'

# Commented out because it started to fail with "The version of Kaleidoscope installed at /Applications/Kaleidoscope.app (version 126) is too old to be launched by ksdiff (version 146)."
# Instead, open Kaleidoscope and go to "Kaleidoscope" -> "Integration" and install the CLT following the instructions there
#
# 15 Dec 2025: on macOS Tahoe when selected "Integration" menu item as mentioned above the app will quit/crash.
#
# cask 'ksdiff'
