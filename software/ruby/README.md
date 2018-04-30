## Install rbenv

```bash
brew install rbenv
brew install ruby-build
brew install rbenv-gem-rehash
```

## Install and override system Ruby

<table>
  <tr>
    <td>:warning:</td>
    <td>I don't like to override system Ruby anymore, so think carefully before implementing this in the new `dotfiles`…</td>
  </tr>
</table>

For latest best practices [read here first](https://github.com/sstephenson/ruby-build/wiki)!

```bash
export __RUBY_VERSION__='2.2.3'

brew update
brew upgrade rbenv || brew install rbenv
brew upgrade ruby-build || brew install ruby-build
brew upgrade rbenv-gem-rehash || brew install rbenv-gem-rehash
brew upgrade openssl || brew install openssl
brew upgrade libyaml || brew install libyaml
brew upgrade libffi || brew install libffi
brew upgrade readline || brew install readline

RUBY_CONFIGURE_OPTS="--with-openssl-dir=$(brew --prefix openssl) --with-readline-dir=$(brew --prefix readline)" rbenv install "$__RUBY_VERSION__"
rbenv global "$__RUBY_VERSION__"
```
