#!/usr/bin/env ruby
require_relative '../../src/helpers'

debounce(period: '1d') {
  brew 'awscli'
  cask 'session-manager-plugin'
}

bash_source_relative
