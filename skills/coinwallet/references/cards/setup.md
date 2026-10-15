# Setup card

Set up the CoinsDo wallet MCP service so the `coinwallet` tools work. Do it right after the skill install, in the same chat. Never skip it: the skill is useless without the service.

## Steps

1. Open your Host's file, exactly one:
   - Hermes → `references/cards/setup-hermes.md`
   - Claude Code → `references/cards/setup-claude-code.md`
   - Codex → `references/cards/setup-codex.md`
   - OpenClaw → `references/cards/setup-openclaw.md`
2. Follow it. Setup is done when `scripts/mcp.py install` printed `result: ok` and the register command ran once.

## Reading `scripts/mcp.py`

- It prints `key: value` lines. Read `result:` and `say:`.
- `result: ok` → go on. If it printed a `say:` line, tell the user that line.
- `result: needs_user` with "older than the minimum" → tell the user and ask: "Upgrade the wallet service now? It restarts the service." Yes → open `references/cards/update.md`. No → stop and say the wallet does not work below that version.
- Any other result → tell the user the `say:` line in their language and stop.
- Run each command exactly as printed. Wait for it: install can take 2 minutes.

## Rules

- `scripts/mcp.py` is the only way the service is installed. Never tell the user to download it in a browser.
- The service always starts with `-e prod`. Testnet wallets work on it too.
- macOS: if a popup asks for the password for "com.coinsdo.wallet.secure", tell the user: type your Mac login password and click **Always Allow**. Never click **Deny**.
- macOS: if a "Keychain Not Found" dialog offers **Reset To Defaults**, tell the user to click **Cancel**.
