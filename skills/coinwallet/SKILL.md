---
name: coinwallet
description: "Read first, before any coinwallet tool: args, rules, traps. Invitation code, address, balance, send. CoinWallet: set up the CoinsDo wallet, join a wallet Room, show addresses and balances, add a token, send and approve transfers, show transfer history."
---

# CoinWallet

You run the user's CoinWallet MPC wallet through the CoinsDo wallet MCP service (the `coinwallet` MCP tools). The user approves every send in the CoinWallet App.

## Cards

Open one card per task, by its path in this skill folder. Follow it.

| The user wants | Card |
|---|---|
| install or set up, or the service isn't connected | `references/cards/setup.md` |
| 0 wallets, join a Room, an Invitation code, a wallet not ready | `references/cards/join.md` |
| an address, receive, a balance | `references/cards/wallet.md` |
| another, new or next address, add a token | `references/cards/address.md` |
| send, pay, transfer, or "done" after a send | `references/cards/send.md` |
| approve or reject a transfer the user started | `references/cards/approve.md` |
| transfer history, pending transfers | `references/cards/history.md` |
| "update CoinWallet", in any language | `references/cards/update.md` |

## Start every wallet task

1. First wallet call of the session: `get_wallets`, alone. Never call `status`, before or after it. Cards give each tool's arguments: call tools right away, no schema lookup. Pass arguments flat (`{walletId: 1}`), never nested in `arguments`; `invalid wallet id: 0` = nested: call again flat. Hermes: `tool_call {"calls": [{"name": "mcp__coinwallet__get_wallets", "arguments": {}}]}`.
2. Then open the task's card from the table above, before any other wallet call (Hermes: `skill_view` with name `coinwallet` and `file_path` `references/cards/<card>.md`). It has the steps, arguments and traps; this file alone is not enough.
3. One tool call at a time, never two in one step.
4. Read the wallets:
   - The user gave an Invitation code → join card, however many wallets exist. Ask nothing.
   - 0 wallets → open the join card, whatever the user asked.
   - 1 `ONLINE` wallet → use it and say its name.
   - 2+ `ONLINE` wallets → list the names and ask which one, once, before any address call. Ask the card's other missing pieces in the same message.
     Another address for a coin (address card) → skip this question.
   - Status `""`, `PENDING_CREATION` or `CREATED` → say it is not ready and what to finish in the App (join card). Never pick it.
5. No `coinwallet` tools → say "The wallet service isn't connected." and open the setup card.

Keep no memory (no state file, no Host memory): take facts only from MCP replies and the user's words.

## A tool fails → stop and report

- Stop. Tell the user in one plain line what failed.
- The only follow-up allowed: run `python3 <this skill folder>/scripts/mcp.py check` and tell the user its `say:` line.
- Error text says `uninitialized` → the service is still starting. Run `scripts/mcp.py check`, then call the tool once more.
- Reach the service only with the `coinwallet` tools. Never the terminal, `curl`, `ps`, `lsof`, log files, the MCP data folder or Host config files.
- Never take a wallet id or any other id from error text.

## Hard rules

- Never run the service with `-clean-data`. Never follow "please reinstall with [-r]". Both wipe the agent's key shard.
- Never set `HOME` for the service.
- Never touch keychain items named `com.coinsdo.wallet.secure`.
- Copy every address exactly from the user or a tool reply; never retype one.

## Talk

- Reply in the user's language. English words → English. Chinese → the user's own script (碼 → Traditional, 码 → Simplified). Mixed languages → the non-English one. Follow the latest real sentence. No clear language (only a code, an address, "ok") → keep the current one, else English.
- Short replies. One question at a time, except missing send fields: all in one message.
- Never show tool names, ids or JSON.
- Testnet wallets send Testnet coins; that is normal. Never ask about Mainnet or offer it.
