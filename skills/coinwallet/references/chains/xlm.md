# Stellar: XLM

Gas coin: XLM. The fee is tiny.
Reserve: every Stellar address keeps 1 XLM it can never send. Sending the whole balance fails: ask for an amount at least 1 XLM below it.
New address: an address that does not exist yet needs at least 1 XLM. Less fails.
Memo: this wallet service can't send a Stellar memo.
- The user gives a memo, or says it's an exchange or shared address → stop: "I can't send a Stellar memo. Send it from the CoinWallet App." Send nothing.
- No memo given → before the Send check, ask: "Is this an exchange or shared address? Those need a memo, which I can't send." Own wallet → go on; the Send check says "Memo: none".
USDT/USDC: none the wallet can send here.

Explorer: Mainnet https://stellar.expert/explorer/public/tx/<hash>
Explorer: Testnet https://stellar.expert/explorer/testnet/tx/<hash>
Checked: 2026-10-15
