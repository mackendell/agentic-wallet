# History card: past and pending transfers

1. `get_transactions {walletId, pageIndex: 1, pageSize: 20}` once. Never pass `status`: Hermes rejects it. Filter the reply yourself.
2. Reply with a short list, newest first (the reply's order), one line each:
   "<amount> <currencyName> to <toAddress> · <status word as-is> · by <creatorName> · <txHash>" (no hash → leave it out).
   - The user asked only for pending ones → show only `PENDING_APPROVAL`.
   - No items → "No transfers yet in <wallet>."
3. A `PENDING_APPROVAL` item by "agent" → add: "Approve it in the App ("Activity" → "Pending") within 15 minutes of when it was sent, or it ends as TIMEOUT." By anyone else → add: "It waits for my approval. Ask me to approve it."

## Traps

- `get_transactions` needs `pageIndex: 1` and `pageSize`. Without them: "page index must be greater than 0" or "page size must be between 1 and 100".
- An item has no time and no Chain. Name the asset by `currencyName`; `currency` is its type (ERC20, TRC20, XRP).
- `APPROVED` with a hash means sent, not arrived. `TIMEOUT` means nobody approved within 15 minutes: nothing was sent.
- Show each hash in full, exactly as given.
- Show the status word as it is. Never retry or resend anything from this card.

App 2.0.31: "Activity" in all languages. Pending: 待审批 / 待審批 / ja 未確認.
