#!/usr/bin/env ruby

require "English" # $CHILD_STATUS instead of $?, etc.


def main(args)
  exit unless there_are_no_pending_changes?(args)
end

def there_are_no_pending_changes?(args)
  changes = git(:status, "--porcelain")
  say_cannot_undo_with(changes, args) unless changes.empty?
  changes.empty?
end

def say_cannot_undo_with(changes, args)
  return if args[:quiet]
  puts "Cannot undo: You have changes you would loose otherwise."
  puts ["", "#{changes}"].join("\n") if args[:verbose]
end

def git(subcommand, *args)
  output = `git #{subcommand} #{args.join(" ")}`
  exit unless $CHILD_STATUS.success?
  output
end

def parse_cli(args)
  {
    quiet:   args.include?("--quiet"),
    verbose: args.include?("--verbose")
  }
end


args = parse_cli(ARGV)
exit main(args)
