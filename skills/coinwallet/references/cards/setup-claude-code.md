# Setup on Claude Code

Run each step once, in order, in this chat.

1. Run this in the terminal (it can take 2 minutes; wait for it):

   ```sh
   python3 "$(ls -d "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/plugins/cache/coinsdo/coinwallet/*/skills/coinwallet | sort -V | tail -1)/scripts/mcp.py" install --host claude-code
   ```

   It downloads the tested MCP service, starts it once, waits until it answers, then stops it.
2. `result: ok` → run the line after `register:` in the terminal, exactly as printed. It adds the `coinwallet` MCP server to Claude Code for this user. If it printed a `say:` line, tell the user that line.
   Any other result → see "Reading `scripts/mcp.py`" in `references/cards/setup.md`.
3. The `coinwallet` tools and this skill load only in a new chat. In this chat, never call `coinwallet` tools and never wait for them.
4. Tell the user: "The wallet service is set up." Then open `references/cards/join.md` in this chat for the App steps. End with: "Open a new chat and paste your Invitation code there."

## Claude Code traps

- Register only with the printed line (it runs `claude mcp add-json --scope user`). Never run `claude mcp add` by hand. Never change Claude Code's config files by hand.
- The skill folder is `plugins/cache/coinsdo/coinwallet/<version>/skills/coinwallet` inside `~/.claude`. Cards are under its `references/cards/`.
- A command is blocked by a permission prompt → ask the user to allow it, then run the same command again.
