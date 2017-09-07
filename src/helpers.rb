require_relative './common'

def brew(formula)
  Kernel.system "brew ls --versions #{formula} > /dev/null"
  system "brew install #{formula}" unless $?.success?
end
