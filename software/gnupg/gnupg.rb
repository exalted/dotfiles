#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

brew 'gnupg'  # a.k.a. `gpg`
cask 'gpg-suite'
