#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

brew 'awscli'
brew 'aws/tap/aws-sam-cli'

bash_source_relative
