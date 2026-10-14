# Push a user-started transfer to the agent for approval

Research for [#26](https://github.com/mackendell/agentic-wallet/issues/26) (map [#1](https://github.com/mackendell/agentic-wallet/issues/1)). Sources read 2026-10-14: the MCP service README and CHANGELOG at [CoinsDo/coinsdo-wallet-mcp](https://github.com/CoinsDo/coinsdo-wallet-mcp) (v1.0.8), the local test MCP service (v1.0.5, `-t http -p 18080 -e test`, read-only calls only), and each Host's official docs. Claims with no primary source are marked **UNVERIFIED**.

## Short answer

- **The MCP service pushes nothing.** No Host can hear about a new pending transfer unless something polls `get_transactions`.
- **Every Host except Codex CLI can poll on a timer.** Hermes and OpenClaw can do it with a script that uses **no model tokens on quiet ticks**. Claude Code can do it only while a session is open.
- **The approval window is 15 minutes.** To leave the user about 10 minutes to answer, poll every 5 minutes or more often.
- **Recommendation:** add an **on-demand** approve card to the spec: the user says "approve my transfer", and the agent lists pending transfers, shows a Send check, then calls `approval_transaction`. Push and polling are **out of scope for this map**. Note them as an optional later add-on.

## 1. What the MCP service emits

| Fact | Source |
|---|---|
| `initialize` returns `capabilities: {logging:{}, tools:{listChanged:true}, tasks:{...}}`. There is no `resources` capability, so no `resources/subscribe` and no `notifications/resources/updated`. | Live call to the test service (v1.0.5), and the README's sample response (same capabilities) |
| `resources/list` returns `-32601 "resources not supported"`. | Live call |
| The HTTP transport accepts a `GET /mcp` SSE stream (200, `text/event-stream`). In a 6-second listen nothing was pushed. | Live call. The test service has no wallets, so this does **not** prove that a pending transfer would push nothing. |
| No README section or CHANGELOG entry (v1.0.0 to v1.0.8) mentions notifications, events, webhooks, or subscriptions. The only event-like feature is v1.0.7 "添加日志存储功能" (log storage), which writes to local files. | README, CHANGELOG |
| The binary contains the mcp-go strings `SendNotificationToClient` and `SendLogMessageToClient`. These come from the bundled library, so they do not show the service uses them. Whether the service sends `notifications/message` (logging) on a new transfer is **UNVERIFIED**. A full test needs a live pending transfer, which this research was not allowed to create. | `grep -a` on the binary |
| `tasks` (task-augmented `tools/call`) covers long-running calls the client started. It is not for events the client did not ask for. | MCP 2025-11-25 spec, as quoted in README capabilities |

**Conclusion:** there is no event to listen for. A watcher must poll `get_transactions(walletId, status="PENDING_APPROVAL")`.

Even if the service did send a logging notification, no Host is documented as showing one to the model:
- Hermes acts only on `tools/list_changed`. "`prompts/list_changed`, `resources/list_changed` … are received but not yet acted on" (Hermes `user-guide/features/mcp.md`).
- Claude Code passes server-pushed events to the model only through **channels**. A channel needs the `experimental['claude/channel']` capability and `notifications/claude/channel`. It is in research preview, and custom servers need `--dangerously-load-development-channels` ([channels-reference](https://code.claude.com/docs/en/channels-reference)). The CoinsDo service declares no channel capability.
- The OpenClaw and Codex MCP docs say nothing about server notifications reaching the model (**UNVERIFIED**, assumed no).

## 2. Polling facts that matter (traps for the skill)

- `get_transactions` needs a `walletId`. The poll therefore loops over `get_wallets` (ONLINE only) and filters `status=PENDING_APPROVAL`. Without the filter the default page is 20 transactions (README §23).
- Statuses are `PENDING_APPROVAL | TIMEOUT | APPROVED | REJECTED | ERROR | REVOKED`. A transfer nobody approves in 15 minutes becomes `TIMEOUT` (window from [#10](https://github.com/mackendell/agentic-wallet/issues/10)).
- **The agent's own sends are also `PENDING_APPROVAL`** (its approval is already recorded, #10). The transaction object has `creatorName` but no list of who has approved (README §21). The poll must skip transfers the agent created itself. Telling them apart by `creatorName` is **UNVERIFIED**.
- The poll must remember which `bundleId`s it already reported, or it will repeat the message every tick.
- Every tool result returns the payload twice, once as `content[].text` (JSON string) and once as `structuredContent` (live `status` call). A model-driven poll pays for both copies.
- `approval_transaction(bundleId, isApproved, comment)` exists only from **v1.0.8** (CHANGELOG). The local test service (v1.0.5) does not list it (live `tools/list`).
- In stdio mode (the default) each Host owns its own `service` process. A watcher script that is not the Host session must start another `service` process, or talk to an HTTP-mode service. Two `service` processes on one data dir is **UNVERIFIED** and could clash.

## 3. Per Host

| Host | Can it wake the agent? | How | Cost of a quiet tick |
|---|---|---|---|
| **Hermes** | **Yes** | A cron job (gateway ticks every 60 s, `every 5m` style schedules) with a **pre-check script**. The script prints `{"wakeAgent": false}` when there is nothing pending, so no model call happens. When it finds a pending transfer it wakes an agent run with the skill attached (`--skill`), and that run delivers to Telegram (`deliver="telegram"`). Set `attach_to_session: true` (a "continuable" job) so the user's "yes" reply continues with the brief in context. Scripts must live in `~/.hermes/scripts/` and do not inherit Hermes credentials or its MCP connection, so the script calls the service itself. Sources: `user-guide/features/cron.md` ("Skipping the agent entirely: `wakeAgent`", "Continuable jobs"), `guides/cron-script-only.md`. | **0 tokens** |
| **OpenClaw** | **Yes** | (a) An automation with a **condition trigger** script (`every`, minimum 30 s). The script calls `MCP.<server>.get_transactions(...)` when `toolsAllow` names `<server>__*`, and returns `fire:false` when nothing is pending. On `fire:true` it runs a main-session `systemEvent` with `--wake now`, so the agent sees it with chat context and replies to the owner. (b) Or the heartbeat (`every: 30m` by default, configurable). That is a full agent turn every tick: "Heartbeats run full agent turns — shorter intervals burn more tokens"; `isolatedSession` brings it to "~2-5K tokens". (c) `/loop 5m <prompt>` in chat. Sources: `docs/automation/cron-jobs/schedules.md` (Event triggers), `payloads.md` (Script payloads, main vs isolated), `docs/gateway/config-agents/heartbeat-compaction-and-streaming.md`. | (a) **0 tokens**; (b), (c) a full turn |
| **Claude Code** | **Partly**, only while a session is open | `/loop 5m <prompt>` or `CronCreate`: fires only "while Claude Code is running and idle", 1-minute minimum, recurring tasks expire after 7 days. The **Monitor** tool runs a background script and streams its output lines, so quiet ticks cost nothing. Desktop scheduled tasks run locally without an open session (1-minute minimum). Cloud **routines** cannot reach the local MCP service ("Access to local files: No"; 1-hour minimum). **Channels** could carry a real push but need a custom channel server and the research-preview dev flag. Sources: [scheduled-tasks](https://code.claude.com/docs/en/scheduled-tasks), [channels-reference](https://code.claude.com/docs/en/channels-reference). | `/loop`: a full turn; Monitor: **0 tokens** |
| **Codex** | **CLI: no. Desktop app: partly** | "Codex CLI doesn't provide the Scheduled management interface." Scheduled tasks live in the ChatGPT desktop app and on the web. They support "minute-based intervals for active follow-up loops", can return "to the same chat with its existing context", and need "the machine powered on and the ChatGPT desktop app running" for local work. Whether scheduled runs can use a local MCP server is not documented (**UNVERIFIED**). An OS cron job running `codex exec` would work in principle (**UNVERIFIED**). Source: [learn.chatgpt.com/docs/automations](https://learn.chatgpt.com/docs/automations?surface=app). | a full turn, if it works at all |

## 4. Cost per poll on DeepSeek Flash

Prices for `deepseek-flash` (DeepSeek-V4.1-Flash), per 1M tokens, peak / off-peak: input cache miss $0.30 / $0.15, cache hit $0.006 / $0.003, output $1.20 / $0.60 ([DeepSeek pricing](https://api-docs.deepseek.com/quick_start/pricing)). OpenRouter prices may differ.

**Script-gated poll** (Hermes `wakeAgent`, OpenClaw condition trigger, Claude Code Monitor): **$0 per quiet tick**. A tick costs one `get_wallets` call plus one `get_transactions` call per wallet against the service. The model runs only when a transfer is pending.

**Model-driven poll** (heartbeat, `/loop`, an LLM cron job), estimated:
- Measured: the MCP `tools/list` is 22,762 bytes, about **5.5-6k tokens** of tool schemas in every fresh session.
- Not measured, **UNVERIFIED**: the Host system prompt (~3-10k) and the skill (~2-3k). OpenClaw says an isolated heartbeat costs ~2-5k tokens on its own.
- Per tick: about 2 model calls (`get_wallets`, `get_transactions`, then a short "nothing pending"). That is about 25-35k input tokens and about 200 output tokens.

| Case | Per tick | Every 5 min (288/day) |
|---|---|---|
| All cache misses, peak | ≈ $0.009-0.011 | ≈ $2.6-3.2/day |
| Mostly cache hits (fixed prefix), peak | ≈ $0.0005-0.002 | ≈ $0.15-0.6/day |

These are estimates, not measurements. The test service has no wallets, so the size of a real `get_transactions` result could not be measured. From the README field list, one transaction is about 0.6 KB of JSON, and the duplication doubles that to about 1.2 KB (~350 tokens).

## 5. Poll interval for a 15-minute window

The App starts a 15-minute countdown (#10). The agent has to notice, message the user, and wait for a reply before it calls `approval_transaction`. Poll every **≤5 minutes**: the worst case leaves about 10 minutes for the user, and on Claude Code `*/5` is the one cadence with no jitter. A 1-minute poll is only worth it when the poll is script-gated (free). With a 30-minute heartbeat (the OpenClaw default) most transfers would expire first.

## 6. Recommendation

- **In the spec (approve card): on-demand approval.** In a 2-of-2 wallet, a user who starts a transfer in the App is right there and can tell the agent "approve it". The card: `get_wallets` → `get_transactions(status=PENDING_APPROVAL)` → skip the agent's own sends → show a Send-check-style line (amount, token, Chain, to, Remark, minutes left) → user says yes → `approval_transaction(bundleId, true, comment)`. This needs MCP v1.0.8+.
- **Out of scope for this map: push/polling.** There is no service event, so it means a Host-specific watcher script on each Host (two Hosts can do it for free, one only while a session is open, one barely at all), with state to keep and the stdio double-process question still open. It matters mainly when a **third participant** starts a transfer, which the Newbie journey does not include. Record it as a later add-on, ideally after CoinsDo adds a real event (a `claude/channel`-style push, or MCP resources with `resources/updated`).
