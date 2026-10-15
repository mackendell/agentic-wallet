# Setup on Codex

Run each step once, in order, in this chat.

1. Run this in the terminal (it can take 2 minutes; wait for it):

   ```sh
   python3 "$(ls -d "${CODEX_HOME:-$HOME/.codex}"/plugins/cache/coinsdo/coinwallet/*/skills/coinwallet | sort -V | tail -1)/scripts/mcp.py" install --host codex
   ```

   It downloads the tested MCP service, starts it once, waits until it answers, then stops it.
2. `result: ok` → run the line after `register:` in the terminal, exactly as printed. It adds the `coinwallet` MCP server to Codex. If it printed a `say:` line, tell the user that line.
   Any other result → see "Reading `scripts/mcp.py`" in `references/cards/setup.md`.
3. The `coinwallet` tools and this skill load only in a new chat. In this chat, never call `coinwallet` tools and never wait for them.
4. Tell the user: "The wallet service is set up." Then open `references/cards/join.md` in this chat for the App steps. End with: "Open a new chat and paste your Invitation code there."

## Codex traps

- Both commands need the network and write outside this folder. In the sandbox they fail: install says "Download failed", register says "permission denied" or "read-only". Then run the same command again with escalated permissions (outside the sandbox), so the user can approve it. Never change the command.
- Register only with the printed `codex mcp add` line. Never change Codex's config files by hand.
- The skill folder is `plugins/cache/coinsdo/coinwallet/<version>/skills/coinwallet` inside `~/.codex`. Cards are under its `references/cards/`.
