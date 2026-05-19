#!/usr/bin/env ruby
require_relative '../src/helpers'

# https://stripe.com/docs/stripe-cli#install
brew 'stripe/stripe-cli/stripe'

# https://stripe.com/docs/stripe-cli/configure#autocompletion
unless File.exist? "#{ENV["HOME"]}/.stripe/stripe-completion.bash"
  system "stripe completion --shell bash"
  system "mkdir -p #{ENV["HOME"]}/.stripe"
  system "mv stripe-completion.bash #{ENV["HOME"]}/.stripe"
end

bash_source "#{ENV["HOME"]}/.stripe/stripe-completion.bash"
