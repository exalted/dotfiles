#!/usr/bin/env ruby
require_relative '../../src/helpers'

debounce(period: '1d') {
  brew 'gnupg'  # a.k.a. `gpg`
  cask 'gpg-suite'
}
