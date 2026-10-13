# CoinWallet App: Newbie journey from the docs

Research for [#2](https://github.com/mackendell/agentic-wallet/issues/2) (map [#1](https://github.com/mackendell/agentic-wallet/issues/1)). Researched 2026-10-13. Terms follow `CONTEXT.md`.

**Question:** Using the official CoinWallet docs and site, what exact steps does a **Newbie** take in the App to reach a **First transfer** with an agent?

## Sources

Every fact below cites one of these primary sources by its key.

| Key | Source |
| --- | --- |
| [EN-intro] | https://coinsdo.gitbook.io/docs/coinwallet/introduction |
| [EN-create] | https://coinsdo.gitbook.io/docs/coinwallet/setup/creating-a-wallet |
| [EN-testnet] | https://coinsdo.gitbook.io/docs/coinwallet/how-to/how-to-turn-on-testnet |
| [EN-send] | https://coinsdo.gitbook.io/docs/coinwallet/how-to/sending-and-receiving-crypto-currencies |
| [EN-activity] | https://coinsdo.gitbook.io/docs/coinwallet/how-to/activity |
| [EN-2fa] | https://coinsdo.gitbook.io/docs/coinwallet/setup/two-factor-authentication-2fa |
| [EN-secupg] | https://coinsdo.gitbook.io/docs/coinwallet/faq/what-is-wallet-security-upgrade |
| [EN-tee] | https://coinsdo.gitbook.io/docs/coinwallet/setup/how-to-setup-custom-tee |
| [CN-about] | https://coinsdo.gitbook.io/docs/cn/coinwallet/guan-yu-coinwallet |
| [CN-firstrun] | https://coinsdo.gitbook.io/docs/cn/coinwallet/zhu-yao-she-zhi/shou-ci-chuang-jian-qian-bao-mi-ma (首次创建钱包密码, first-run and wallet password) |
| [CN-mpc] | https://coinsdo.gitbook.io/docs/cn/coinwallet/zhu-yao-she-zhi/chuang-jian-mpc-fen-pian-si-yao (创建MPC分片私钥, create MPC shard key) |
| [CN-testnet] | https://coinsdo.gitbook.io/docs/cn/coinwallet/qi-ta-cao-zuo/qi-yong-ce-shi-lian-gong-neng (启用测试链功能, enable Testnet) |
| [CN-region] | https://coinsdo.gitbook.io/docs/cn/coinwallet/qi-ta-cao-zuo/qu-yu-she-zhi (区域设置, region settings) |
| [CN-deploy] | https://coinsdo.gitbook.io/docs/cn/coinwallet-center-beta/he-yue-bu-shu (CoinWallet Center contract deploy, approved in the App) |
| [CN-interact] | https://coinsdo.gitbook.io/docs/cn/coinwallet-center-beta/he-yue-jiao-hu (CoinWallet Center contract call, approved in the App) |
| [SITE] | https://coinwallet.coinsdo.com/en |
| [IOS] | https://apps.apple.com/us/app/coinsdo-wallet-btc-eth-wallet/id6479635869 (and iTunes lookup API `https://itunes.apple.com/lookup?id=6479635869`) |
| [PLAY] | https://play.google.com/store/apps/details?id=com.coinsdo.wallet |
| [SKILL-wf] | `skills/agent-wallet/references/workflows.md` (this repo, Get Started and Wallet Onboarding sections) |

Note on docs language: the step-by-step MPC create/join flow, the first-run flow, region (language) settings and in-App approval exist **only in the Chinese docs**. The English docs describe the four creation options but not the MPC Room flow ([EN-create]). Chinese button labels quoted below are the docs' own; English labels are given only where an English doc states them.

## 1. Where to download the App

| Platform | Official link | Source |
| --- | --- | --- |
| iOS | https://a8ata.app.link/coinwallet_ios, which resolves to App Store id **6479635869**, listed as "CoinsDo Wallet: BTC ETH Wallet", seller Tecstation Pte Ltd, version 2.0.30 (2026-08-12) | [SITE], [IOS] |
| Android | https://a8ata.app.link/coinwallet_android, which resolves to Google Play `com.coinsdo.wallet`, listed as "CoinWallet: BTC USDT Wallet", updated Jul 29, 2026 | [SITE], [PLAY] |
| Chrome extension | https://chromewebstore.google.com/detail/coinwallet-btc-crypto-wal/oafedfoadhdjjcipmcbecikgokpaphjk | [SITE] |

Contradiction: the docs' iOS link `https://apps.apple.com/kg/app/coinsdo/id1631258517` ([EN-intro], [CN-about]) returns **HTTP 404** as of 2026-10-13, and the iTunes lookup API returns 0 results for that id. Use the [SITE] link or id 6479635869. The App's store name also differs by platform ("CoinsDo Wallet" on iOS, "CoinWallet" on Android) ([IOS], [PLAY]).

## 2. Newbie step list, each tied to an App screen

Screen names: English where an English doc names them, otherwise the Chinese doc's label with a translation. "Creator" = the Newbie; "agent" = the **MCP service** participant.

| # | Who | Step | App screen | Source |
| --- | --- | --- | --- | --- |
| 1 | Newbie | Download and install the App (section 1). | App Store / Google Play listing | [SITE] |
| 2 | Newbie | First launch shows a scam alert (诈骗警报); close it with "x". | **Scam alert pop-up** | [CN-firstrun] |
| 3 | Newbie | Page through the intro screens; the top-right icon switches the default language. | **Intro / guide pages (引导页)** with language icon | [CN-firstrun] |
| 4 | Newbie | Tap "开始使用" (Get started); set the wallet password: a 6-digit PIN entered twice, or an 8–18 character password (switch type top right). | **Create wallet PIN** | [CN-firstrun], [EN-create] |
| 5 | Newbie | Enable biometric authentication. | **Biometric prompt** | [CN-firstrun] |
| 6 | Newbie | Choose among four options: Seed Phrase Wallet, **MPC Wallet**, Import Wallet, Join MPC Wallet. Pick **MPC Wallet**. (Later, from the home screen, the docs say "+Add wallet" top left, then "+ mpc钱包".) | **Wallet creation (four options)** | [EN-create], [CN-firstrun], [CN-mpc] step 1 |
| 6a | Newbie | Only if Testnet was switched on first (section 3): this screen offers Mainnet / Testnet. Otherwise no network choice is shown. | Wallet creation / import screen with network choice | [EN-testnet], [CN-testnet] step 4 |
| 7 | Newbie | Enter the number of shards (分片数量) and the approval threshold (审批阈值). Optional "CoinsDo托管" (CoinsDo custody): CoinsDo holds one shard and **auto-approves transactions**. Tap "继续" (Continue). | **MPC setup: shards and threshold** | [CN-mpc] step 2 |
| 8 | Newbie | Enter the MPC wallet name, own shard name, theme color; tap "确认" (Confirm). This opens the **Room**. | **MPC wallet name / shard name** | [CN-mpc] step 2 |
| 9 | Newbie | The **Invitation code** is shown on this screen with a countdown; all invitees must join within the remaining time shown. Copy it and give it to the agent. | **Invitation code screen (with remaining time)** | [CN-mpc] step 3 |
| 10 | Agent | Joins the Room with the Invitation code and a display name (`join_mpc_wallet`, `invitationCode` + `custodianName`). In the App flow a human invitee instead uses side panel → "加入MPC钱包" (Join MPC Wallet) → code → "继续", then "接受" (Accept), shard name, color, "立即加入" (Join now). | (agent side: none) | [SKILL-wf] Wallet Onboarding; [CN-mpc] steps 4–5 |
| 11 | Newbie | The joined participant's shard name appears in the **group member list (群组成员列表)**; the invitee can still "离开" (Leave) here. | **Room member list** | [CN-mpc] step 5 |
| 12 | Newbie | When everyone has joined, tap "创建" (Create), then "领取分片私钥" (Claim shard key), and tell invitees to claim theirs. | **Room member list → Create** | [CN-mpc] step 6 |
| 13 | Newbie | Set a backup-file password, choose a backup method, then "是的，我已备份" (Yes, I have backed up). | **Shard backup** | [CN-mpc] step 7 |
| 14 | Newbie | Wait screen until all invitees claim shards, then "完成" (Done); App jumps to the asset page with default assets. Creation is complete. | **Waiting for invitees → Asset (Crypto) list** | [CN-mpc] steps 8–9 |
| 15 | Agent | Confirms the wallet is ONLINE (`get_wallet`) after the user reports creation complete. | (agent side) | [SKILL-wf] Wallet Onboarding step 4 |
| 16 | Agent | Submits a transfer from the Mainnet wallet. | (agent side) | CONTEXT.md **First transfer** |
| 17 | Newbie | Approve: open the App, tap "Activity", open the record whose status is "待处理" (Pending), tap "批准" (Approve), verify identity; status becomes "确认中" (Confirming), then "链上成功" (On-chain success). | **Activity list → transaction detail → Approve** | [CN-deploy] step 4, [CN-interact] steps 4–6, [EN-activity] |
| 17a | Newbie | Identity verification at approval uses device biometrics or device passcode on App ≥ 2.0.25 (not the App password); 2FA applies if enabled. | **Device verification / 2FA prompt** | [EN-secupg], [EN-2fa] |

Caveat on step 17: the only documented in-App approval of an externally submitted transaction is the **CoinWallet Center** contract deploy/call flow ([CN-deploy], [CN-interact]). No doc page covers approving an MPC *transfer* submitted by another participant. The screen path is likely the same but is not confirmed by the docs.

## 3. Mainnet vs the hidden Testnet switch

- A freshly installed App hides the Testnet feature ([CN-testnet] step 3).
- To reveal it: Settings → **About App**, tap the App logo **8 times** in a row; a message says Testnet is enabled ([EN-testnet] steps 1–2, [CN-testnet] steps 1–2). The Chinese doc reaches About App by tapping the wallet name top left, then the "关于App" icon ([CN-testnet] step 1).
- Back on Settings home, turn on **Testnet** (green = on) ([EN-testnet] step 3, [CN-testnet] step 4).
- Effect: the wallet creation / import screen then offers Mainnet / Testnet. With the toggle off (grey), no network choice is shown ([EN-testnet], [CN-testnet] step 4). So the **Wallet network** is chosen per wallet at creation; by default every new wallet is Mainnet. This matches CONTEXT.md **First transfer**.
- The docs do not say whether an existing wallet's network can change, or how the App labels a Testnet wallet in lists.

## 4. Supported App languages

- App Store listing: **English, Japanese, Simplified Chinese, Traditional Chinese** (iTunes `languageCodesISO2A`: EN, JA, ZH, ZH) ([IOS]).
- The Google Play listing does not list languages ([PLAY]).
- In-App switching: on the first-run intro pages (top-right icon) ([CN-firstrun] step 2), and later under wallet name → Settings → "区域" (Region) → language and time zone ([CN-region]).
- The docs do not list the languages; the official site's switcher offers only English ([SITE]). Docs exist in English and Chinese only (https://coinsdo.gitbook.io/docs/llms.txt).

## 5. Screenshot checklist (for the next ticket)

Capture each screen in **each of the 4 App languages**: English, Japanese (日本語), Simplified Chinese (简体中文), Traditional Chinese (繁體中文). Use the current store build (iOS 2.0.30 or the current Android build) and note the version and platform on each file. Name files `<nn>-<screen>-<lang>.png` (lang = en, ja, zh-Hans, zh-Hant).

| # | Screen | What must be visible |
| --- | --- | --- |
| 01 | Language picker (intro pages, top-right icon) | The list of languages exactly as offered |
| 02 | Settings → Region (区域) | Language entry and its current value |
| 03 | Wallet creation (four options), Testnet **off** | All four option labels; no network choice |
| 04 | Settings → About App | The App logo to tap and the App version |
| 05 | Toast after 8 taps | The "Testnet enabled" message text |
| 06 | Settings home with Testnet toggle | The toggle label, on (green) |
| 07 | Wallet creation with Testnet **on** | The Mainnet / Testnet choice labels |
| 08 | Home → "+Add wallet" menu | The add-wallet entry and the MPC wallet entry |
| 09 | MPC setup: shards and threshold | Shard count, threshold fields, the CoinsDo custody option and its explanation, Continue button |
| 10 | MPC wallet name / shard name | Field labels, color picker, Confirm button |
| 11 | Invitation code screen | The code area (code may be blurred), copy/share control, remaining-time countdown, any explanatory text |
| 12 | Room member list after the agent joins | The agent's display name in the member list, the Create button, status text |
| 13 | Claim shard key | Button label and any prompt text |
| 14 | Shard backup | Backup password field, backup method choices, "Yes, I have backed up" button |
| 15 | Waiting for invitees | Waiting text, per-member claim status, Done button |
| 16 | Asset (Crypto) list after creation | Wallet name, Mainnet/Testnet marker if any, default assets |
| 17 | Wallet switcher / side panel | How a Mainnet and a Testnet wallet are distinguished in the wallet list |
| 18 | Activity list with the agent's pending transfer | The record and its pending status label |
| 19 | Transaction detail of the pending transfer | Amount, asset, recipient, fee, initiator if shown, Approve and Reject button labels |
| 20 | Identity verification at approval | Biometric / device passcode prompt and 2FA prompt if enabled |
| 21 | Result after approval | Success message and the new status (Confirming / On-chain success) |
| 22 | Join MPC Wallet entry (side panel) | Label of the join entry, for the case where the agent creates and the user joins (optional) |

## 6. Gaps and contradictions in the current skill text

Against [SKILL-wf] Get Started step 2 and Wallet Onboarding:

1. **Download links:** the skill points only to https://coinwallet.coinsdo.com/en. That page does carry working store links ([SITE]); the docs' iOS link is dead (section 1). The skill should never repeat the docs' `id1631258517` link.
2. **Invitation code expires:** the docs say invitees must join within the remaining time shown ([CN-mpc] step 3). The skill does not warn the user to send the code promptly or what to do on expiry.
3. **Creation is a multi-step creator action:** the skill says "finish creation in the App". The docs show Create → Claim shard key → backup with password → wait for **all invitees to claim** → Done ([CN-mpc] steps 6–9). Whether the agent must claim its shard (and whether the MCP service does that automatically) is not in the docs or the skill.
4. **Threshold choice decides approvals:** the shard count and threshold are set by the Newbie ([CN-mpc] step 2). The skill gives no guidance, yet the threshold decides whether the agent's transfer needs the user's approval. The "CoinsDo托管" option auto-approves transactions ([CN-mpc] step 2), which matters for a First transfer.
5. **Display name:** the skill asks for "the name you want me to display"; in the App this appears as a shard name in the Room member list ([CN-mpc] step 5).
6. **Testnet is hidden:** the skill shows wallets "by name and mainnet/testnet" but never explains that the App creates Mainnet wallets unless the hidden switch is on (section 3).
7. **User-side approval in the App:** the skill covers only the agent's `approval_transaction`. It never tells the user to approve in the App via Activity → Pending → Approve (step 17).
8. **Mainnet First transfer vs skill policy:** `skills/agent-wallet/SKILL.md` says "Consumer mainnet transfers stop at preparation by default", while CONTEXT.md defines **First transfer** as an agent-submitted Mainnet transfer. A First transfer needs the policy gates to pass, or the policy needs an exception.
9. **Button names by language:** CONTEXT.md requires the exact App text per language, but the docs give only Chinese labels for most of the MPC flow, so the skill cannot name buttons until the screenshots in section 5 exist.

## 7. Unknown / not in the docs

- The MPC Room flow and in-App approval in **English, Japanese or Traditional Chinese** wording: no doc page exists in those languages ([EN-create] covers options only).
- How a participant approves an MPC **transfer** submitted by another participant (the agent). Only CoinWallet Center contract approvals are documented ([CN-deploy], [CN-interact]).
- Whether the agent counts toward the threshold, and recommended shard/threshold values for a user + agent wallet.
- Whether the agent (MCP service) must "claim" its shard, and what the creator's wait screen shows for it.
- Invitation code length/format and exact expiry duration ([CN-mpc] shows only "remaining time").
- Whether an expired Room can be restarted or the code regenerated.
- How the App marks a wallet as Mainnet vs Testnet in lists, and whether the network can be changed after creation.
- Whether push notifications alert the user to a pending approval (listed as a 2025 Q3 roadmap item, status not updated: https://coinsdo.gitbook.io/docs/coinwallet/product-roadmap).
- The full in-App language list (store listing only; docs are silent) and whether the Android build matches iOS.
- Whether the Chrome extension supports MPC Rooms or approvals ([SITE] lists it; [EN-secupg]'s Chrome section is empty).
- Custom TEE setup ("Coming soon!" [EN-tee]), which may matter for where shards are held.
- Whether current App screens still match the docs' screenshots (docs carry no App version; the security upgrade changed verification at 2.0.25 [EN-secupg]).
