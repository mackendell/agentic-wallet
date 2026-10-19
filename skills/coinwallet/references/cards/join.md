# Join card

The user makes an MPC wallet Room in the CoinWallet App. You join it with the Invitation code.

## No code yet

1. Give the App links. Only these:
   - iPhone: https://a8ata.app.link/coinwallet_ios
   - Android: https://a8ata.app.link/coinwallet_android
2. Copy all 5 App steps exactly, every quoted button kept, in the user's language only (table below):
   1. Tap your avatar (top left) to open the side panel. Tap "Add Wallet" at the bottom.
   2. "Select a method" → "MPC Wallet".
   3. "Customize MPC Wallet": keep the defaults → "Next".
   4. "Create MPC Wallet": type a wallet name → "Confirm".
   5. "Invite Members": copy the 6-character code and paste it here. It expires in 60 minutes.
3. Stop. Wait for the code.

## The user pastes a code

1. Count its characters. Not exactly 6 (0-9, A–F) → say only "The code needs 6 characters." Never write the user's code back. Ask again. Never call join with it.
2. 6 → call `join_mpc_wallet {invitationCode: "<code>", custodianName: "agent"}` once, right away, even with other wallets. Never write the code back or save it.
3. Tell the user: in the App, tap "Create", then "Claim MPC key shard". Tell me when done.

## The user says done

1. Call `get_wallets` once.
2. Read the new wallet's `status`:
   - `ONLINE` → "Your wallet <walletName> is ready." Done.
   - `""` or `PENDING_CREATION` → tell the user to tap "Create" in the App.
   - `CREATED` → tell the user to claim the key shard in the App.
3. Not `ONLINE` → check again only when the user writes again. Never loop.

## Traps

- There is no `claim_key_shard` tool. The service claims the agent's shard itself.
- `get_addresses` before `ONLINE` returns no items (or the text `"null"`): no addresses yet. Never call it again with the same arguments.
- Testnet: only if the user asks. "Settings" → "About App" → tap the logo 8 times → back in "Settings", turn on the Testnet switch. Then pick "Testnet" in "Customize MPC Wallet".

## App 2.0.31 buttons

Use the user's language column. Chinese: Simplified or Traditional from their characters; unclear → Simplified. Other languages → English. `—` → give the place only.

| en | zh-Hans | zh-Hant | ja |
|---|---|---|---|
| Add Wallet | 添加钱包 | — | — |
| Select a method (or: Select to add) | 选择创建方式 | 選擇創建方式 | 追加方法を選択 |
| MPC Wallet | MPC钱包 | MPC錢包 | MPCウォレット |
| Customize MPC Wallet | MPC设定 | MPC設定 | MPC設定 |
| Next | 继续 | 繼續 | 続行 |
| Create MPC Wallet | 创建MPC钱包 | 創建MPC錢包 | MPCウォレットを作成 |
| Confirm | 确认 | 確認 | 確認 |
| Invite Members | 邀请成员 | 邀請成員 | メンバーを招待 |
| Create | 创建 | 創建 | 作成 |
| Claim MPC key shard | 领取MPC分片 | 領取MPC分片 | MPCキーシャードを取得する |
| About App | 关于App | 關於App | アプリ概要 |
| Testnet switch: Testnet | 测试链 | 測試鏈 | テストネット |
| Testnet | 测试网络 | 測試網絡 | Testnet |
