# Agent-joined and approval screens (Android 2.0.31+1455, Pixel 6, 2026-10-13)

Throwaway Testnet 2-of-2 wallets `agent-test` and `agent-test-2`, creator "owner" on the phone, agent "agent" through MCP v1.0.5 started with `-e prod` (the Play Store App's Rooms are not visible to a `-e test` service: `join_mpc_wallet` → `ErrCodeTee6052|不存在未创建的钱包`). Raw MCP replies in `mcp-raw/`.

## What happens, in order

| Step | App (creator) | MCP (agent) `get_wallets` status |
|---|---|---|
| Creator confirms Create MPC Wallet | Invite Members, code + 60-min timer, "?" Member, Create disabled | — |
| Agent `join_mpc_wallet` | 12: agent row appears (red ✕ to remove), Create enabled | `""` for a few seconds, then `PENDING_CREATION` |
| Creator taps Create | 13: Claim Key Shard, both ticks grey, button "Claim MPC key shard" | `CREATED` |
| Creator claims (PIN/biometric, secure screen) | 15: creator tick green, agent grey, button "Waiting for others" (disabled) | `CREATED` |
| Agent `claim_key_shard` | 14: both ticks green, button "Complete" | `ONLINE`, `get_addresses` returns 13 default addresses |

- **The agent's shard needs a claim** (`claim_key_shard`); without it the wallet stays `CREATED` and the creator is stuck on "Waiting for others". The claim can happen before or after the creator's (first wallet: agent claimed first, App ticks only refreshed after the creator's claim).
- `get_addresses` returns `"null"` (string) until the wallet is `ONLINE`.
- Secure screens (PIN, biometric, backup, approval identity check) screenshot as black (FLAG_SECURE).

## Pending transfer

- Agent `send_transaction` (1 XRP, memo 12345, comment) → `PENDING_APPROVAL`; reply has `netType: 0` and `txType: ""` (the same tx in `get_transactions` has `netType: 1`, `txType: TEE_CRYPTO_TRANSACTION`).
- **Push arrives** within seconds: title = wallet name, text "You have a new XRP transaction pending approval" (17b).
- Activity badge "1"; row under **Require Action** with a red **15-minute countdown** and "Pending" (18). The approval window is 15 minutes.
- Detail (19): Request / Parameter / Approval tabs, "New Transfer" top right, "1 approval(s) required", Reject / Approve. Parameter tab shows the raw JSON (fee, memo, sequence). Approval tab shows "agent (Initiator) · Transaction approved ✓" and the agent's Remark as a bubble: the agent's shard approves on submit.
- Approve → sheet titled "Transaction approved" with optional "Approval Remarks", Cancel / Confirm (20a) → identity check (secure, black) → status Confirming, then Successful; MCP `APPROVED` with txHash (21, 21b).
- Testnet wallets show a yellow banner "This is a Testnet wallet." on Crypto and Activity.

## Strings (en / zh-Hans / zh-Hant / ja)

| en | zh-Hans | zh-Hant | ja |
|---|---|---|---|
| Invite Members | 邀请成员 | 邀請成員 | メンバーを招待 |
| Members (2) / Wallet Details | 成员 (2) / 钱包详情 | 成員 (2) / 錢包詳情 | メンバー (2) / ウォレット詳細 |
| owner (Creator, You) | owner (创建者, 您) | owner (創建者, 您) | owner (作成者, あなた) |
| Cancel Creation / Create | 取消创建 / 创建 | 取消創建 / 創建 | 作成をキャンセル / 作成 |
| MPC Wallet Name / MPC Wallet TEE ID / Approval / Restore threshold / 2 shard(s) | MPC钱包名称 / MPC钱包TEE ID / 审批/还原阈值 / 2 分片 | MPC錢包名稱 / MPC錢包TEE ID / 審批/還原閾值 / 2 分片 | MPCウォレット名 / MPCウォレットのTEE ID / 承認および復元の閾値 / 2 キーシャード |
| Claim Key Shard | 领取MPC分片 | 領取MPC分片 | キーシャードを受け取る |
| Claim MPC key shard | 领取MPC分片 | 領取MPC分片 | MPCキーシャードを取得する |
| Waiting for others | 等待其他人 | (not captured) | (not captured) |
| This is a Testnet wallet. | 这是个测试网络钱包。 | 這是個測試網絡錢包。 | このウォレットはテストネット環境にあります |
| Require Action / History | 需要操作 / 历史记录 | 需要操作 / 歷史記錄 | 必要な操作 / 履歴 |
| Pending / Successful | 待审批 / 成功 | 待審批 / 成功 | 未確認 / 成功 |
| Details / New Transfer | 详情 / 新转账 | 詳情 / 新轉賬 | 詳細 / 新しい送金 |
| Request / Parameter / Approval | 请求 / 参数 / 审批 | 請求 / 參數 / 審批 | リクエスト / パラメータ / 承認 |
| Send | 发送 | 發送 | 送金 (list: 送信) |
| 1 approval(s) required | 需要1个批准 | 需要1個批准 | 1の承認が必要 |
| Reject / Approve | 拒绝 / 批准 | 拒絕 / 批准 | 拒否 / 承認 |
| Transaction approved (sheet title and bubble) | 批准交易 | 批准交易 | トランザクションは承認されました |
| Approval Remarks / Cancel / Confirm | 审批备注 / 取消 / 确认 | 審批備註 / 取消 / 確認 | 承認備考 / キャンセル / 確認 |
| Save Address / Share | 保存地址 / 分享 | 保存地址 / 分享 | アドレスを保存 / シェア |

- English in every language: tabs `Crypto / NFT / Activity`, `Destination tag`.
- ja shows a pending transfer as 未確認 ("unconfirmed"), not "pending approval".
- ru spot-check: English fallback (same text as en) except the sheet buttons Отмена / подтверждать.

## Not captured

- 05 Testnet-enabled toast (needs a phone with Testnet still hidden).
- 14 and 15 in zh-Hant/ja (wallet went ONLINE before the language switch landed).
- 20 identity check, 13/14 backup: secure screens, black in screenshots.
