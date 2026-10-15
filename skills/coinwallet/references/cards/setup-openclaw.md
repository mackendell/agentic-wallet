# Setup on OpenClaw

Run each step once, in order, in this chat.

1. Run this in the terminal (it can take 2 minutes; wait for it):

   ```sh
   python3 "${OPENCLAW_STATE_DIR:-$HOME/.openclaw}/extensions/coinwallet/skills/coinwallet/scripts/mcp.py" install --host openclaw
   ```

   It downloads the tested MCP service, starts it once, waits until it answers, then stops it.
2. `result: ok` → run the line after `register:` in the terminal, exactly as printed. It adds the `coinwallet` MCP server to OpenClaw. If it printed a `say:` line, tell the user that line.
   Any other result → see "Reading `scripts/mcp.py`" in `references/cards/setup.md`.
3. OpenClaw starts the service by itself and loads the `coinwallet` tools from the user's next message. Stay in this chat.
4. Tell the user: "The wallet service is set up." Then open `references/cards/join.md` in this chat.

## OpenClaw traps

- Register only with the printed `openclaw mcp set` line. Never run `openclaw mcp add`. Never change OpenClaw's config files by hand.
- The skill folder is `extensions/coinwallet/skills/coinwallet` inside `~/.openclaw`. Cards are under its `references/cards/`.
- `coinwallet` tools still missing on the next message → run `openclaw mcp reload` in the terminal, once. Then ask the user to send their message again.
