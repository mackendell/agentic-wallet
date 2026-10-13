# Address check with a wallet present (Hermes + DeepSeek Flash)

Throwaway evidence for the ticket "Reproduce the address check with a wallet present".

## Setup

- Date: 2026-10-13
- Host: Hermes, one-shot (`hermes -z "give me my receiving address"`), isolated `HERMES_HOME` per run, `--usage-file`
- Model: `deepseek/deepseek-v4-flash` via OpenRouter
- Skill: repo `skills/agent-wallet` + `skills/agent-wallet-mcp` at `v1.0.8.20261013.alpha` (main @ 26ec92b)
- Wallets: the two Testnet wallets from the agent-screens ticket (`agent-test`, `agent-test-2`), both ONLINE, service started `-e prod -u agenttest`
- No new Room was needed: the old service data still had both wallets.
- Two MCP versions:
  - Runs 1–3: **v1.0.5** (the binary installed on this Mac)
  - Runs 4–7: **v1.0.8** (latest GitHub release, 2026-10-09), on a copy of the same data
- Run 7 used a different prompt to force a currency lookup: "find USDT on Tron for my agent-test wallet: is it supported, and what's the contract?"

## Results

| Run | MCP | Wall | Calls | Total tokens | Cost | Got an address? |
|---|---|---|---|---|---|---|
| 1 | v1.0.5 | 32 s | 7 | 164K | $0.006 | No, asked which asset |
| 2 | v1.0.5 | 193 s | 26 | 1,188K | $0.046 | Yes, by raw `curl` to the service |
| 3 | v1.0.5 | killed at 641 s | 22 | ~1,190K | ~$0.076 | No, went off exploring the machine |
| 4 | v1.0.8 | 32 s | 6 | 189K | $0.010 | No, asked which wallet + asset (correct by the 2+ wallets rule) |
| 5 | v1.0.8 | 68 s | 9 | 326K | $0.018 | Yes (`clarify` → one-shot auto-pick) |
| 6 | v1.0.8 | 78 s | 12 | 483K | $0.027 | Yes (`clarify` → one-shot auto-pick) |
| 7 | v1.0.8 | 218 s | ~30 | — | — | Yes, but via `get_addresses`; currency lookup never worked |

## Findings

1. **v1.0.5 breaks Hermes once a wallet exists.** Every list reply (`get_wallets`, `get_addresses`, `search_chains`, `search_currencies`) puts a JSON *array* in `structuredContent`. The MCP spec says it must be an object. Hermes' MCP client (Python SDK) rejects it: `ValidationError ... structuredContent Input should be a valid dictionary ... input_type=list`. The no-wallet path worked only because `"null"` passes. **v1.0.8 fixes this** (`{"items": [...]}`).
2. **v1.0.8 still has the `"1|2"` bug, and it is fatal on Hermes.** `netType` is `{"type":"integer","enum":["1|2"]}` on 8 tools (`get_chains`, `get_currencies`, `get_protocols`, `get_nft_projects` and the four `search_*`). `nftState` is `enum ["0|1|2"]`. Hermes checks args against the schema before calling: `1`, `2` fail the enum; `"1|2"` fails the type. **No currency/chain lookup can run on Hermes.** The service itself accepts `netType: 1` fine (checked with raw JSON-RPC). Saved: `mcp-v1.0.8-tools-list.json`.
3. **When tools fail, Flash goes rogue.** Runs 2, 3 and 7 left the MCP tools and used `terminal`/`execute_code` to `ps`, `lsof`, read `~/.hermes/config.yaml`, read the MCP service logs in its data folder, raw-`curl` the service, and web-search contract addresses. Run 3 never stopped (killed at 10.7 min). The skill needs a hard "if the wallet tool fails, stop and report; never call the service another way" rule.
4. **Same waste as the no-wallet runs.** Every run loaded SKILL.md + workflows.md; 5 of 7 also loaded runtime-api.md (53 KB); runs 5–6 loaded `macos-keychain.md` for an address question. 5 of 7 batched `status` + `get_wallets` into one Hermes `tool_call` and burned a turn. `status` before `get_wallets` is a wasted call either way.
5. **Fetches every address up front.** With 2 wallets, runs 5–6 pulled `get_addresses` (pageSize 100) for *both* wallets before asking which one. The 2+ wallets rule (ask once, first) would have saved two calls and ~150K tokens.
6. **`clarify` in one-shot mode auto-picks.** Hermes answers `clarify` itself with "[oneshot mode: no user available. Pick the best option…]". Fine for these runs, but the test harness must give fixed replies (session resume), not one-shot, or the agent picks a wallet for the user.
7. **Run 1 (v1.0.5) picked a wallet from an error message.** It read `walletId: 2` from the truncated `ValidationError` text and used it without asking.
8. **Good:** when it did answer (runs 5, 6), the reply named wallet, asset, network and "testnet", and warned the sender to use the same network.

## Files

- `runN-transcript.md`: full message log with timings, reasoning, tool results
- `runN-usage.json`: Hermes `--usage-file` report (run 3 has none: killed)
- `mcp-v1.0.8-tools-list.json`: raw `tools/list` from v1.0.8
