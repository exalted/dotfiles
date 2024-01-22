#!/usr/bin/env ruby
require_relative '../../src/helpers'

brew 'awscli'
cask 'session-manager-plugin'
brew 'aws-sam-cli'

bash_source_relative
