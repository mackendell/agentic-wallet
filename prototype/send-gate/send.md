# Send a transfer

<!--
PROTOTYPE draft for "Mainnet send gate" (#7). Throwaway branch.
Assumes a per-task card layout; the real layout is decided in "Lean skill shape" (#8).
Placeholders: chains/<chain>.md comes from #13 / #14; App button text per language from #11.
-->

Use this card for every transfer you submit: one the user asks for, or one you decide to make yourself (paying an invoice, for example). The user's **App approval** is the real gate: your shard approves the moment you submit, and the transfer goes out only after the user and the other participants approve in the App. Your job is to submit exactly what the user agreed to, and to tell them the next step whenever something blocks.

Talk in the user's language. Whenever you stop, end with the one thing the user should do next.

## Steps

1. **Wallet.** Use the wallet chosen this session (from `get_wallets`). Done when you hold one `walletId` whose `netType` you know (1 Testnet, 2 Mainnet).

2. **Asset.** Find the sending address for the asset in this wallet with `get_addresses`. Check the asset's contract (`flag`) against the real contract in `chains/<chain>.md`.
   - Same name, other contract → tell the user: "This <name> is not the real one. Remove it in the App." Use the real one, or stop if the wallet has no real one.
   - Two real-looking assets (USDC and USDC.e) → show both with full name and contract, and say which one most receivers expect. Ask which one.
   - Done when you hold one `addressId` and one asset the user would recognise.

3. **Chain rules.** Read `chains/<chain>.md` and apply every rule in it: gas coin, fee model, minimum balance, tag or memo.
   - Tag chains: ask "Sending to an exchange? Give me the tag or memo. Personal wallet? Say none."
   - Check the gas coin with one `query_address_balance` on the sending address. At 0, stop: "Your <chain> address <address> has 0 <gas coin>. Send some <gas coin> to it, then tell me."
   - Sending the gas coin itself and the amount equals the whole balance → ask for a slightly smaller amount, leaving room for the fee.
   - Done when every rule in the chain file is met or the user has the next step.

4. **Amount.** Take a plain positive decimal string: `10`, `0.5`, `10.25`. Ask again for `1e3`, `1,000`, words or "all"; for "all", ask for an exact number. Keep it a string. Done when the amount matches `(?:0|[1-9][0-9]*)(?:\.[0-9]+)?` and is above zero.

5. **Remark.** Write a short remark yourself from the conversation ("Pay invoice 123"). It goes in `comment` and stays off-chain.

6. **Send check.** Show one block and ask for yes:

   ```
   Send 10 USDT (Tron, Mainnet)
   From: Main · TXabc…full address
   To:   TXyz…full address
   Tag:  12345            ← only when there is one
   Note: Pay invoice 123
   Fee:  shown in the App when you approve
   Send? (yes / no)
   ```

   Show the contract only when two assets share a name. Done when the user's latest message is a yes to this exact block. Any change to a line → show the block again.

7. **ONLINE.** Call `get_wallet` for this `walletId`. Done when `status` is exactly `ONLINE`. Otherwise stop: "Your wallet is not ready. Open the App and check it is online, then tell me."

8. **Submit once.** Call `send_transaction` with `addressId`, `toAddress`, `amount`, `comment`, and `memo` only when there is a tag. Then say:

   > Submitted. Now open the App → Activity → Pending → Approve. You and the other approvers must approve. It needs as many approvals as you set when you made the wallet (2 of 2 by default).

   On an error or timeout, the transfer may still exist. Look for it with `get_transactions` (newest first), tell the user what you see, and leave the decision to them. Submit a second time only for a new Send check.

## Approving a transfer the user started

When the user asks you to approve a transfer they made in the App: find it with `get_transaction`, show the Send check block built from it, get a yes, run step 7, then call `approval_transaction` once with approve = true.
