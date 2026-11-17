# History card: past and pending transfers

1. `get_transactions {walletId, pageIndex: 1, pageSize: 20}` once. Never pass `status`: Hermes rejects it. Filter the reply yourself.
2. Reply with a short list, newest first (the reply's order), one line each:
   "<amount> <currencyName> to <toAddress> · <status word as-is> · by <creatorName> · <txHash>" (no hash → leave it out).
   - The user asked only for pending ones → show only `PENDING_APPROVAL`.
   - No items → "No transfers yet in <wallet>."
3. A `PENDING_APPROVAL` item by "agent" → add: "Approve it in the App ("Activity" → "Pending") within 15 minutes of when it was sent, or it ends as TIMEOUT." By anyone else → add: "It waits for my approval. Ask me to approve it."

## Traps

- `get_transactions` needs `pageIndex: 1` and `pageSize`. Without them: "page index must be greater than 0" or "page size must be between 1 and 100".
- An item has no time field and no Chain: a time comes only from "When" below. Name the asset by `currencyName`; `currency` is its type (ERC20, TRC20, XRP).
- `APPROVED` with a hash means sent, not arrived. `TIMEOUT` means nobody approved within 15 minutes: nothing was sent.
- Show each hash in full, exactly as given.
- Show the status word as it is. Never retry or resend anything from this card.

## When: a transfer's time or date

Asked when a transfer happened, or for transfers on a date → this section.

1. Date asked → `get_transactions {walletId, pageIndex: 1, pageSize: 100}`; `total` over 100 → also `pageIndex: 2`, and on.
2. Each `bundleId` holds its start time. Read all of them in one run, with the user's UTC offset (unknown → 0):
   `python3 -c "import sys,datetime as d;z=d.timezone(d.timedelta(hours=float(sys.argv[1])));[print(i,d.datetime.fromtimestamp(((int(i)>>22)+1288834974657)/1000,z).strftime('%Y-%m-%d %H:%M UTC%z')) for i in sys.argv[2:]]" <offset> <bundleId> <bundleId>`
   Pass each `bundleId` as the exact digits from the reply.
3. Check the times: all in the past and after 2025; 2+ items not all the same. Pass → trust them. Fail → use no time; say "The App shows its time." (an `APPROVED` item: also "Its hash on a block explorer shows when it confirmed.")
4. Reply with "started <time and zone>" on each line, newest first. Date asked → only items started that day; none → "No transfers on <date>. <wallet> has <total> in all."

App 2.0.31: "Activity" in all languages. Pending: 待审批 / 待審批 / ja 未確認.
