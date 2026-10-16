# Address card: another address, add a token

## Another address for a coin

The user asks for another, new, next or second address for a coin (TRX, ETH, USDT…), with or without a wallet name.

1. After `get_wallets`, call no other tool: no `get_addresses`. Ask nothing, even with 2+ wallets. The reply is the same whether the wallet has the coin or not.
2. Reply with exactly this, in the user's language: "I can't add another <coin> address here. You can add it yourself in the CoinWallet App, in that wallet. Then ask me and I'll show the wallet's <coin> addresses." No coin named → say "address" for "<coin> address". Name no App buttons.
3. "Is my new address ready?" → "I didn't make an address request. Add the address in the CoinWallet App; then I can show it." Call no tool.

Never call `add_address` for a coin the wallet already has (it answers `{"existed":1}`) or `custom_address_path` (its address never shows).

## A token on the address that the wallet doesn't list

1. You need its Chain and contract. Only a name → ask for the contract. Never guess or search for it.
2. Mainnet wallet → say "I can't confirm this token is real."
3. `get_protocols {netType}` (the wallet's). Keep the `protocolId` of the Chain's token type (ERC20 on ETH, BEP20 on BSC, TRC20 on TRX). Call it even if its schema looks odd (Hermes: `tool_call {"calls": [{"name": "mcp__coinwallet__get_protocols", "arguments": {"netType": 1}}]}`). Once. Rejected or failed → reply only "I can't look up new assets with this wallet service version yet." and stop. No `mcp.py check` for this one.
4. `add_currency {protocolId, flag: "<contract>"}` once. Keep the `currencyId` it returns.
5. `add_address {walletId, currencyId}` once. Reply `{"pending":1}`.
6. Say: "Approve it in the App within 15 minutes: "Activity" → "Require Action" → "Add address" → "Approve". Then tell me done."
7. Done → `get_addresses {walletId, currencyId, pageIndex: 1, pageSize: 100}`. An item → keep its `addressId`, back to the send card. No item → under 15 minutes: "Still waiting for your approval in the App." 15 minutes or more: "The approval time ran out. Shall I ask again?" Only after a yes: step 5.

Traps:
- Never call `search_protocols`: it returns empty for ERC20.
- Never call `search_currencies` with only `flag`: it errors "either currency or currency name is required". Use the `currencyId` from `add_currency`.
- `query_address_balance` shows the balance but `addressId: 0`, also after approval. Take the id only from `get_addresses`.
- `add_address` for a token reuses the Chain's first address, so tokens already there become sendable.
- The timeout is silent. Asked while waiting → waiting for App approval; no new `add_address`.

App 2.0.31 buttons, only to approve this token request ("Activity" in all languages):

| en | zh-Hans | zh-Hant | ja |
|---|---|---|---|
| Require Action | 需要操作 | 需要操作 | 必要な操作 |
| Add address (inside: Add currency) | 添加地址 (inside: 添加币种) | — | — |
| Approve | 批准 | 批准 | 承認 |
