## Create a new key

```bash
mkdir -p "$HOME/.ssh"
ssh-keygen -t rsa -C "$(whoami)@$(hostname)" -f "$HOME/.ssh/foobar_rsa"
```
