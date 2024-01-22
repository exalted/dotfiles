#!/usr/bin/env ruby
require_relative '../src/helpers'

# We are installing nightly, because for whatever reason Sequel Pro didn't
# release a new version in years, but still fixing bugs and stuff and building
# nightlies :shrug:
cask 'sequel-pro-nightly'
# cask 'sequel-pro'

# TODO: consider saving its settings
