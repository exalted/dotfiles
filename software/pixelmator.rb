#!/usr/bin/env ruby
require_relative '../src/helpers'

install 'Pixelmator', <<~MESSAGE
  Pixelmator must be installed manually.

  15 Dec 2025: "Error: No apps found in the App Store for ADAM ID 407963104"

  Previously installed automatically via `mas '407963104'` — that no longer works.
MESSAGE
