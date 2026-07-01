#!/usr/bin/env ruby
require_relative '../src/helpers'

# TODO: save its settings

install 'Reeder', <<~MESSAGE
  Reeder must be installed manually.

  15 Dec 2025: "Error: No apps found in the App Store for ADAM ID 880001334"

  Previously installed automatically via `mas '880001334'` (Reeder 3) — that no longer works.
MESSAGE
