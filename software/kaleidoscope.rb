#!/usr/bin/env ruby
require_relative '../src/helpers'

# TODO: save its settings

install 'Kaleidoscope', <<~MESSAGE
  Kaleidoscope must be installed manually.

  15 Dec 2025: "Error: No apps found in the App Store for ADAM ID 587512244"

  Previously installed automatically via `mas '587512244'` — that no longer works.
MESSAGE

install 'ksdiff', <<~MESSAGE
  ksdiff (Kaleidoscope's CLI diff/merge tool) can't be installed via cask.

  Commented out because it started to fail with "The version of Kaleidoscope installed at /Applications/Kaleidoscope.app (version 126) is too old to be launched by ksdiff (version 146)."

  Instead, open Kaleidoscope and go to "Kaleidoscope" -> "Integration" and install the CLT following the instructions there.

  15 Dec 2025: on macOS Tahoe, selecting "Integration" crashes the app.

  Previously installed automatically via `cask 'ksdiff'` — that no longer works.
MESSAGE
