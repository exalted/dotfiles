#!/usr/bin/env ruby
require_relative '../src/helpers'

install 'CleanShot X', <<~MESSAGE
  CleanShot X must be installed manually.

  License is stuck at "version 4.7.7" — see:
  https://cleanshot.com/why-updates-expire

  Download and install this version instead:
  https://updates.getcleanshot.com/v3/CleanShot-X-4.7.7.dmg

  Previously installed automatically via `cask 'cleanshot'` — that no longer works.
MESSAGE
