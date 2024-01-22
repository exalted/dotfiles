#!/usr/bin/env ruby
require_relative '../../src/helpers'

# TODO: The technique below is copied from `software/mosaic.rb`, no bueno…

filename = "Remount all.workflow"
src = "#{__dir__}/#{filename}"
dest = "#{ENV["HOME"]}/Library/Services"

FileUtils.mkdir_p dest
FileUtils.cp_r(src, dest, preserve: true)
