require_relative '../common'
require_relative './install_everything'

# Foundational software the dotfiles machinery itself depends on. Unlike the
# profile lists in profiles.rb this is not configurable — bin/dotfiles can't run
# without it — so it lives here and is installed up front, before any profile
# software. Order matters: the package manager, then the shell, then Ruby.
BOOTSTRAP = %w[
  homebrew
  bash
  ruby
].freeze

def bootstrap
  ohai 'Bootstrapping…'
  BOOTSTRAP.each { |name| system resolve_software(name) }
  install_dependencies
end

# This repo is itself Ruby, so it carries its own dev bundle: solargraph, the
# language server the editor runs as `bundle exec solargraph` from the repo
# root. The committed .bundle/config vendors it into ./vendor/bundle regardless
# of any global ~/.bundle/config. Runs after BOOTSTRAP so Ruby + Bundler exist.
def install_dependencies
  root = File.expand_path("#{__dir__}/../..")

  Dir.chdir(root) do
    if Kernel.system('bundle check > /dev/null 2>&1')
      ohai 'Repo dependencies already satisfied.'
    else
      ohai 'Installing repo dependencies…'
      system 'bundle install'
    end
  end
end
