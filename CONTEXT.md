# CoinWallet Agent Skill

Skills that let an AI agent operate a CoinWallet MPC wallet through the CoinsDo wallet MCP service.

## Language

**Newbie**:
A person who already runs a **Host** but has no CoinWallet App, no skill, and no MCP service yet.
_Avoid_: beginner, new user

**Host**:
The AI agent program the skill is installed into: Claude Code, Codex, Hermes or OpenClaw.
_Avoid_: client, platform

**Target model**:
The language model driving a **Host** that the skill must work well on. The bar is set by the weakest one in use (Sonnet, and cheap or free OpenRouter models such as Nemotron and DeepSeek Flash).

**MCP service**:
The CoinsDo wallet program the **Host** talks to: a thin layer over MPC wallet functions, installed from the coinsdo-wallet-mcp GitHub releases. It keeps no agent or task memory. It is started in one **Service environment**.
_Avoid_: server, backend

**Service environment**:
`test` or `prod`, fixed when the **MCP service** starts. Not the same as **Wallet network**.

**Wallet network**:
Testnet or Mainnet, a property of each wallet (`netType`). One **Service environment** can hold wallets of both networks.
_Avoid_: env, chain

**Room**:
A wallet being set up in the CoinWallet App before creation is complete. The agent joins a room with an **Invitation code**.

**MPC wallet**:
The only kind of wallet the agent can work in. Created in the CoinWallet App; the agent is one participant.

**Invitation code**:
The code the wallet creator copies from the App so the agent can join a **Room**. Never repeated or stored.

**First transfer**:
The end of the **Newbie** journey: the agent submits a transfer from a Mainnet wallet and the user approves it in the App. Mainnet, because the App shows only Mainnet until the user finds a hidden Testnet switch.

**Approval threshold**:
How many participants must approve a transfer in an **MPC wallet** before it goes out; chosen when the wallet is made, never less than 2 of 2. Whoever submits a transfer approves it with their own shard at the same moment.
_Avoid_: signatures, quorum

**App approval**:
A user approving a pending transfer or new address in the CoinWallet App. The real human gate on every agent send. A new address needs it because the user's key shard is needed to compute it.

**Send check**:
The one-line summary the agent shows in chat, and the user's yes, before every transfer it submits, whether the user or the agent thought of it.
_Avoid_: review, confirmation

**Gas coin**:
The native coin of a chain that pays its network fees (TRX on Tron, ETH on Ethereum).
_Avoid_: fee token

**Remark**:
A note the agent attaches to a transfer (the MCP `comment`). Kept off-chain.
_Avoid_: memo (a memo or tag goes on-chain, e.g. an XRP destination tag)

**Task budget**:
The most tool calls, seconds and tokens a task may use on a **Target model** before it counts as failed.

## Relationships

- A **Host** connects to one **MCP service**; the **MCP service** runs in one **Service environment**
- A **Service environment** holds wallets of either **Wallet network**
- A **Room** becomes a wallet once the creator finishes creation in the App
- The agent's instructions name App buttons in the user's language, using the exact text the App shows in that language
- Every task in the **Newbie** journey has a **Task budget**
- A new address added by the agent needs **App approval** before it can be used
- An agent send needs a **Send check** in chat, then **App approval** from the user and any other participants up to the **Approval threshold**

## Flagged ambiguities

- "testnet/mainnet" was used for both the **Service environment** (startup flag) and the **Wallet network** (App toggle). These are different: the xlsx shows a Mainnet wallet in the test **Service environment**.
