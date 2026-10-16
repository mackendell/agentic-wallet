# XRP Ledger: XRP

Gas coin: XRP. The fee is tiny.
Reserve: every XRP address keeps 1 XRP it can never send. Sending the whole balance fails: ask for an amount at least 1 XRP below it.
New address: an address that never held XRP needs at least 1 XRP. Amount under 1 XRP → say it fails if the address is new, and ask for 1 XRP or more.
Tag: no tag given and no "own wallet" said → ask, and end your turn with no Send check (never assume "no tag"): "Is this an exchange or shared address? If yes, paste the tag. If it's your own wallet, say 'no tag'."
- A tag is digits only (0 to 4294967295). Read only the digits: "tag:12345 " → 12345.
- Send it as `memo: "12345"`. Send check: "Tag: 12345".
- "no tag" or "my own wallet" → no `memo`. Send check: "Tag: no tag".
USDT/USDC: none the wallet can send here.

Explorer: Mainnet https://livenet.xrpl.org/transactions/<hash>
Explorer: Testnet https://testnet.xrpl.org/transactions/<hash>
Checked: 2026-10-15
