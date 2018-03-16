#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../src/helpers'

brew 'awscli'
# TODO: consider removing `s3cmd` in favor of `aws s3`
brew 's3cmd'

# TODO: `aws configure` generates `~/.aws/config` and `~/.aws/credentials` files:
#         - what if I wanted to access to multiple AWS accounts? (there's a
#           `--profile` flag to `aws configure` command, maybe that's it?)
#         - it contains secrets, so can't push it to GitHub!

# TODO: `~/.s3cfg` file:
#         - what if I wanted to access to multiple AWS accounts?
#         - it contains secrets, so can't push it to GitHub!
