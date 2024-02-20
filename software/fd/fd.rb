#!/usr/bin/env ruby
require_relative '../../src/helpers'

brew 'fd'

link_to_home_relative 'ignore', '.config/fd/ignore'
