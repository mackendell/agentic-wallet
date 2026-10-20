<p align="center"><img src="logo.svg" alt="CoinsDo" width="240"></p>

# CoinWallet スキル

[English](../../README.md) · [简体中文](README.zh-Hans.md) · [繁體中文](README.zh-Hant.md) · 日本語

**Installing with an AI agent:** the agent runs the "Install steps" in the English [README.md](../../README.md).

AI エージェントが CoinWallet の MPC ウォレットで暗号資産を受け取り、送金できるようになります。送金はすべて、あなたが CoinWallet アプリで承認します。

次の一文をそのまま、エージェントのチャットに貼り付けてください（Claude Code、Codex、Hermes、OpenClaw のどれでも使えます）。

```text
Install the CoinWallet skill from https://github.com/CoinsDo/agentic-wallet
```

## 使い方

1. 上の一文をエージェントのチャットに貼り付けます。
2. エージェントがスキルと CoinsDo ウォレットサービスをインストールします。ほかに入れるものはありません。macOS か Linux と、Python 3.9 以降が必要です。
3. エージェントが CoinWallet アプリのリンク（iPhone と Android）と、アプリでウォレットを作る手順を教えてくれます。
4. アプリに 6 文字の招待コードが表示されます。60 分以内にチャットに貼り付けてください。Claude Code か Codex では、新しいチャットを開いてから貼り付けます。
5. アプリで「作成」をタップし、続けて「MPCキーシャードを取得する」をタップします。これでウォレットの完成です。

## こんなことを頼めます

ふだんの言葉で頼んでください。たとえば：

- 「USDT のアドレスを教えて」
- 「ウォレットにいくら入ってる？」
- 「新しい TRX アドレスを作って」
- 「10 USDT を TX… に送って」
- 「私の送金を承認して」（あなたがアプリで始めた送金）
- 「送金履歴を見せて」
- 「CoinWallet をアップデートして」

## 送金はすべてアプリで承認します

エージェントが勝手に送金することはできません。送金には 2 つのステップがあります。

1. **チャットで：** エージェントが金額、通貨、チェーン、ウォレット、送金先の完全なアドレスを 1 行で見せます。よく確認してください。「はい」か「yes」と返すと先に進みます。それ以外の返事では何も送られません。
2. **アプリで：** 「Activity」→「未確認」を開き、その送金を開きます。**完全なアドレスが一致しているか確認してください。** そのあと 15 分以内に「承認」をタップします。やめたいときは「拒否」をタップするか、15 分待てば期限切れになります。

新しいアドレスにも、アプリでの承認が必要です（「Activity」にある新しいアドレスの申請）。

アプリでは承認待ちの送金が「未確認」と表示されます。これは「承認待ち」という意味です。

## 知っておくこと

- **Mac でアップデートしたあと：** 「com.coinsdo.wallet.secure」のために Mac のログインパスワードを求めるポップアップが出ます。パスワードを入力して **Always Allow**（常に許可）をクリックしてください。**Deny**（拒否）は絶対にクリックしないでください。「Keychain Not Found」ダイアログに **Reset To Defaults** が出たら、**Cancel**（キャンセル）をクリックしてください。
- **Linux：** マスターキーのファイルとウォレットのデータフォルダは、絶対に削除したり置き換えたりしないでください。新しいサーバーに移るときは、ウォレットの Room を作り直します。
- **テストネット：** アプリには最初メインネットだけが表示されます。先にテストネットで試したいときは、エージェントに聞いてください。

## 手動でインストール

エージェントがインストールしてくれた場合は不要です。使っている Host を開いてください。

<details>
<summary>Claude Code</summary>

インストール：

```sh
claude plugin install coinwallet --marketplace CoinsDo/agentic-wallet
```

そのあと新しいチャットを開いて、「Set up the CoinWallet service.」と頼みます。

アンインストール（先に下の警告を読んでください）：

```sh
claude mcp remove --scope user coinwallet
claude plugin marketplace remove coinsdo
```

</details>

<details>
<summary>Codex</summary>

インストール：

```sh
codex plugin marketplace add CoinsDo/agentic-wallet && codex plugin add coinwallet@coinsdo
```

そのあと新しいチャットを開いて、「Set up the CoinWallet service.」と頼みます。

アンインストール（先に下の警告を読んでください）：

```sh
codex mcp remove coinwallet
codex plugin remove coinwallet@coinsdo && codex plugin marketplace remove coinsdo
```

</details>

<details>
<summary>Hermes</summary>

インストール：

```sh
hermes skills install CoinsDo/agentic-wallet/skills/coinwallet --yes
```

そのあと「Set up the CoinWallet service.」と頼みます。

アンインストール（先に下の警告を読んでください）：

```sh
hermes config unset mcp_servers.coinwallet
hermes skills uninstall coinwallet --yes
```

</details>

<details>
<summary>OpenClaw</summary>

インストール：

```sh
openclaw plugins install coinwallet --marketplace CoinsDo/agentic-wallet --force --accept-capabilities
```

そのあと「Set up the CoinWallet service.」と頼みます。

アンインストール（先に下の警告を読んでください）：

```sh
openclaw mcp unset coinwallet
openclaw plugins uninstall coinwallet --force
```

</details>

> [!WARNING]
> **アンインストールの前に：** ウォレットに資産があるうちは、ウォレットのデータフォルダとそのマスターキーを絶対に削除しないでください。そこにエージェントのキーシャードが入っています。これがないとエージェントは署名できず、2/2 のウォレットはまったく送金できなくなります。スキルをアンインストールしても、これらは残ります。
>
> - macOS：`~/Library/Application Support/coinsdo-wallet-mcp`（マスターキーは Mac のキーチェーンに「com.coinsdo.wallet.secure」として入っています。削除しないでください）
> - Linux：`~/.config/coinsdo-wallet-mcp`（`master.key` ファイルがあれば、それも残してください）
>
> 先にアプリで資産を移しておいてください。

## メンテナンス

メンテナー向けです。開発ツールは `AGENTS.md` にあります。

<details>
<summary>MCP の新しいリリースごとに</summary>

1. 新しい MCP サービスで、テストプラン（Test plan）をローカルで実行します。
2. ダウングレードの往復をします。同じデータの上で、前にテストした MCP に戻します。`get_wallets` が `ONLINE` を返し、テストネットの送金が 1 件成功すること。
3. 合格 → そのバージョンと sha256 を `skills/coinwallet/mcp-tested.json` に追加します。往復に失敗したら `no_fallback` にも入れます。
4. スキルをリリースします（下の手順）。ユーザーには「エージェントに *update CoinWallet* と送ってください」と伝えます。
5. MCP の最低バージョン（`minimum`）は、スキルのリリースと一緒にだけ上げます（たとえば `"1|2"` スキーマの修正が出たあと）。

</details>

<details>
<summary>アプリの新しいリリースごとに</summary>

非公開のアプリ更新スキル（`mackendell/coinwallet-maintainer`、後で作成）が、各カードのボタン対応表と「App 2.0.31」の行を更新します。直すのは文言だけで、流れの変更は人が直します。

</details>

<details>
<summary>チェーンを追加する</summary>

1. #13 と同じように、そのチェーンの送金ルールを調べます：ガス代の通貨、リザーブやレント、タグやメモ、本物のトークンコントラクト、エクスプローラー。
2. 既存のチェーンファイルをもとに `skills/coinwallet/references/chains/<chain>.md` を書きます。1.5 KB 以内で、`Gas coin:`、`Explorer:`、`Checked:` の行を入れます。
3. 送金カードの許可リストの行（``by `abbreviation` ``）に、そのコードを追加します。
4. テストネットがあるチェーンなら、`dev/test_cases.py` にテストネットの落とし穴ケースを追加します。
5. DeepSeek Flash で 3 回中 3 回合格すること。

</details>

<details>
<summary>古くなった情報</summary>

各チェーンファイルの `Checked:` の日付を、ときどき確認し直します。

</details>

<details>
<summary>リリース</summary>

ユーザーは `main` からインストールするので、`main` はリリースのときだけ動かします。

1. `skills/coinwallet/VERSION`、`.claude-plugin/plugin.json`、`.codex-plugin/plugin.json` に同じ `X.Y.Z` を書きます。
2. 必須の Host × モデルがすべてテストプランに合格すること。
3. `~/.hermes/hermes-agent/venv/bin/python dev/hermes_scan.py` で high や critical の指摘がないこと。
4. `python3 dev/check_repo.py --tag vX.Y.Z` が通ること（3 つのバージョンがタグと一致するか確認します）。
5. `main` にマージし、タグ `vX.Y.Z` を付けてプッシュし、GitHub Release のノートを書きます（`gh release create vX.Y.Z`）。

</details>
