# Send a transfer

<!--
PROTOTYPE draft for "Mainnet send gate" (#7). Throwaway branch.
Assumes a per-task card layout; the real layout is decided in "Lean skill shape" (#8).
"Talking to the user" applies to every card, so it likely moves to the always-loaded SKILL.md.
Message style follows https://github.com/ayghri/i-have-adhd.
Placeholders: chains/<chain>.md comes from #13 / #14; App button text per language from #11.
App paths like "Assets → USDT → Remove" are guesses until the screenshots in #10 confirm them.
-->

Use this card for every transfer you submit: one the user asks for, or one you decide to make yourself (paying an invoice, for example). The user's **App approval** is the real gate: your shard approves the moment you submit, and the transfer goes out only after the user and the other participants approve in the App. Your job is to submit exactly what the user agreed to.

## Talking to the user

Every message you send follows these rules:

1. **Action first.** The first line is what the user does now. The reason comes after, in one line.
2. **Numbered steps.** More than one thing to do → a numbered list, one tap or one reply per step.
3. **One next step at the end.** Every stop ends with one thing the user can do in under two minutes, usually a reply word: "Then reply **done**."
4. **Plain facts on errors.** Say what happened and the fix, in calm words.
5. **Show the win.** After a success, say what now exists ("10 USDT is waiting for your approval").
6. **Short.** Skip greetings, recaps and sign-offs. At most 5 items in any list.
7. **The user's language,** with App buttons named exactly as the App shows them.

## Steps

1. **Wallet.** Use the wallet chosen this session (from `get_wallets`). Done when you hold one `walletId` whose `netType` you know (1 Testnet, 2 Mainnet).

2. **Asset.** Find the sending address for the asset in this wallet with `get_addresses`. Check the asset's contract (`flag`) against the real contract in `chains/<chain>.md`. Done when you hold one `addressId` and one asset the user would recognise.
   - Same name, other contract → use the real one and say:
     > Remove the fake USDT in the App: Assets → USDT (contract 0xdead…) → Remove.
     > It's not the real USDT. Real USDT on Polygon is 0xc213…
   - The wallet has only the fake one → stop and say the same, plus: "Then add the real USDT and reply **done**."
   - Two real-looking assets → ask:
     > Which one should I send? Reply **1** or **2**.
     > 1. USDC (0x3c49…), the current one most exchanges take
     > 2. USDC.e (0x2791…), the older bridged one
     > Not sure? Ask the receiver which one they want.

3. **Chain rules.** Read `chains/<chain>.md` and apply every rule in it: gas coin, fee model, minimum balance, tag or memo. Done when every rule is met or the user has their next step.
   - Tag chains → ask:
     > Reply with the destination tag, or **none**.
     > Exchanges need a tag to know it's yours. Personal wallets don't.
   - Check the gas coin with one `query_address_balance` on the sending address. At 0, stop:
     > Send some TRX to your Tron address `TXabc…full`. Then reply **done**.
     > Sending USDT on Tron needs TRX for the fee, and this address has 0.
   - Sending the gas coin itself and the amount equals the whole balance:
     > Pick a slightly smaller amount, like 9.9 TRX. Reply with the number.
     > The fee comes out of the same balance.

4. **Amount.** Take a plain positive decimal string: `10`, `0.5`, `10.25`. Done when the amount matches `(?:0|[1-9][0-9]*)(?:\.[0-9]+)?` and is above zero. Keep it a string. For `1e3`, `1,000`, words or "all":
   > Reply with the exact amount as a plain number, like `250` or `0.5`.

5. **Remark.** Write a short remark yourself from the conversation ("Pay invoice 123"). It goes in `comment` and stays off-chain.

6. **Send check.** Show this block:

   ```
   Reply yes to send:
   10 USDT · Tron · Mainnet
   From: Main · TXabc…full address
   To:   TXyz…full address
   Tag:  12345            ← only when there is one
   Note: Pay invoice 123
   Fee:  shown in the App when you approve
   ```

   Show the contract only when two assets share a name. Done when the user's latest message is a yes to this exact block. Any change to a line → show the block again.

   **Buttons, when the Host has them.** With a `clarify` tool (Hermes) or `ask_user` tool (OpenClaw), ask the Send check through it: one single-choice question, the block as the question text, choices exactly `Yes` and `No` in the user's language, no other option. Only an answered `Yes` counts as yes. Any other result → show the block as text and ask for a typed yes.

7. **ONLINE.** Call `get_wallet` for this `walletId`. Done when `status` is exactly `ONLINE`. Otherwise stop:
   > Open the CoinWallet App and check wallet "Main" is online. Then reply **done**.
   > I can only send from an online wallet.

8. **Submit once.** Call `send_transaction` with `addressId`, `toAddress`, `amount`, `comment`, and `memo` only when there is a tag. Then say:

   > 10 USDT to TXyz… is waiting for your approval.
   > 1. Open the CoinWallet App
   > 2. Tap Activity → Pending
   > 3. Tap Approve
   >
   > The other approvers approve too, up to the number you set when you made the wallet (2 of 2 by default).

   On an error or timeout, the transfer may still exist. Look for it with `get_transactions` (newest first), then say what you found:
   > Check the App → Activity → Pending for 10 USDT to TXyz….
   > The send call failed, but it may have gone through. I see <what you found>.
   > Reply **send again** only if it's not there.

   A second submit needs a new Send check.

## Approving a transfer the user started

When the user asks you to approve a transfer they made in the App: find it with `get_transaction`, show the Send check block built from it (first line "Reply yes to approve:"), get a yes, run step 7, then call `approval_transaction` once with approve = true. Then say:
> Approved: 10 USDT to TXyz….
> It goes out once it has as many approvals as you set when you made the wallet (2 of 2 by default).
