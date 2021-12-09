#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../src/helpers'

# https://stripe.com/docs/stripe-cli#install
brew 'stripe/stripe-cli/stripe'

# https://stripe.com/docs/stripe-cli/configure#autocompletion
unless File.exist? "#{ENV["HOME"]}/.stripe/stripe-completion.bash"
  Kernel.system "stripe completion --shell bash"
  Kernel.system "mkdir -p #{ENV["HOME"]}/.stripe"
  Kernel.system "mv stripe-completion.bash #{ENV["HOME"]}/.stripe"
end

bash_source "#{ENV["HOME"]}/.stripe/stripe-completion.bash"
