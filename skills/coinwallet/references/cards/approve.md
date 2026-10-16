# Approve card: a transfer the user started

Only when the user asks you to approve (or reject) a transfer they started in the App.

1. `get_transactions {walletId, pageIndex: 1, pageSize: 20}` once. Keep items with `status` "PENDING_APPROVAL" and `creatorName` not "agent" (skip your own sends).
   - None → "No transfer is waiting for approval." Stop.
   - 2+ → list them (amount, asset, full `toAddress`) and ask which one.
2. `get_transaction {bundleId}` for the one picked. Still `PENDING_APPROVAL`, else say its status and stop.
3. Approve check, one message: "Approve: <amount> <asset> · <Testnet or Mainnet> · wallet <name> · to <full toAddress> · started by <creatorName>. Reply yes to approve."
4. Yes = a plain yes, nothing added, any language (yes, ok, 好的, はい, 네). Anything else → ask again.
   Have `clarify` or `ask_user`? Ask with it, choices exactly `Yes` and `No`. Approve only if `user_response` is exactly `Yes`. Any other reply ("no user available", "best option", time-out): nobody answered. Never pick for the user. End your turn with the full approve check as text, ending "Reply yes to approve." (not "approve it in the App").
5. `get_wallet {walletId}`: `status` must be `ONLINE`, else stop.
6. `approval_transaction {bundleId, isApproved: true, comment: "<short note>"}` once.
7. Say: "Approved. It goes out once it has every approval the wallet needs (2 of 2 by default). Tell me done to see the hash."

Reject: only when the user asks. Same steps with "Reply yes to reject." and `isApproved: false`.

## Traps

- Never pass `status` to `get_transactions`: Hermes rejects it. Filter the reply yourself.
- `get_transactions` needs `pageIndex: 1` and `pageSize`. Without them: "page index must be greater than 0" or "page size must be between 1 and 100".
- An item has no time and no Chain. Name the asset by `currencyName`; `currency` is its type (ERC20, TRC20, XRP).
- `approval_transaction` errors, or its reply says `status: "ERROR"` (seen live) → never call it again. Say "Status: ERROR"; nothing was sent. Call `get_transactions` once if unsure.
- A transfer expires (`TIMEOUT`) 15 minutes after it was started. Never approve one that is not `PENDING_APPROVAL`.

## App 2.0.31 buttons

Use the user's language column. Chinese: script from their characters; unclear → Simplified. Other languages → English.

| en | zh-Hans | zh-Hant | ja |
|---|---|---|---|
| Activity | Activity | Activity | Activity |
| Require Action | 需要操作 | 需要操作 | 必要な操作 |
| Pending | 待审批 | 待審批 | 未確認 |
| Approve | 批准 | 批准 | 承認 |
| Reject | 拒绝 | 拒絕 | 拒否 |

ja shows a pending transfer as 未確認 ("unconfirmed"), not "pending approval".
