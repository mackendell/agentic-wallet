<p align="center"><img src=".github/readme/logo.svg" alt="CoinsDo" width="240"></p>

# CoinWallet skill

English · [简体中文](.github/readme/README.zh-Hans.md) · [繁體中文](.github/readme/README.zh-Hant.md) · [日本語](.github/readme/README.ja.md)

**Installing with an AI agent:** the agent runs the 4 "Install steps" below.

Let your AI agent hold and send crypto in a CoinWallet MPC wallet. You approve every send in the CoinWallet App.

Paste this into your agent's chat (Claude Code, Codex, Hermes or OpenClaw):

```text
Install the CoinWallet skill from https://github.com/CoinsDo/agentic-wallet
```

## Install steps

These are the steps behind the install sentence above: the skill, then the wallet service it needs. The agent runs all 4 in this chat, in order. Step 4 is the end.

1. Install the skill with the Host's command. `OWNER` is the owner in the user's GitHub link (`CoinsDo` if there is no link). On Codex, use this plugin command, not the skill-installer:

   | Host | Command |
   |---|---|
   | Claude Code | `claude plugin install coinwallet --marketplace OWNER/agentic-wallet` |
   | Codex | `codex plugin marketplace add OWNER/agentic-wallet && codex plugin add coinwallet@coinsdo` |
   | Hermes | `hermes skills install OWNER/agentic-wallet/skills/coinwallet --yes` |
   | OpenClaw | `openclaw plugins install coinwallet --marketplace OWNER/agentic-wallet --force --accept-capabilities` |

2. Run the Host's setup card from the installed `coinwallet` skill. It installs and starts the wallet service; the skill can't reach the wallet without it.

   | Host | Setup card |
   |---|---|
   | Claude Code | `~/.claude/plugins/cache/coinsdo/coinwallet/*/skills/coinwallet/references/cards/setup-claude-code.md` |
   | Codex | `~/.codex/plugins/cache/coinsdo/coinwallet/*/skills/coinwallet/references/cards/setup-codex.md` |
   | Hermes | `skill_view` with name `coinwallet` and path `references/cards/setup-hermes.md` |
   | OpenClaw | `~/.openclaw/extensions/coinwallet/skills/coinwallet/references/cards/setup-openclaw.md` |

3. Open `references/cards/join.md` in the same skill and follow it: give the App links and help the user make a wallet Room. Give App links only from that card.
4. Claude Code or Codex: end with "Open a new chat and paste your Invitation code there." Hermes or OpenClaw: keep going in this chat.

## How it works

1. Paste the sentence above into your agent's chat.
2. The agent installs the skill and the CoinsDo wallet service. You don't need to install anything else. It needs macOS or Linux with Python 3.9 or newer.
3. The agent gives you the CoinWallet App links (iPhone and Android) and the steps to make a wallet in the App.
4. In the App you get a 6-character Invitation code. Paste it into the chat within 60 minutes. On Claude Code or Codex, paste it into a new chat.
5. In the App, tap "Create", then claim your key shard. Your wallet is ready.

## What you can ask

Ask in your own language. For example:

- "What's my USDT address?"
- "How much is in my wallet?"
- "Give me a new TRX address."
- "Send 10 USDT to TX…"
- "Approve my transfer." (a transfer you started in the App)
- "Show my transfer history."
- "Update CoinWallet."

## You approve every send in the App

The agent can never send on its own. Every send has two steps:

1. **In the chat:** the agent shows one line with the amount, the coin, the Chain, the wallet and the full address. Read it. Reply "yes" to go on. Anything else, and nothing is sent.
2. **In the App:** open "Activity" → "Pending" and open the transfer. **Check that the full address matches.** Then tap "Approve" within 15 minutes. Changed your mind? Tap "Reject", or wait 15 minutes.

A new address also needs your approval in the App ("Activity" → "Add address").

## Good to know

- **Mac, after an update:** a popup asks for your Mac login password for "com.coinsdo.wallet.secure". Type it and click **Always Allow**. Never click **Deny**. If a "Keychain Not Found" dialog offers **Reset To Defaults**, click **Cancel**.
- **Linux:** never delete or replace the master key file or the wallet data folder. Moving to a new server means making a new wallet Room.
- **Testnet:** the App shows Mainnet only. Ask the agent if you want to try Testnet first.

## Install by hand

You don't need this if the agent installed it for you. Open your Host:

<details>
<summary>Claude Code</summary>

Install:

```sh
claude plugin install coinwallet --marketplace CoinsDo/agentic-wallet
```

Then open a new chat and ask: "Set up the CoinWallet service."

Uninstall (read the warning below first):

```sh
claude mcp remove --scope user coinwallet
claude plugin marketplace remove coinsdo
```

</details>

<details>
<summary>Codex</summary>

Install:

```sh
codex plugin marketplace add CoinsDo/agentic-wallet && codex plugin add coinwallet@coinsdo
```

Then open a new chat and ask: "Set up the CoinWallet service."

Uninstall (read the warning below first):

```sh
codex mcp remove coinwallet
codex plugin remove coinwallet@coinsdo && codex plugin marketplace remove coinsdo
```

</details>

<details>
<summary>Hermes</summary>

Install:

```sh
hermes skills install CoinsDo/agentic-wallet/skills/coinwallet --yes
```

Then ask: "Set up the CoinWallet service."

Uninstall (read the warning below first):

```sh
hermes config unset mcp_servers.coinwallet
hermes skills uninstall coinwallet --yes
```

</details>

<details>
<summary>OpenClaw</summary>

Install:

```sh
openclaw plugins install coinwallet --marketplace CoinsDo/agentic-wallet --force --accept-capabilities
```

Then ask: "Set up the CoinWallet service."

Uninstall (read the warning below first):

```sh
openclaw mcp unset coinwallet
openclaw plugins uninstall coinwallet --force
```

</details>

> [!WARNING]
> **Before you uninstall:** never delete the wallet data folder or its master key while the wallet holds funds. They hold the agent's key shard. Without it, the agent can't sign, and a 2-of-2 wallet can't send at all. Uninstalling the skill leaves them in place.
>
> - macOS: `~/Library/Application Support/coinsdo-wallet-mcp` (its master key is in your Mac keychain as "com.coinsdo.wallet.secure"; never delete it)
> - Linux: `~/.config/coinsdo-wallet-mcp` (with its `master.key` file, if it has one)
>
> Move the funds out in the App first.

## Maintenance

For the maintainer. Dev tools are listed in `AGENTS.md`.

<details>
<summary>Per MCP release</summary>

1. Run the Test plan locally on the new MCP service.
2. Do a downgrade round trip: put the previous tested MCP back on the same data. `get_wallets` must show `ONLINE`, and one Testnet send must work.
3. Pass → add the version and its sha256 hashes to `skills/coinwallet/mcp-tested.json`. Round trip failed → also list it under `no_fallback`.
4. Release the skill (steps below). Tell users: "Send your agent *update CoinWallet*."
5. The `minimum` MCP version goes up only with a skill release (for example, once the `"1|2"` schema fix ships).

</details>

<details>
<summary>Per App release</summary>

The private App refresh skill (`mackendell/coinwallet-maintainer`, built later) updates the button tables in the cards and their "App 2.0.31" line. It fixes words; people fix flows.

</details>

<details>
<summary>Add a Chain</summary>

1. Research the Chain's send rules (gas coin, reserve or rent, tag or memo, real token contracts, explorer), like #13.
2. Write `skills/coinwallet/references/chains/<chain>.md` from an existing chain file. Keep it at 1.5 KB or less, with `Gas coin:`, `Explorer:` and `Checked:` lines.
3. Add its codes to the send card's allow-list line (``by `abbreviation` ``).
4. The Chain has a Testnet → add a Testnet trap case to `dev/test_cases.py`.
5. It must pass 3 of 3 runs on DeepSeek Flash.

</details>

<details>
<summary>Stale facts</summary>

Re-check each chain file's `Checked:` date now and then.

</details>

<details>
<summary>Release</summary>

Users install from `main`, so `main` moves only at a release.

1. Set the same `X.Y.Z` in `skills/coinwallet/VERSION`, `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`.
2. Every must-pass Host × model passes the Test plan.
3. `~/.hermes/hermes-agent/venv/bin/python dev/hermes_scan.py` shows no high or critical finding.
4. `python3 dev/check_repo.py --tag vX.Y.Z` passes (it checks that the three versions match the tag).
5. Merge to `main`, tag `vX.Y.Z`, push the tag, and write GitHub Release notes (`gh release create vX.Y.Z`).

</details>
