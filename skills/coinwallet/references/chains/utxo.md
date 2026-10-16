# UTXO: BTC, LTC, DOGE

Gas coin: the coin itself (BTC, LTC, DOGE). The fee comes out of the same balance.
Sending the whole balance fails: ask for a slightly smaller amount.
DOGE: an amount under 1 DOGE may be refused as dust. Ask for 1 DOGE or more.
Reserve: none. Tag: none. Memo: none. Never ask a tag question.
BTC addresses: Testnet starts with m, n, 2 or tb1; Mainnet with 1, 3 or bc1. A recipient for the other network → stop and ask the user to check it.
USDT on BTC (Omni) is dead: Tether stopped it. A USDT on BTC → "This looks fake. Remove it in the App." Send nothing.

| Code | Mainnet host | Testnet host |
|---|---|---|
| BTC | mempool.space | mempool.space/testnet |
| LTC | litecoinspace.org | none |
| DOGE | none | none |

Explorer: Mainnet https://<Mainnet host>/tx/<hash>
Explorer: Testnet https://<Testnet host>/tx/<hash>
Host "none" → show the hash only.
Checked: 2026-10-15
