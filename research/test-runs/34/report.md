# #34 Test plan report: CoinWallet skill v0.1.0 on MCP v1.0.9

Dates: 2026-10-19 → 2026-10-22. Skill: this branch, last card change e041ec5; runs install it with `--source local`. MCP v1.0.9 is the release evidence; the switch was 2026-10-20 10:16. Earlier runs on v1.0.8, including round 1 from GitHub `main`, are history only.

Every run is counted as one of:
- **PASS**
- **FAIL**
- **HOST_ERROR:** the Host failed before the model ran.
- **VOID:** a harness or outside problem; the reason is written in the record.

Raw data: `raw/*.jsonl` (all fields) and `runs.jsonl`. Each row has: case, Host + model, language, prompt, short reply, calls/secs/tokens target vs actual, cost, result, transcript path, fail reason, MCP version, skill commit.

## Matrix on MCP v1.0.9

| Host + model | Runs | PASS | FAIL | HOST_ERROR | VOID | Address miscopies | Cost |
|---|---|---|---|---|---|---|---|
| Claude Code + Sonnet (subscription) | 82 | 79 | 3 | 0 | 0 | 0 | ≈$33 list price, all rounds (paid by subscription) |
| Hermes + DeepSeek v4.1 Flash | 244 | 220 | 22 | 0 | 2 | 3 (2 refused by the 1.0.9 checksum check, 1 in a reply) | $0.54 |
| OpenClaw + DeepSeek v4.1 Flash (thinkingDefault medium) | 250 | 218 | 28 | 1 | 3 | 1 | $1.74 |
| Hermes + Sonnet (OpenRouter) | 40 | 37 | 1 | 0 | 2 | 0 | $6.25 (all rounds) |
| Codex + default | — | — | — | — | 3 | — | — |

- **Hermes + Sonnet:** dropped by user decision (cost); a partial lane. Never run on 1.0.9: send, approve, busy-send, token, M9 and the reruns after 9927970.
- **Codex:** skipped on 1.0.9 because of the workspace spend cap. Its 1.0.8 history is 45/50 PASS, with 1 address miscopy (a history reply dropped a "k"). Retest planned for November 2026.
- **DeepSeek v4 Flash on 1.0.9** (Hermes 9/9, OpenClaw 8/9): the first round before the switch to v4.1; history only.

### Latest round per case (release evidence)

Flash lanes ran each case 3 times, Claude Code once. Each cell is PASS/runs for the case's latest round.

| Case | Claude Code + Sonnet | Hermes + v4.1 | OpenClaw + v4.1 |
|---|---|---|---|
| 1 setup | 1/1 | 3/3 | 2/3 + 1 host error |
| update (1.0.8 → 1.0.9) | 1/1 (+1/1 popup path) | 2/3 (+1/1 popup path) | 2/3 (+1/1 popup path) |
| 2 fresh | 1/1 | 3/3 | 3/3 |
| 3 join (join-dry) | 1/1 | 3/3 | 3/3 |
| 4 addresses | 1/1 | 3/3 | 3/3 |
| 5 add-address | 1/1 | 3/3 | 3/3 |
| 6 send (phone) | 1/1 | 3/3 | 3/3 |
| 7 traps tron/xrp/xlm/sol/btc/gas | 6/6 | 17/18 | 18/18 |
| 8 approve (phone) | 1/1 | 2/3 | 3/3 |
| 9 history | 1/1 | 3/3 | 3/3 |
| 10 token | 1/1 | 6/6 | 3/3 |
| 11 reject (phone) | 1/1 | 3/3 (+1 unplanned PASS) | 1/3 |
| 12 lookalike (Mainnet) | 1/1 | 3/3 | 3/3 |
| approve-dry / -own, busy-send | 3/3 | 8/9 | 8/9 |
| M1–M8, M10–M18 | 16/17 | 47/51 | 46/51 |
| M7 (phone) | 1/1 | 2/3 | 3/3 |
| M9 whole Newbie journey (phone) | 1/1 | 1/1 | 1/1 |

Fails in the latest rounds:
- **Claude Code, M4:** Sonnet narrated the half code ("Code "4B6B" has 4 characters") before the fixed line.
- **Hermes + v4.1:**
  - update 1/3: updated without asking first.
  - trap-xlm 1/3: no memo line.
  - M1 1/3: asked without a question mark.
  - M3 1/3: an address near-copy in a reply.
  - M18 1/3: a balance call before asking for the re-paste.
  - approve 1/3: ran `pwd; ls -la`.
  - busy-send 1/3: ran Python to decode bundleId times.
  - M7 1/3: miscopied the recipient (dropped the last "P"). The 1.0.9 checksum check refused the send, so nothing was sent.
- **OpenClaw + v4.1:**
  - setup: 1 host error (CLI lane timeout before the model ran).
  - update 1/3: didn't ask first.
  - M4 0/3: Simplified reply to a Traditional user.
  - M2 1/3: English reply to a Japanese user.
  - M18 1/3: a balance call before asking.
  - busy-send 1/3: empty reply after an OpenClaw internal error.
  - reject, 2 fails: round 1 sent again after an argument error (fixed in 71abb77); round 2 said "Rejected" instead of REJECTED.

### Budgets (worst run of the latest round vs target)

- **Hermes + v4.1:** inside the call and token budgets on most cases; over on setup (12–30 calls vs 10).
- **OpenClaw:** over on calls almost everywhere (+2 to +19), because every MCP call goes through tool_search / tool_describe / tool_call.
- **Claude Code:** over on tokens, because Claude Code counts cached context.
- **M9, against 26 calls / 265 s / 520K tokens:** Hermes 13 / 62 s / 416K, OpenClaw 22 / 126 s / 521K, Claude Code 18 / 123 s / 1168K.

Per-case numbers are in `runs.jsonl`.

## Persona sweep (Hermes + Flash, 5 personas, at most 10 turns; Sonnet driver via Claude Code subscription)

On 1.0.8 + v4 it found three traps, each now an M-case with a card fix:
- **M16:** after a balance error, the user said "the App shows 50 XRP, send". The agent re-ran setup, rewrote the Host config and tried to send.
- **M17:** the agent turned into a WeChat transfer tutor.
- **M18:** it accepted a recipient address with a space in it.

Rerun on 1.0.9 + v4.1: no new traps. Every blocked send got a fresh Send check, and the agent stopped correctly on 0 TRX and on balance errors.

## MCP v1.0.9 checks

- **P0 #3 is fixed:** send_transaction refuses an XRP address with one letter miscopied ("checksum mismatch"). A real Hermes M7 miscopy was stopped this way.
- **Downgrade round trip on own33 passed:** 1.0.9 → 1.0.8 (`mcp.py fallback`) → get_wallets ONLINE → Testnet send APPROVED → back to 1.0.9. One keychain popup, at the fallback step.
- **Update 1.0.8 → 1.0.9 on the real one-account path:** 3/3 PASS. There is one popup per account, from /usr/bin/security. The update finished before the popup was answered, and the service works after "Allow".
- **Linux:** the service makes and keeps its own key in `<data>/.key/master.key`; `<data>` follows $XDG_CONFIG_HOME, else $HOME/.config. tests/test_mcp_cli.py: macOS 23 OK (5 skipped); Docker arm64 and amd64, each with and without /etc/machine-id, 23 OK each.

## Known issues (v0.1.0 ships on MCP 1.0.9 with these)

1. **P0, MCP 1.0.9, macOS keychain.**
   - **Finding:** any process running as the user can read the agent's secret (`com.coinsdo.wallet.secure`) with no prompt.
   - **Tests:** a fresh 1.0.9 install (test A) and a 1.0.8 → 1.0.9 migration with "Allow" clicked (test B). In both, `security find-generic-password -s com.coinsdo.wallet.secure -a <account> -w` returned the 32-byte secret. On 1.0.8 the same read prompted.
   - **Impact:** sends still need App approval.
   - **Next:** reported to the MCP dev in Chinese and English (bug-list items 19–21). Moving to the fixed MCP is the first maintenance update.
2. **P1, MCP 1.0.9, macOS:** 1 in 10 fresh setups failed its second start with ErrLocalPasswordError, and the account stayed broken. 0 of 6 deliberate repros failed. The keychain item appeared 40 s after the failure.
3. **Hermes + v4.1:** in M9, after an English question ("What's my XRP address?"), the agent kept answering in Chinese, against the "follow the latest real sentence" rule. The check doesn't catch this.
4. **OpenClaw + v4.1:** at OpenClaw's default thinking level it leaks its reasoning into the reply and joined with a half Invitation code (M4 0/6). With `openclaw config set agents.defaults.thinkingDefault medium` (now a README tip) M4 passed 3/3 once. In the final rounds it still answers M4 in Simplified to a Traditional user (0/3).
5. **OpenClaw host errors:** the CLI can stop with "CommandLaneTaskTimeoutError … no progress" or "OpenClaw state ownership … could not be …". Runs that had already used model tokens count as FAIL; runs with 0 tokens count as HOST_ERROR.
6. **Claude Code + Sonnet:** sometimes narrates its reasoning in the reply (M4 quoted the half code).
7. **Codex:** not tested on 1.0.9 (spend cap). Retest in November 2026.
8. **XLM memo:** 1.0.9's `send_transaction` memo description lists Stellar, but the skill still stops on Stellar memos until the MCP dev confirms memos work.

## Card and skill changes during #34

Each change was followed by a rerun of the affected cases, and both rounds are counted.

- **Join card** (480ab3a, 928373a, efd5ebd, 6ccabef, d7a668c, 847cc32, 56dd5d2, 3e6d321): count the code's characters silently first. A wrong-length code gets one fixed line, with nothing before it and a zh-Hant version. Copy the App steps exactly, in the user's language only.
- **SKILL.md:**
  - flat tool arguments and the OpenClaw `tool_call` format (8ff445a, a83a0a6)
  - never write an Invitation code back (2f8323a)
  - the language rule at the top, with English → English and 码/钱/这 → Simplified vs 碼/錢/這 → Traditional (69e2acc, 3e6d321, 190595e, 9927970)
  - never check an address with code (190595e)
  - CoinWallet tasks only; re-paste a spaced address; never reinstall after an error (d51c9c7)
  - "First wallet call"; 0 wallets → join card except for update/setup (8765f2e, b57a814)
  - never touch `.key/` (29d0b5f)
- **Send card** (80a6452, d51c9c7, 71abb77): a balance error → stop, never send on the user's word; the Send check only after a balance; `amount` is a string.
- **Address card** (cf8ec4a, dee418e, f96e45f): for 1.0.9, get_protocols works on Hermes and add_address status comes from get_gen_address_requests; the obsolete traps are removed.
- **Update and setup cards, mcp.py** (b57a814, e041ec5, 3378b83, 29d0b5f): ask before any command; "Allow", not "Always Allow"; a user-requested fallback says so; Linux keys for 1.0.9.
- **mcp-tested.json** (9c70e58): v1.0.9 added and the minimum raised to v1.0.9.
- **README** (from the README branch: 273217f, fb4d718, f83ba5f): install means skill plus service, neutral "Install steps" wording, the Codex plugin command only, the OpenClaw thinking tip, the keychain known issue.

## Harness changes (dev/ and tests/, not shipped)

- **New runner support:** `host_runner.py` now runs every case on OpenClaw, Claude Code and Codex. New cases: M1, M8, M9, M16–M18.
- **Fixtures:** fix34-a and fix34-b replace the lost agenttest wallets. A service stub makes `mcp.py check` answer "running in your Host". The proxy has `--fail-tool` to inject errors.
- **Check and runner fixes:** case 11 now needs REJECTED (a TIMEOUT used to pass); the runners read the wallet state after M9; Codex "at capacity" turns are retried.
- **Rescored records:** text checks (zh-Hans detection, curly apostrophe, Chinese requests without a question mark) were rescored, and each rescored record is marked "rescored".
