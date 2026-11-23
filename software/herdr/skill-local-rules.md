
## Start a helper agent that does not get stuck

This machine's shell setup adds 2 interactive questions that stop a helper agent before it can work. Follow these rules each time you start an agent in a pane, in addition to the rules above.

1. Split the pane with `--env CLAUDE_TODO_HOOKS=0`. This variable turns off the todo hooks. Without it, a helper Claude asks about open side tasks at the end of its turn and stays `blocked`.
2. For `--kind claude`, give a session name after `--`: `-- -n <name>`. Without `-n`, the `claude` shell wrapper asks for a session name, and `agent start` waits until its timeout.
3. Pass `--timeout` to `agent start`, `agent prompt --wait` and `agent wait`. A stop then fails as a `timeout` error instead of an endless wait.
4. After each wait, read `.result.agent.agent_status`. If the status is `blocked`, run `agent read` and ask the user before you answer the dialog.
5. When the work is done, close the pane you created, unless the user wants to keep it.

Example:

```bash
pane=$(herdr pane split --current --direction right --cwd "$PWD" --env CLAUDE_TODO_HOOKS=0 --no-focus \
  | jq -r .result.pane.pane_id)
herdr agent start helper --kind claude --pane "$pane" --timeout 60000 -- -n helper
herdr agent prompt helper "Summarize the uncommitted changes." --wait --timeout 120000 \
  | jq -r .result.agent.agent_status
herdr agent read helper --source recent-unwrapped --lines 120
herdr pane close "$pane"
```
