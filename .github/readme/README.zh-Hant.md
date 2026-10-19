<p align="center"><img src="logo.svg" alt="CoinWallet" width="96"></p>

# CoinWallet 技能

[English](../../README.md) · [简体中文](README.zh-Hans.md) · 繁體中文 · [日本語](README.ja.md)

**AI agents:** the install steps are in "For AI agents" in the English [README.md](../../README.md).

讓你的 AI 智能體在 CoinWallet MPC 錢包裡收幣、轉帳。每一筆轉帳都要你在 CoinWallet App 裡批准。

把下面這句話原封不動貼到智能體的聊天框（Claude Code、Codex、Hermes 或 OpenClaw 都可以）：

```text
Install the CoinWallet skill from https://github.com/CoinsDo/agentic-wallet
```

## 怎麼用

1. 把上面那句話貼到智能體的聊天框。
2. 智能體會裝好技能和 CoinsDo 錢包服務，你不用再另外安裝。需要 macOS 或 Linux，以及 Python 3.9 或更新版本。
3. 智能體會給你 CoinWallet App 的下載連結（iPhone 和 Android），並一步一步教你在 App 裡建立錢包。
4. App 會給你一組 6 位數的邀請碼。請在 60 分鐘內貼到聊天裡。用 Claude Code 或 Codex 的話，請開一個新聊天再貼。
5. 在 App 裡點「創建」，再點「領取MPC分片」。錢包就完成了。

## 你可以這樣問

用你習慣的語言問就好。例如：

- 「我的 USDT 地址是什麼？」
- 「我的錢包裡有多少錢？」
- 「給我一個新的 TRX 地址。」
- 「轉 10 USDT 到 TX…」
- 「批准我的轉帳。」（你在 App 裡發起的轉帳）
- 「看看我的轉帳紀錄。」
- 「更新 CoinWallet。」

## 每一筆轉帳都要你在 App 裡批准

智能體不能自己把幣轉走。每筆轉帳都有兩步：

1. **在聊天裡：** 智能體會先給你看一行確認資訊：金額、幣種、鏈、錢包和完整的收款地址。請看清楚。回覆「好」或「yes」才會繼續，回覆其他內容都不會轉。
2. **在 App 裡：** 打開「Activity」→「待審批」，點開這筆轉帳。**核對完整地址是否一致。** 然後在 15 分鐘內點「批准」。改變主意了？點「拒絕」，或等 15 分鐘讓它過期。

新地址也要你在 App 裡批准（在「Activity」裡找到新增地址的請求）。

## 注意事項

- **Mac 更新之後：** 會跳出一個視窗，要你輸入「com.coinsdo.wallet.secure」的 Mac 登入密碼。輸入密碼後點 **Always Allow**（永遠允許），千萬別點 **Deny**（拒絕）。如果出現「Keychain Not Found」視窗並提供 **Reset To Defaults**，請點 **Cancel**（取消）。
- **Linux：** 千萬不要刪除或替換主密鑰檔案和錢包資料夾。換到新伺服器，就要重新建一個錢包 Room。
- **測試網：** App 預設只顯示主網。想先用測試網試試，可以問智能體。

## 手動安裝

如果智能體已經幫你裝好，就不用看這一節。選你的 Host：

<details>
<summary>Claude Code</summary>

安裝：

```sh
claude plugin install coinwallet --marketplace CoinsDo/agentic-wallet
```

然後開一個新聊天，問：「Set up the CoinWallet service.」

解除安裝（請先看下面的警告）：

```sh
claude mcp remove --scope user coinwallet
claude plugin marketplace remove coinsdo
```

</details>

<details>
<summary>Codex</summary>

安裝：

```sh
codex plugin marketplace add CoinsDo/agentic-wallet && codex plugin add coinwallet@coinsdo
```

然後開一個新聊天，問：「Set up the CoinWallet service.」

解除安裝（請先看下面的警告）：

```sh
codex mcp remove coinwallet
codex plugin remove coinwallet@coinsdo && codex plugin marketplace remove coinsdo
```

</details>

<details>
<summary>Hermes</summary>

安裝：

```sh
hermes skills install CoinsDo/agentic-wallet/skills/coinwallet --yes
```

然後問：「Set up the CoinWallet service.」

解除安裝（請先看下面的警告）：

```sh
hermes config unset mcp_servers.coinwallet
hermes skills uninstall coinwallet --yes
```

</details>

<details>
<summary>OpenClaw</summary>

安裝：

```sh
openclaw plugins install coinwallet --marketplace CoinsDo/agentic-wallet --force --accept-capabilities
```

然後問：「Set up the CoinWallet service.」

解除安裝（請先看下面的警告）：

```sh
openclaw mcp unset coinwallet
openclaw plugins uninstall coinwallet --force
```

</details>

> [!WARNING]
> **解除安裝之前：** 錢包裡還有資產時，千萬不要刪除錢包資料夾或它的主密鑰。裡面存著智能體的密鑰分片。沒有它，智能體就無法簽名，2/2 的錢包也就完全無法轉帳。解除安裝技能不會動到它們。
>
> - macOS：`~/Library/Application Support/coinsdo-wallet-mcp`（主密鑰存在 Mac 鑰匙圈裡，名稱是「com.coinsdo.wallet.secure」，千萬別刪）
> - Linux：`~/.config/coinsdo-wallet-mcp`（如果有 `master.key` 檔案，也要一起保留）
>
> 請先在 App 裡把資產轉出去。

## 維護

給維護者看。開發工具見 `AGENTS.md`。

<details>
<summary>MCP 每次發新版</summary>

1. 在本機用新的 MCP 服務跑一遍測試計畫（Test plan）。
2. 做一次降級來回：在同一份資料上換回上一個測試過的 MCP。`get_wallets` 必須顯示 `ONLINE`，而且一筆測試網轉帳要成功。
3. 通過 → 把這個版本和它的 sha256 寫進 `skills/coinwallet/mcp-tested.json`。降級來回失敗 → 同時把它列進 `no_fallback`。
4. 發一個技能版本（見下面的發布步驟）。通知使用者：「對你的智能體說 *update CoinWallet*。」
5. 最低 MCP 版本（`minimum`）只能隨技能發版一起提高（例如 `"1|2"` schema 修正發布之後）。

</details>

<details>
<summary>App 每次發新版</summary>

私有的 App 更新技能（`mackendell/coinwallet-maintainer`，之後再做）會更新各卡片裡的按鈕對照表和「App 2.0.31」那一行。它只改文字，流程變動由人來改。

</details>

<details>
<summary>新增一條鏈</summary>

1. 像 #13 那樣研究這條鏈的轉帳規則：Gas 幣、預留金或租金、tag 或 memo、真正的代幣合約、瀏覽器。
2. 參考現有的鏈檔案，寫 `skills/coinwallet/references/chains/<chain>.md`。不超過 1.5 KB，要有 `Gas coin:`、`Explorer:` 和 `Checked:` 三行。
3. 把它的代碼加進發送卡片的白名單那一行（``by `abbreviation` ``）。
4. 這條鏈有測試網 → 在 `dev/test_cases.py` 裡加一個測試網陷阱案例。
5. 在 DeepSeek Flash 上 3 次都要通過。

</details>

<details>
<summary>過時的資訊</summary>

定期重新核對每個鏈檔案的 `Checked:` 日期。

</details>

<details>
<summary>發布</summary>

使用者從 `main` 安裝，所以 `main` 只在發布時更新。

1. 在 `skills/coinwallet/VERSION`、`.claude-plugin/plugin.json` 和 `.codex-plugin/plugin.json` 裡寫同一個 `X.Y.Z`。
2. 所有必須通過的 Host × 模型都通過測試計畫。
3. `~/.hermes/hermes-agent/venv/bin/python dev/hermes_scan.py` 沒有 high 或 critical 等級的問題。
4. `python3 dev/check_repo.py --tag vX.Y.Z` 通過（它會檢查三處版本號和 tag 一致）。
5. 合併到 `main`，打 tag `vX.Y.Z` 並推送，寫 GitHub Release 說明（`gh release create vX.Y.Z`）。

</details>
