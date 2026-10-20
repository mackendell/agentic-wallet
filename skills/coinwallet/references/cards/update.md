# Update card

The user asked to update CoinWallet. One yes covers both: the skill and the wallet service.

## Steps

1. Before any command, ask once, in one message: "Update CoinWallet now? This updates the skill and the wallet service, and restarts the service."
   On macOS (`uname -s` says `Darwin`) add this line to the same message: "A Mac popup will ask for your login password for "com.coinsdo.wallet.secure". Type your Mac login password and click **Always Allow**. Never click **Deny**. If a "Keychain Not Found" dialog offers **Reset To Defaults**, click **Cancel**."
2. Wait for the answer; run nothing until then. Only a plain yes counts. No, or unclear → stop. Nothing is changed.
3. Run your Host's two commands in the terminal, in order, exactly as written. The first updates the skill. The second backs up the MCP data folder, installs the newest tested service and starts it right away (it can take 2 minutes; wait for it).
   - Claude Code:
     `claude plugin marketplace update coinsdo && claude plugin update coinwallet@coinsdo`
     `python3 "$(ls -d "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/plugins/cache/coinsdo/coinwallet/*/skills/coinwallet | sort -V | tail -1)/scripts/mcp.py" upgrade`
   - Codex:
     `codex plugin marketplace upgrade coinsdo && codex plugin add coinwallet@coinsdo`
     `python3 "$(ls -d "${CODEX_HOME:-$HOME/.codex}"/plugins/cache/coinsdo/coinwallet/*/skills/coinwallet | sort -V | tail -1)/scripts/mcp.py" upgrade`
   - Hermes:
     `hermes skills update coinwallet`
     `python3 "${HERMES_HOME:-$HOME/.hermes}/skills/coinwallet/scripts/mcp.py" upgrade`
   - OpenClaw:
     `openclaw plugins update coinwallet --accept-capabilities`
     `python3 "${OPENCLAW_STATE_DIR:-$HOME/.openclaw}/extensions/coinwallet/skills/coinwallet/scripts/mcp.py" upgrade`
4. Read the `result:` line of `mcp.py`:
   - `ok` → tell the user the `say:` line.
   - `fallback` → the new version failed its check, so the old one runs again on the same data. Tell the user the `say:` line.
   - `needs_user` → tell the user the `say:` line. When the user says it's done, run the same `mcp.py` command with `start` instead of `upgrade`, once.
   - `failed` → tell the user the `say:` line and stop.
5. End with: "Start a new chat so the new version loads."

## Update traps

- Run `upgrade`, never `install`: install leaves an old service as it is.
- The skill update command fails → tell the user its last line and stop. Never run `upgrade` before the skill update worked.
- After the upgrade the `coinwallet` tools stop working in this chat. That is expected. Never call them again in this chat.
- Never delete or move the MCP data folder, its `backups` or `.key` folder, or a master key file: the key pairs with the agent's key shard.
