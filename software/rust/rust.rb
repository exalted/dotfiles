#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

brew 'rustup-init'
# TODO: This 👆 all by itself will NOT install rust, rustup, cargo, etc. Instead
#       you need to run `rustup-init` afterwards and follow instructions to
#       to tweak the installation (e.g., we don't want `rustup-init` to modify
#       our `~/.bashrc` file).
#       So, in order to improve your dotfiles you should check if rust is
#       already installed, and conditionally either call `rustup-init` with all
#       the options you want (e.g., `--no-modify-path`), to install rust
#       properly for the first time; OR consider running `rustup update` to
#       update rust.

bash_source_relative
