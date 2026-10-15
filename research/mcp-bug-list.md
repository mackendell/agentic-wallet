# coinsdo-wallet-mcp 问题清单（给 MCP 开发）

你好！我们在做 CoinWallet 的 AI agent skill（Claude Code / Codex / Hermes / OpenClaw，最低要跑通 DeepSeek Flash），用真实的 MCP 服务和 App 2.0.31 测了一轮。下面是发现的问题，按优先级排好。版本都是指 MCP 版本；没特别说明的，在最新的 **v1.0.8** 上仍然存在。

优先级：**P0** = 挡住功能或有安全风险，请先修；**P1** = 会误导用户或 agent；**P2** = 数据/文档不对，skill 能绕开；**P3** = 有空再说。

---

## P0

### 1. 枚举参数的 JSON Schema 写错了：`"enum": ["1|2"]`（最优先）

- **版本**：v1.0.7、v1.0.8（v1.0.5 没有这个问题）。
- **复现**：`tools/list`，看这些参数：
  - `netType`：`{"type":"integer","enum":["1|2"]}`，出现在 `get_chains`、`get_currencies`、`get_protocols`、`get_nft_projects`、`search_chains`、`search_currencies`、`search_protocols`、`search_nft_projects`（8 个工具）
  - `nftState`：`enum ["0|1|2"]`（`get_chains`、`get_protocols`）
  - `search_addresses.currencyType`：`enum ["0|1|3"]`
  - `get_transactions.status`：`enum ["PENDING_APPROVAL|TIMEOUT|APPROVED|REJECTED|ERROR|REVOKED"]`
- **问题**：enum 只有一个值，就是字符串 `"1|2"`，而且类型还写成 integer。按 schema 来，`1`、`2` 都不在 enum 里，`"1|2"` 又不是整数，所以**没有任何合法值**。看起来是生成 schema 时把 tag 里的 `1|2` 当成了一个整体。
- **影响**：Hermes 在调用前会按 schema 检查参数，直接拒绝，所以上面这些工具在 Hermes 上**全部不能用**（服务本身其实接受 `netType: 1`）。结果是 Hermes 上没法加新币种/新代币（要先查 `currencyId`）。另外，工具报错后 DeepSeek Flash 会自己去用终端、`curl` 直接打服务、翻服务日志，有一次一直不停。
- **建议**：改成 `{"type":"integer","enum":[1,2]}`（`nftState` → `[0,1,2]`，`currencyType` → `[0,1,3]`），`status` 改成 `{"type":"string","enum":["PENDING_APPROVAL","TIMEOUT",...]}`。修好的版本发布后，skill 的最低 MCP 版本会升到那一版。

### 2. 日志里记录了完整的 shard（私钥分片）

- **版本**：v1.0.8（Linux 上确认）。
- **复现**：agent 加入 Room 后，看 `~/.config/coinsdo-wallet-mcp/logs/` 下的日志：`tee/shard/collection` 的完整返回被写进去了，包括 `shard` 字段的值。
- **影响**：密钥材料落在明文日志里。日志常被用户拷贝、上传给客服或发给 AI 排查问题。
- **建议**：日志里不要记录 `shard` 等密钥字段（打码或只记长度）。旧版本留下的日志可能也需要清理提示。

---

## P1

### 3. 报错让用户 `reinstall with [-r]`，但没有 `-r`，真正的 `-clean-data` 会毁掉 agent 的分片

- **版本**：v1.0.8（macOS + Linux）。
- **复现**（结尾都是 `please reinstall with [-r]`）：
  - macOS 钥匙串弹窗点了「拒绝」：`keychain query failed: Keychain Error. (-128)`
  - 弹窗没人点（约 38 秒）：`keychain add failed: Keychain Error. (-60006)`
  - 没有图形界面（launchd/SSH）：`keychain add failed: Keychain Error. (-60008)`
  - Linux 主密钥变了：`decrypt secure storage: cipher: message authentication failed`
- **问题**：没有 `-r` 这个参数。真正的参数是 `-clean-data`，它会删掉数据、日志和密钥，agent 的分片就永久丢了，只能新建 Room。前三种情况其实只要重启、在弹窗里点「始终允许」就好，完全不需要重装。
- **建议**：报错写清真实原因和正确做法，例如「你在钥匙串弹窗点了拒绝，请重启服务并点始终允许」「没有图形界面，无法弹出钥匙串窗口」「主密钥和创建时不一致（COINSDO_MASTER_KEY / machine-id 变了）」。不要提 reinstall。`-clean-data` 现在要键盘输入 `Y`，脚本里只能 `echo Y |`，可以加一个 `-y`，但请在帮助里写明「会永久删除 agent 分片」。

### 4. macOS 二进制是 ad-hoc 签名：每次升级都弹钥匙串窗口，浏览器下载会被 Gatekeeper 拦

- **版本**：所有 darwin 版本（v1.0.8 darwin-arm64，macOS 26.5.1 上测的）。
- **复现**：`codesign -dv` 显示 `Identifier=a.out`、没有 Team ID、没有公证。用 v1.0.7 建好钥匙串项，再换 v1.0.8 启动 → 弹窗「service-darwin-arm64 wants to use your confidential information stored in "com.coinsdo.wallet.secure"」要输登录密码。浏览器下载的文件 `spctl --assess` → `rejected`。
- **影响**：每次升级用户都要输 Mac 密码点「始终允许」；点错「拒绝」就会看到问题 3 的误导报错。
- **建议**：用 Developer ID 签名 + 固定的 identifier + 公证（notarize）。这样钥匙串会信任同一个开发者签的新版本，不再每次弹窗。

### 5. `add_address` 审批超时后，agent 完全不知道

- **版本**：v1.0.8。
- **复现**：`add_address` 返回 `{"pending":1}`，App 里不去审批，15 分钟后过期。之后 `get_addresses` 一直是空的，没有任何工具能看到这条申请的状态（转账超时在 `get_transactions` 里能看到 `TIMEOUT`，加地址没有）。
- **影响**：agent 无法区分「还在等审批」和「已经超时」，只能让用户回去看 App。
- **建议**：`add_address` 返回一个申请 id，并提供查询状态的方式（或者在某个列表里能看到 PENDING / TIMEOUT / APPROVED / REJECTED）。

---

## P2

### 6. 链上 memo 只支持 6 条链，Stellar / TON / Symbol 交易所充值做不了

- **版本**：v1.0.5（test 环境）查的。
- **问题**：`send_transaction` 的 memo 只在 XRP、EOS、Tron（TRX/TRC20）、Solana（SOL/SPL）、Algorand、Cosmos 上生效。Stellar、TON、Symbol 的交易所充值必须带 memo，现在发不了（Vaulta 没确认）。
- **影响**：skill 遇到这些链要给交易所转账时只能停下，说做不到。
- **建议**：给这些链也支持 memo；如果短期不做，请在工具说明里写清哪些链支持 memo。

### 7. 已停用或已迁移的链/币还在列表里，缺真 Arbitrum USDT

- **版本**：v1.0.5（test 环境）查的，Mainnet 列表。
- **问题**：
  - OKT Chain（2026-01-01 停止）、HECO/HT（2025-01-15 停止）、Fantom Opera（迁到 Sonic，跨链桥 2026-06-30 关闭）还在列表里。
  - Polkadot 余额 2025-11-04 已迁到 Asset Hub，旧的 `DOT_OLD` 还在。
  - EOS 已改名 Vaulta（A），两个都在。
  - Tron 上的 USDC：Circle 已停止发行，但还在列表。
  - Arbitrum 上真正的 USDT（USDT0）不在列表里。
- **建议**：把停用的链下掉或标记，补上 USDT0。（各链真实 USDT/USDC 合约我们整理过，需要的话可以发给你。）

### 8. `send_transaction` 返回的 `netType`、`txType` 不对

- **版本**：v1.0.8。
- **复现**：Testnet 钱包 `send_transaction`，返回里 `netType: 0`、`txType: ""`；同一笔在 `get_transactions` 里是 `netType: 1`、`txType: "TEE_CRYPTO_TRANSACTION"`。
- **建议**：返回和 `get_transactions` 一致的值。

### 9. `query_address_balance` 在地址加好之后，`addressId` 还是 0

- **版本**：v1.0.8。
- **复现**：地址上有一个钱包里没有的代币 → `add_currency` → `add_address` → App 审批通过 → `get_addresses {walletId, currencyId}` 能拿到 `addressId: 28`，但 `query_address_balance` 仍然返回 `addressId: 0`。
- **影响**：`send_transaction` 需要真实的 `addressId`，agent 拿 0 去发会失败。
- **建议**：返回真实的 `addressId`。

### 10. `search_protocols {"currency":"ERC20"}` 返回空

- **版本**：v1.0.8，Sepolia（`netType: 1`）。
- **复现**：`search_protocols {"netType":1,"currency":"ERC20"}` → `{"items":[]}`；但 `get_protocols {"netType":1}` 里有 ERC20（`protocolId 10`）。
- **建议**：搜索也能按协议名（ERC20 / TRC20 / SPL…）找到。

### 11. `search_currencies` 只传 `flag`（合约地址）会报错，和 schema 不一致

- **版本**：v1.0.8。
- **复现**：`search_currencies {"netType":1,"flag":"0x…"}` → `either currency or currency name is required`。schema 里 `flag` 看起来是可选的查询方式之一。
- **建议**：支持只按合约地址查（这是最常见的用法），或者在 schema 里写明 `flag` 不能单独用。

### 12. `add_address` 的工具说明不对

- **版本**：v1.0.8。
- **问题**：说明写「a new unique address is generated each time this tool is called」，但对代币来说，它复用该链的第一个地址（index 0，`m/44'/60'/0'/0/0`），不会生成新地址（Sepolia 实测两次）。
- **影响**：模型会以为每调一次就多一个地址，或者不敢用它来「让已有代币可发送」。
- **建议**：说明里分开写主币和代币的行为。

### 13. 刚加入 Room 时钱包 `status` 是空字符串

- **版本**：v1.0.5（v1.0.8 未复查）。
- **复现**：`join_mpc_wallet` 后马上 `get_wallets`，几秒内 `status: ""`，之后才变 `PENDING_CREATION`。
- **建议**：一开始就返回 `PENDING_CREATION`。

### 14. 列表为空时返回字符串 `"null"`

- **版本**：v1.0.5：`get_wallets`（没钱包时）和 `get_addresses`（钱包还没 ONLINE 时）返回字符串 `"null"`。v1.0.8 的 `get_wallets` 已经是 `{"items":[]}`，`get_addresses` 在未 ONLINE 钱包上还没复查。
- **建议**：确认所有列表工具为空时都返回 `{"items":[]}`。

### 15. `claim_key_shard` 在 v1.0.5 → v1.0.8 之间被去掉了，没写在更新说明里

- v1.0.5 必须调用 `claim_key_shard`，否则创建者一直卡在「等待其他人」；v1.0.8 没有这个工具，改成后台自动领取。行为改变很好，但请在 release notes 里写一句，方便我们和用户知道版本差异。

---

## P3

### 16. 旧版本能直接跑在新版本的数据上，没有任何提示

- **版本**：v1.0.5 ↔ v1.0.8（Linux 实测，Testnet 转账正常）。
- **问题**：旧版本启动时会把 `t_version` 静默改成自己的号（1460 → 1458），然后照常运行。目前这个范围内的表结构是兼容的，所以没出事，但以后如果有不向后兼容的迁移，就会出问题。
- **建议**：迁移不能向后兼容时，旧版本启动直接报「数据版本太新，请使用 vX.Y.Z 或更新版本」，不要改 `t_version`。

---

## 一个小请求（不是 bug）

### 17. `get_wallet` 返回审批门槛（Approval threshold）

- 现在 agent 不知道钱包是几签几（比如 2-of-3），所以没法告诉用户「还需要几个人在 App 里批准」。请在 `get_wallet` 里加上审批门槛和成员数。

---

测试记录、原始返回、截图都有，需要哪一条的详细复现可以随时找我。谢谢！
