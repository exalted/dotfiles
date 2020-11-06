#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../src/helpers'

# https://stripe.com/docs/stripe-cli#install
# https://stripe.com/docs/stripe-cli/configure#autocompletion
bash_source "#{ENV["HOME"]}/.stripe/stripe-completion.bash"

# TODO: install stripe-cli and create autocompletion automatically
