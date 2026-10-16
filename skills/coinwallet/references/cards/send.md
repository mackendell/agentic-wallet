# Send card

Chain files in `references/chains/`, by `abbreviation`: ETH, BSC, POL, ARB1, OP, BASE → evm.md; BTC, LTC, DOGE → utxo.md; TRX → tron.md; XRP → xrp.md; SOL → sol.md; XLM → xlm.md.

1. `get_addresses {walletId, pageIndex: 1, pageSize: 100}`.
2. Chain (`abbreviation`) not listed → "I can't send on <Chain> yet. Send it from the App." Stop. Else read its chain file, even if the asset is missing, and apply all its rules (stops first).
3. Asset not in the list: a token with a contract → open the address card now (token part), no other tool first. A coin → "Add <coin> in the App first." Stop.
4. Ask all missing at once: amount, recipient, Chain (asset on 2+ Chains), the chain file's tag/memo question (never assume "no tag"). Never guess amount or recipient. Amount: a plain positive number ("all", "1,000" → ask).
5. Mainnet (`netType` 2) only: a real token's name in the chain file, other `flag` → "This looks fake. Remove it in the App." Stop. Unlisted name → allowed; Send check adds its full contract and "I can't confirm this token is real".
6. Gas coin: `get_address_balance {addressId}` of its item. 0 → "Your <Chain> address <full address> has 0 <gas coin>. Send some <gas coin> to this address first, then tell me." Stop.
7. Send check, one message: "<amount> <asset> · <Chain> <Testnet or Mainnet> · from <wallet> · to <full recipient> · <Tag/Memo line> · Remark: <your short note> · Fee: shown in the App when you approve. Reply yes to send."
8. Yes = a plain yes, nothing added, any language (yes, ok, 好的, はい, 네). Yes plus a change ("yes but 5") is no yes: new Send check, send nothing. Else ("hmm", emoji) ask again: "Reply yes to send."
   Have `clarify` or `ask_user`? Ask the Send check with it, choices exactly `Yes` and `No`. Send only if `user_response` is exactly `Yes`. Other replies ("no user available"): nobody answered. End your turn with the Send check as text.
9. `get_wallet {walletId}`: `status` must be `ONLINE`, else stop.
10. `send_transaction {addressId, toAddress, amount, comment}` once (`memo` only with a tag). Say: "Submitted. In the App: "Activity" → "Pending" → "Approve" within 15 minutes, then tell me done. It needs all approvals you set (2 of 2 by default)."

## After the send

- Reply `txHash: ""`, `netType: 0`: fine; keep `bundleId`.
- Error or no reply → never resend. `get_transactions`, say what is there.
- "done" → `get_transactions {walletId, pageIndex: 1, pageSize: 20}` once, no `status` (Hermes rejects it); match `bundleId` (fresh chat: newest by "agent"; 2+ new: ask). `APPROVED` → "Sent: <txHash exactly>" + the chain file's Explorer link. Never "arrived". `PENDING_APPROVAL` → "Not approved yet. You have until <send time + 15 min>." Other word (`TIMEOUT`, `REJECTED`) → show it; nothing was sent; never resend.
- Changed mind → "Tap "Reject" in the App, or let 15 minutes pass." You reject only if asked, after a yes.

App 2.0.31: Pending = 待审批/待審批/ja 未確認. Approve = 批准/ja 承認. Reject = 拒绝/拒絕/ja 拒否.
