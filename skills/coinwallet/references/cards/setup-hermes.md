# Setup on Hermes

Run each step once, in order, in this chat.

1. Run this in the terminal (it can take 2 minutes; wait for it):

   ```sh
   python3 "${HERMES_HOME:-$HOME/.hermes}/skills/coinwallet/scripts/mcp.py" install --host hermes
   ```

   It downloads the tested MCP service, starts it once, waits until it answers, then stops it.
2. `result: ok` → run the line after `register:` in the terminal, exactly as printed. It adds the `coinwallet` MCP server to Hermes' config. If it printed a `say:` line, tell the user that line.
   Any other result → see "Reading `scripts/mcp.py`" in `references/cards/setup.md`.
3. Hermes starts the service by itself and loads the `coinwallet` tools from the user's next message. Stay in this chat.
4. Tell the user: "The wallet service is set up." Then open `references/cards/join.md` in this chat.

## Hermes traps

- Register only with the printed `hermes config set` line. Never run `hermes mcp add`: it waits for an answer in a menu. Never edit `config.yaml` by hand.
- `coinwallet` tools still missing on the next message → ask the user to send `/reload-mcp`, once.
