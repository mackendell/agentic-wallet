# Wallet card: addresses and balances

Every fact comes from `get_addresses`. Never call `get_chains`, `get_currencies`, `get_protocols` or any `search_` tool here.

## Steps

1. The wallet comes from the router. The user said "both" or "all" → do steps 2–4 for each wallet.
2. Call `get_addresses {walletId, pageIndex: 1, pageSize: 100}` once per wallet.
3. Find the asset the user named. Match `currencyName` (USDT, ETH) or the Chain code `abbreviation` (ETH, BSC, TRX, POL).
   - Same asset on 2+ Chains and no Chain given → show each Chain.
   - Asset not in the list → say this wallet has no <asset> address yet.
4. Balance asked → `get_address_balance {addressId}` for each address you show, one call at a time.
   - "How much is in my wallet" → every address in the list. Reply: "<wallet> (<Testnet or Mainnet> wallet):", then one line per non-zero balance, and stop there. The reply names only coins with a balance. All zero → say the wallet is empty.
5. Reply.

## Fields

- `netType`: 1 = Testnet, 2 = Mainnet.
- `networkFullName`: the Chain name (Tron, Ethereum). `abbreviation`: its code.
- `currencyName`: the asset. `currencyType` 3 = a token on that Chain.
- `addressStr`: the address. Show it in full, exactly.

## Reply

- Address: "<wallet> (<Testnet or Mainnet> wallet), <asset> on <Chain>: <full address>". Always add the line "The sender must send on <Chain> only.", also when you show a balance too.
- A token on an EVM Chain (Ethereum, BSC, Polygon…) has the same address as the Chain's coin: the Universal address. Say so when the user asks for a token.
- Balance: "<asset> (<Chain>): <balance>", one line each, plus the wallet name and Mainnet or Testnet.
- Say "Testnet wallet" or "Mainnet wallet". Never say the service is on testnet.

## Traps

- `get_addresses` with `pageSize` but no `pageIndex` fails ("page index must be greater than 0"). Always send `pageIndex: 1`.
- `get_addresses` returns no items or the text `"null"` → no addresses yet (wallet not `ONLINE`). Never call it again with the same arguments.
- Use `get_address_balance {addressId}`. It needs no currency lookup.
