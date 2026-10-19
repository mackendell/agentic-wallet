<p align="center"><img src="logo.svg" alt="CoinsDo" width="240"></p>

# CoinWallet 技能

[English](../../README.md) · 简体中文 · [繁體中文](README.zh-Hant.md) · [日本語](README.ja.md)

**AI agents:** the install steps are in "For AI agents" in the English [README.md](../../README.md).

让你的 AI 智能体在 CoinWallet MPC 钱包里收币、转账。每一笔转账都要你在 CoinWallet App 里批准。

把下面这句话原样粘贴到智能体的聊天框里（Claude Code、Codex、Hermes 或 OpenClaw 都可以）：

```text
Install the CoinWallet skill from https://github.com/CoinsDo/agentic-wallet
```

## 怎么用

1. 把上面那句话粘贴到智能体的聊天框。
2. 智能体会装好技能和 CoinsDo 钱包服务，你不用另外装别的。需要 macOS 或 Linux，以及 Python 3.9 或更新版本。
3. 智能体会给你 CoinWallet App 的下载链接（iPhone 和 Android），并一步步教你在 App 里创建钱包。
4. App 会给你一个 6 位的邀请码。请在 60 分钟内把它粘贴到聊天里。用 Claude Code 或 Codex 的话，请开一个新聊天再粘贴。
5. 在 App 里点「创建」，再点「领取MPC分片」。钱包就好了。

## 你可以这样问

用你习惯的语言问就行。比如：

- 「我的 USDT 地址是多少？」
- 「我钱包里有多少钱？」
- 「给我一个新的 TRX 地址。」
- 「转 10 USDT 到 TX…」
- 「批准我的转账。」（你在 App 里发起的转账）
- 「看看我的转账记录。」
- 「更新 CoinWallet。」

## 每一笔转账都要你在 App 里批准

智能体不能自己把币转走。每笔转账都有两步：

1. **在聊天里：** 智能体先给你看一行确认信息：金额、币种、链、钱包和完整的收款地址。请看清楚。回复「好的」或「yes」才会继续，回复别的都不会转。
2. **在 App 里：** 打开「Activity」→「待审批」，点开这笔转账。**核对完整地址是否一致。** 然后在 15 分钟内点「批准」。改主意了？点「拒绝」，或者等 15 分钟让它过期。

新地址也要你在 App 里批准（「Activity」→「添加地址」）。

## 注意事项

- **Mac 更新之后：** 会弹出一个窗口，要你输入「com.coinsdo.wallet.secure」的 Mac 登录密码。输入密码后点 **Always Allow**（始终允许），千万别点 **Deny**（拒绝）。如果出现「Keychain Not Found」窗口并提供 **Reset To Defaults**，请点 **Cancel**（取消）。
- **Linux：** 千万不要删除或替换主密钥文件和钱包数据文件夹。换到新服务器，就要重新建一个钱包 Room。
- **测试网：** App 默认只显示主网。想先用测试网试试，可以问智能体。

## 手动安装

如果智能体已经帮你装好了，就不用看这一节。选你的 Host：

<details>
<summary>Claude Code</summary>

安装：

```sh
claude plugin install coinwallet --marketplace CoinsDo/agentic-wallet
```

然后开一个新聊天，问：「Set up the CoinWallet service.」

卸载（先看下面的警告）：

```sh
claude mcp remove --scope user coinwallet
claude plugin marketplace remove coinsdo
```

</details>

<details>
<summary>Codex</summary>

安装：

```sh
codex plugin marketplace add CoinsDo/agentic-wallet && codex plugin add coinwallet@coinsdo
```

然后开一个新聊天，问：「Set up the CoinWallet service.」

卸载（先看下面的警告）：

```sh
codex mcp remove coinwallet
codex plugin remove coinwallet@coinsdo && codex plugin marketplace remove coinsdo
```

</details>

<details>
<summary>Hermes</summary>

安装：

```sh
hermes skills install CoinsDo/agentic-wallet/skills/coinwallet --yes
```

然后问：「Set up the CoinWallet service.」

卸载（先看下面的警告）：

```sh
hermes config unset mcp_servers.coinwallet
hermes skills uninstall coinwallet --yes
```

</details>

<details>
<summary>OpenClaw</summary>

安装：

```sh
openclaw plugins install coinwallet --marketplace CoinsDo/agentic-wallet --force --accept-capabilities
```

然后问：「Set up the CoinWallet service.」

卸载（先看下面的警告）：

```sh
openclaw mcp unset coinwallet
openclaw plugins uninstall coinwallet --force
```

</details>

> [!WARNING]
> **卸载之前：** 钱包里还有资产时，千万不要删除钱包数据文件夹或它的主密钥。里面存着智能体的密钥分片。没有它，智能体就无法签名，2/2 的钱包也就完全无法转账。卸载技能不会动它们。
>
> - macOS：`~/Library/Application Support/coinsdo-wallet-mcp`（主密钥存在 Mac 钥匙串里，名为「com.coinsdo.wallet.secure」，千万别删）
> - Linux：`~/.config/coinsdo-wallet-mcp`（如果有 `master.key` 文件，也一起保留）
>
> 请先在 App 里把资产转出去。

## 维护

给维护者看。开发工具见 `AGENTS.md`。

<details>
<summary>MCP 每次发新版</summary>

1. 在本地用新的 MCP 服务跑一遍测试计划（Test plan）。
2. 做一次降级往返：在同一份数据上换回上一个测试过的 MCP。`get_wallets` 必须显示 `ONLINE`，并且一笔测试网转账要成功。
3. 通过 → 把这个版本和它的 sha256 写进 `skills/coinwallet/mcp-tested.json`。降级往返失败 → 同时把它列进 `no_fallback`。
4. 发一个技能版本（见下面的发布步骤）。通知用户：「对你的智能体说 *update CoinWallet*。」
5. 最低 MCP 版本（`minimum`）只能随技能发版一起提高（比如 `"1|2"` schema 修复发布之后）。

</details>

<details>
<summary>App 每次发新版</summary>

私有的 App 刷新技能（`mackendell/coinwallet-maintainer`，之后再做）会更新各卡片里的按钮对照表和「App 2.0.31」那一行。它只改文字，流程变化由人来改。

</details>

<details>
<summary>新增一条链</summary>

1. 像 #13 那样调研这条链的转账规则：Gas 币、预留金或租金、tag 或 memo、真实的代币合约、浏览器。
2. 参照现有的链文件，写 `skills/coinwallet/references/chains/<chain>.md`。不超过 1.5 KB，要有 `Gas coin:`、`Explorer:` 和 `Checked:` 三行。
3. 把它的代码加进发送卡片的白名单那一行（``by `abbreviation` ``）。
4. 这条链有测试网 → 在 `dev/test_cases.py` 里加一个测试网陷阱用例。
5. 在 DeepSeek Flash 上 3 次都要通过。

</details>

<details>
<summary>过时的信息</summary>

定期重新核对每个链文件的 `Checked:` 日期。

</details>

<details>
<summary>发布</summary>

用户从 `main` 安装，所以 `main` 只在发布时更新。

1. 在 `skills/coinwallet/VERSION`、`.claude-plugin/plugin.json` 和 `.codex-plugin/plugin.json` 里写同一个 `X.Y.Z`。
2. 所有必须通过的 Host × 模型都通过测试计划。
3. `~/.hermes/hermes-agent/venv/bin/python dev/hermes_scan.py` 没有 high 或 critical 级别的问题。
4. `python3 dev/check_repo.py --tag vX.Y.Z` 通过（它会检查三处版本号和 tag 一致）。
5. 合并到 `main`，打 tag `vX.Y.Z` 并推送，写 GitHub Release 说明（`gh release create vX.Y.Z`）。

</details>
