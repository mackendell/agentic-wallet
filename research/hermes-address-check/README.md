# Slow address check on Hermes with DeepSeek Flash

Throwaway evidence for the ticket "Reproduce the slow address check on Hermes with DeepSeek Flash".

## Setup

- Date: 2026-10-13
- Host: Hermes, one-shot mode (`hermes -z "give me my receiving address"`), isolated `HERMES_HOME` (the user's own Hermes skills untouched)
- Model: `deepseek/deepseek-v4-flash` via OpenRouter
- Skill: repo `skills/agent-wallet` + `skills/agent-wallet-mcp` at `v1.0.8.20261013.alpha` (main @ c8bb356)
- MCP service: the one already running locally, `service -t http -p 18080 -e test`, reports **v1.0.5**. Not v1.0.7 (xlsx) and not v1.0.8 (skill baseline)
- Wallets on that service: **none** (`get_wallets` returns `"null"`)

## Results

| Run | Wall | Model calls | Total tokens | Input (uncached) | Cost |
|-----|------|-------------|--------------|------------------|------|
| 1 | 48 s | 8 | 277,291 | 44,194 | $0.0108 |
| 2 | 26 s | 5 | 85,126 | 39,685 | $0.0031 |
| 3 | 33 s | 6 | 111,335 | 40,326 | $0.0040 |

No run reached an address: there is no wallet. Every run ended by telling the user to create one in the App.

## Where the time went

Run 1 timeline (`+seconds`):

- +0 → +10: `skill_view agent-wallet` (SKILL.md, 13 KB), then **workflows.md (38 KB) + runtime-api.md (53 KB) + agent-wallet-mcp/macos-keychain.md (3 KB)** in parallel. ~108 KB of skill text before any wallet call.
- +10 → +18: model reads it all (one 8 s turn).
- +18: `tool_describe` on 5 MCP tools.
- +22: batched `tool_call` with status + get_wallets → **error**: Hermes allows only one local tool per `tool_call`. Wasted turn.
- +25: `status` → ok, test env, v1.0.5.
- +28 and +36: `get_wallets` → `"null"`, **called twice with identical arguments** (8 s turn between).
- +44: final answer.

Runs 2 and 3 skipped runtime-api.md and the keychain file, so they were ~2x faster and ~3x cheaper. Same question, same model: the load path is not stable.

## Findings

1. **Skill text is the main cost.** Every run loaded SKILL.md + workflows.md (~50 KB). Run 1 also loaded runtime-api.md (53 KB). A one-line question pays for the whole manual.
2. **Load path is random.** 5 to 8 calls, 85K to 277K tokens, 26 to 48 s across three identical runs.
3. **Irrelevant file loaded.** Run 1 opened macos-keychain.md for an address question.
4. **Hermes tool quirk.** `tool_call` takes one local tool at a time; the model tried to batch and burned a turn.
5. **Retry on empty.** `get_wallets` → `"null"` was retried with identical args. `"null"` (a string) instead of `[]` may read as an error to the model.
6. **Language slips.** Run 3 told the user the service "is running on testnet" — mixing up Service environment and Wallet network. App URL varied across runs (`coinsdo.com/en` vs `coinwallet.coinsdo.com/en`).

## Not reproduced

The path **with** a wallet (get_wallets → get_addresses → maybe currency lookup, where the `"1|2"` network schema bug lives) was not reached. That needs a wallet on this service, or a prod service with one.

## Files

- `runN-transcript.md`: full message log with timings, reasoning and tool results
- `runN-usage.json`: Hermes `--usage-file` report
