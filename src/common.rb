# Inspired by https://github.com/Homebrew/install/blob/63e779e5d6cc1cd7ddefda9c0eb404687d1a1c79/install

module Tty
  module_function

  def blue
    bold 34
  end

  def red
    bold 31
  end

  def reset
    escape 0
  end

  def bold(n = 39)
    escape "1;#{n}"
  end

  def underline
    escape "4;39"
  end

  def escape(n)
    "\033[#{n}m" if STDOUT.tty?
  end
end

class Array
  def shell_s
    cp = dup
    first = cp.shift
    cp.map { |arg| arg.gsub " ", "\\ " }.unshift(first).join(" ")
  end
end

def ohai(*args)
  puts "#{Tty.blue}>>>#{Tty.bold} #{args.shell_s}#{Tty.reset}"
end

def warn(warning)
  puts "#{Tty.red}Warning#{Tty.reset}: #{warning.chomp}"
end

def cmd_exists?(cmdname)
  Kernel.system "command -v #{cmdname} > /dev/null"
end

# ? This overrides built-in system command
def system(*args)
  abort "Failed during: #{args.shell_s}" unless Kernel.system(*args)
end
