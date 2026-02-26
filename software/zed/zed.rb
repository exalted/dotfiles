#!/usr/bin/env ruby
require_relative '../../src/helpers'

brew 'zed@preview'

link_to_home_relative 'settings.json', '.config/zed/settings.json'
link_to_home_relative 'keymap.json', '.config/zed/keymap.json'

