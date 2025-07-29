#!/usr/bin/env ruby
require_relative '../../src/helpers'

brew 'awscli'
cask 'session-manager-plugin'

bash_source_relative
