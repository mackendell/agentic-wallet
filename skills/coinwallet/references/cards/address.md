# Address card: add the next address

Add one more address for a coin the wallet already has. The new address gets the next index (…/0/1, then …/0/2).

## Steps

1. You need the wallet and the coin (and the Chain if the coin is on 2+ Chains). Ask for every missing piece in one message.
2. Call `get_addresses {walletId, pageIndex: 1, pageSize: 100}`. Find the coin: same `currencyName` or Chain code `abbreviation`. Keep its `currencyId` (not its `addressId`). Count its addresses.
   - Coin not in the list → say "I can't add <coin> to this wallet yet." Stop.
3. Call `add_address {walletId, currencyId}` once, with that `currencyId`. There is no index argument.
4. The reply:
   - `pending: 1` → tell the user: "Approve the new address in the App within 15 minutes: open the wallet, tap "Activity" (third tab, top of the wallet), then the "Add address" row under "Require Action", then "Approve". Then tell me done."
   - `success: 1` → go to step 5 now.
   - `existed: 1` → say: "This wallet service can't make a second <coin> address yet. You can add one in the App." Stop. This is the normal answer today for a coin already in the wallet.
   - `failed: 1` → tell the user in one line. Stop.
5. User says done → `get_addresses {walletId, currencyId}`. The new address is the one with the highest last number in `addressPath`. Show it: wallet, coin, Chain, Mainnet or Testnet, full address.
6. No new address yet:
   - Less than 15 minutes since step 3 → "It's still waiting for your approval in the App."
   - 15 minutes or more → "The approval time ran out, so the address was not added. Shall I ask again?" Call `add_address` again only after a yes.

## Traps

- Every `add_address` call makes a new approval request in the App. Call it once per user request.
- The user asks about the new address while it waits → say it is waiting for approval in the App. Never call `add_address` again for that.
- A timeout is silent. Nothing tells you. Only the missing address shows it.
- Read the new address id only from `get_addresses {walletId, currencyId}`. `query_address_balance` keeps saying `addressId: 0`, even after approval.
- Never call `get_currencies` or any `search_` tool here. The `currencyId` comes from `get_addresses`.
- Never call `custom_address_path` to get past `existed: 1`. Its new address never shows in `get_addresses`.

## App 2.0.31 buttons

Use the user's language column. Chinese: Simplified or Traditional from their characters; unclear → Simplified. Other languages → English. `—` → give the place only. "Activity" is English in every language.

| en | zh-Hans | zh-Hant | ja |
|---|---|---|---|
| Activity | Activity | Activity | Activity |
| Require Action | 需要操作 | 需要操作 | 必要な操作 |
| Add address | 添加地址 | — | — |
| Add currency (inside the row) | 添加币种 | — | — |
| Approve | 批准 | 批准 | 承認 |
