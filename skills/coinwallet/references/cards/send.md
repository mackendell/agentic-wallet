# Send card

Chain files in `references/chains/`, by `abbreviation`: ETH, BSC, POL, ARB1, OP, BASE → evm.md; BTC, LTC, DOGE → utxo.md; TRX → tron.md; XRP → xrp.md; SOL → sol.md; XLM → xlm.md.

1. `get_addresses {walletId, pageIndex: 1, pageSize: 100}`.
2. Chain not listed → "I can't send on <Chain> yet. Send it from the App." Stop. Else read its chain file, even if the asset is missing; apply its rules (stops first).
3. Asset not in the list: a token with a contract → open the address card now (token part), no tool first. A coin → "Add <coin> in the App first." Stop.
4. Ask all missing at once: amount, recipient, Chain (asset on 2+ Chains), the chain file's tag/memo question (never assume none). Never guess amount, recipient. Amount: a plain positive number ("all", "1,000" → ask).
5. Mainnet (`netType` 2): a real token's name in the chain file, other `flag` → "This looks fake. Remove it in the App." Stop. Unlisted name → allowed; Send check adds its full contract and "I can't confirm this token is real".
6. Gas coin: `get_address_balance {addressId}`. 0 → "Your <Chain> address <full address> has 0 <gas coin>. Send some <gas coin> to this address first, then tell me." Stop.
7. Send check, one message: "<amount> <asset> · <Chain> <Testnet or Mainnet> · from <wallet> · to <full recipient> · <Tag/Memo line> · Remark: <your short note> · Fee: shown in the App when you approve. Reply yes to send."
8. Yes = plain yes alone, any language (yes, ok, 好的, はい, 네). Yes plus a change ("yes but 5") is no yes: new Send check, send nothing. Else ("hmm", emoji) ask again in their language.
   Have `clarify`/`ask_user`? Ask the Send check with it, choices `Yes`, `No`. Send only if `user_response` is exactly `Yes`. "No user available…" = nobody answered: never pick Yes; end your turn with the full Send check as text with its yes line.
9. `get_wallet {walletId}`: `status` must be `ONLINE`, else stop.
10. `send_transaction {addressId, toAddress, amount, comment}` once (`memo` only with a tag). Say: "Submitted. In the App: "Activity" → "Pending" → "Approve" within 15 minutes, then tell me done. It needs every approval your wallet requires."

## After the send

- Reply `txHash: ""`, `netType: 0`: fine. Keep `bundleId`.
- Error or empty reply → never resend; `get_transactions`, say what's there. `ErrCodeTee6080`: a transfer still waits: approve or reject it in the App first.
- "done" → `get_transactions {walletId, pageIndex: 1, pageSize: 20}` once, no `status`; match `bundleId` (fresh chat: newest by "agent"; 2+ new: ask). `APPROVED` → "Sent: <txHash exactly>" + Explorer link. Never "arrived". `PENDING_APPROVAL` → "Not approved yet. You have until <send time + 15 min>." Other word (`TIMEOUT`; `REJECTED`: user hit Reject) → "Status: <word>"; nothing sent; never resend.
- Changed mind → "Tap "Reject" in the App, or let 15 minutes pass." Never approve your own send.

App 2.0.31: Pending = 待审批/待審批/ja 未確認. Approve = 批准/ja 承認. Reject = 拒绝/拒絕/ja 拒否.
