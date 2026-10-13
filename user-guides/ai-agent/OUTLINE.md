# AI agent user guide: content outline

Status: draft for review. No pages written yet.

Two outputs:
1. **`README.md`** at the root of `CoinsDo/agentic-wallet`: the GitHub landing page. Short: what it is, a 5-step quickstart, safety in 3 lines, links to the GitBook pages. It never holds detail that lives in GitBook.
2. **GitBook pages**, sorted by [Diátaxis](https://diataxis.fr/) like the CoinWallet guide, plus an FAQ that only routes to other pages.

Reader: someone who already uses an AI agent (Claude Code, Codex, Hermes or OpenClaw), maybe through Telegram, and has never used CoinWallet.

> **Dependency:** the lean skill is still being specified (map: *Wayfinder: lean CoinWallet skill, Newbie to First transfer*). Pages marked ⏳ describe agent behavior that the spec decides. They get written after the spec, or written now and checked against it.

---

## README.md (GitHub)

- One line: let your AI agent hold one key shard of a CoinWallet MPC wallet. It can prepare and submit transfers; nothing leaves without your approval in the App.
- Works with: Claude Code · Codex · Hermes · OpenClaw
- Quickstart (5 steps, each links to GitBook): install the skill → let it set up the MCP service → create an MPC wallet in the App → give the agent the invitation code → ask for your address
- Safety, in three bullets: you approve every transfer in the App · the agent shows a one-line Send check first · the agent never resends on its own
- Links: Tutorial · How-to guides · Reference · FAQ · Report a problem

## 1. Tutorial

| Page | Purpose | Source |
|---|---|---|
| Your first transfer with an AI agent | One path, start to finish, on **Testnet**: install the skill → MCP service starts → create a 2-of-2 MPC wallet in the App → copy the invitation code into chat → agent joins and claims its shard → you claim in the App → ask "what's my XRP address?" → get test XRP → ask the agent to send 1 XRP → answer the Send check → approve in the App within 15 minutes → see it Successful | **new** 📷 (all screens captured today) ⏳ |

## 2. How-to guides

### Set up
| Page | Source |
|---|---|
| Install on Claude Code | **new** ⏳ |
| Install on Codex | **new** ⏳ |
| Install on Hermes | **new** ⏳ |
| Install on OpenClaw | **new** ⏳ |
| Run the agent on a cloud server and talk to it on Telegram | **new**, waits on ticket *Start the MCP service on a headless Linux server* ⏳ |
| Move from Testnet to Mainnet | **new** (a new Mainnet MPC wallet; Testnet is the App's hidden choice) |

### Everyday tasks
| Page | Source |
|---|---|
| Connect the agent to a new MPC wallet | **new** 📷 (invitation code, 60-min limit, agent claims, you claim) |
| Get a receiving address | **new** ⏳ |
| Check balances | **new** ⏳ |
| Send crypto through the agent | **new** 📷 (Send check in chat, then approve in the App) ⏳ |
| Send to an exchange that needs a memo or tag | **new** (which chains can and can't) |
| Approve a transfer the agent submitted | **new** 📷 (push → Activity → Require Action → Approve, 15 min) |
| Approve a transfer someone else started | **new** ⏳ (`approval_transaction`) |
| Add an address for another coin | **new** ⏳ (needs App approval) |
| Look up past transfers | **new** ⏳ |
| Work with more than one wallet | **new** ⏳ (the agent asks once which one) |

### Fixing problems
| Page | Source |
|---|---|
| The agent can't join: "no wallet still being set up" | **new** (code expired, MCP in the wrong environment) |
| I'm stuck on "Waiting for others" | **new** 📷 (the agent hasn't claimed its shard) |
| The transfer expired before I approved it | **new** |
| The agent says it can't send to this chain or token | **new** (memo-only chains, lookalike tokens) |
| Remove the agent from a wallet | **new** (in the App) |

## 3. Reference

| Page | Purpose | Source |
|---|---|---|
| What the agent can and can't do | Plain list: joins, claims, reads, adds addresses, submits transfers · never approves for you, never resends, no NFTs | **new** ⏳ |
| The Send check | Its one-line format, what each part means, how to answer (Yes/No buttons on Telegram, typed "yes" elsewhere) | **new** ⏳ |
| Supported chains, memos and minimum balances | Per chain: memo/tag support, gas coin, reserves (XRP, TRX, XLM, SOL, DOT) | **new** from research/chain-send-rules.md |
| Wallet statuses the agent sees | `""` / `PENDING_CREATION` / `CREATED` / `ONLINE`, and what to do in each | **new** 📷 |
| MCP service settings | `-e prod` vs `-e test`, port, where data and the keychain secret live | **new** |
| App buttons by language | The exact button names the agent will mention, en / zh-Hans / zh-Hant / ja | **new** 📷 (agent-screens.md, strings.md) |
| Glossary | Host, MCP service, shard, Room, invitation code, Send check, App approval, Remark | from `CONTEXT.md` |

## 4. Explanation

| Page | Purpose |
|---|---|
| How an agent can hold a key shard safely | The agent holds one shard, the threshold needs yours too, so it can never move funds alone |
| Why every transfer needs you in the App | The Send check vs App approval, and why the App is the real gate |
| What runs where | Host ↔ MCP service ↔ CoinsDo TEE ↔ your phone; what each one stores (shard, keychain secret, no chat memory) |
| Service environment vs wallet network | `prod`/`test` service vs Mainnet/Testnet wallets, and why the App needs `prod` |
| What the agent checks before it sends | Lookalike tokens, chain rules, gas coin balance, never resend |

## 5. FAQ (router)

Examples:
- Can the agent send money without me? → No → *How an agent can hold a key shard safely*
- How long do I have to approve? → 15 minutes → *Approve a transfer the agent submitted*
- Does the agent remember our past chats? → No; it reads the wallet fresh each time → *What runs where*
- Which AI models work? → … → *Install on …*
- Why does my Mac ask about the keychain? → *MCP service settings*
- Can I use it with Telegram? → *Run the agent on a cloud server…*

---

## Open points for review

1. **README home**: README for `CoinsDo/agentic-wallet` (the skill's final home), with GitBook as the full guide. OK?
2. **When to write ⏳ pages**: wait for the spec, or draft now and fix later?
3. **Languages**: English first; zh-Hans next?
