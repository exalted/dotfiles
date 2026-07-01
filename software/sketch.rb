#!/usr/bin/env ruby
require_relative '../src/helpers'

install 'Sketch', <<~MESSAGE
  Sketch must be installed manually.

  License expired, so the latest usable version is 43.2 — see the changelog:
  https://www.sketch.com/changelog/43-2/

  Direct download link:
  https://download.sketch.com/sketch-43.2-39069.zip

  Previously installed automatically via `cask 'sketch'` — that no longer works.
MESSAGE
