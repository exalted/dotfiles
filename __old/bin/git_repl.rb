#!/usr/bin/env ruby

system_bashrc = "/etc/bashrc"
user_bashrc = File.expand_path("~/.bashrc")

text = <<-EOF
#{File.read(system_bashrc) if File.exist?(system_bashrc)}
#{File.read(user_bashrc) if File.exist?(user_bashrc)}
export PS1="$PS1"'\\[\\e[30m\\]git \\[\\e[0m\\]'
EOF

foo = File.expand_path("~/Desktop/bashrc")

File.open(foo, "w") { |f| f.write(text) }

exec("bash --rcfile #{foo} -i")

# TODO: https://github.com/rcaloras/bash-preexec/issues/2
