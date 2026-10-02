#!/usr/bin/env ruby
require_relative '../../src/helpers'

# `jira` reads the Jira site and project key from a per-machine file, because
# this repo is public. Nothing here can create that file, so say so while
# someone is watching the run rather than when `jira` is first typed.
config = File.expand_path("#{ENV["HOME"]}/.config/dotfiles/jira")
warn "`jira` won't open anything until #{config} holds the story URL up to the number, " \
     "e.g. https://<site>.atlassian.net/browse/<PROJECT>-" unless File.size?(config)

bash_source_relative 'jira'
