#!/usr/bin/env ruby
require_relative '../../src/helpers'

brew 'ack'

link_to_home_relative 'ackrc', '.ackrc'
