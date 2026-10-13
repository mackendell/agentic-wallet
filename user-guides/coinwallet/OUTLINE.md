# CoinWallet user guide: content outline

Status: draft for review. No pages written yet.

Built on [Diátaxis](https://diataxis.fr/): four kinds of page, each with one job.

| Kind | Reader is… | Page answers |
|---|---|---|
| **Tutorial** | new, learning | "Walk me through it once, start to finish" |
| **How-to** | working, has a goal | "How do I do X?" |
| **Reference** | working, needs a fact | "What does this screen / setting / status mean?" |
| **Explanation** | studying, wants to understand | "Why does it work this way?" |

FAQ is not a Diátaxis kind. Here it is a **router**: one page of short questions, each answered in 1–3 sentences and linking to the how-to, reference or explanation page that holds the real answer. Nothing is explained only in the FAQ.

Target: App 2.0.31 (Android and iOS). English first; zh-Hans, zh-Hant, ja follow (the App is only fully translated in those four).

Legend for the **Source** column:
- **migrate**: existing page is still right; move and tidy
- **rewrite**: existing page is out of date or mixes kinds
- **new**: nothing exists yet
- 📷 = screenshots already captured on `research/app-screens`; 📷? = still to capture

---

## Home

| Page | Purpose | Source |
|---|---|---|
| Welcome to CoinWallet | What CoinWallet is, the three wallet types in one line each, where to start (links into the four sections) | rewrite `coinwallet/introduction` |

## 1. Tutorials (learning by doing, one path each, no choices)

| Page | Purpose | Source |
|---|---|---|
| Your first wallet | Install → language → PIN → create a Seed Phrase Wallet → back up the phrase → see your receiving address | rewrite `setup/creating-a-wallet` 📷 |
| Receive and send your first crypto | Copy an address, receive a small amount, send it back, find it in Activity | rewrite `sending-and-receiving` 📷? |
| Your first MPC wallet with a co-owner | Create a 2-of-2 MPC wallet on **Testnet**, invite a second phone, both claim, send 1 test coin, approve it | **new** 📷 (screens 08–21) |

## 2. How-to guides (one goal per page)

### Wallets
| Page | Source |
|---|---|
| Create a Seed Phrase Wallet | migrate `setup/creating-a-wallet` (split) |
| Create an MPC wallet | rewrite `cn/创建MPC分片私钥` (English is missing today) 📷 |
| Join an MPC wallet with an invitation code | **new** 📷 |
| Invite members and finish creating an MPC wallet | **new** 📷 (Invite Members, Create, Claim, Complete) |
| Cancel an MPC wallet that is still being set up | **new** 📷 (Cancel Creation) |
| Import a wallet (seed phrase / private key / Keystore / MPC shard) | migrate the 4 import pages into one page with tabs |
| Back up and export a seed phrase or private key | migrate `export-seed-phrase`, `export-address-private-key` |
| Replace the device that holds your MPC shard | rewrite `cn/MPC替换设备` (English missing) |
| Delete a wallet from this device | migrate `delete-private-key` |
| Use a custom TEE | migrate `setup/how-to-setup-custom-tee` |

### Sending, receiving, approving
| Page | Source |
|---|---|
| Receive crypto | split from `sending-and-receiving` |
| Send crypto | split from `sending-and-receiving` |
| Send to an exchange that needs a memo or tag | **new** (XRP tag, TRX/SOL/EOS memo; which chains can't) |
| Approve or reject an MPC transfer | **new** 📷 (Activity → Require Action → Approve, 15-min window) |
| Set the network fee by hand | migrate `how-to-manually-set-gas-fee` |
| Find a transaction hash | migrate |
| Send and receive NFTs | migrate `add-nft` + `send-nft` |
| Cash out to fiat | migrate `withdraw-exchange-to-fiat` |

### Addresses and tokens
| Page | Source |
|---|---|
| Add an address for another coin | migrate `add-wallet-addresses` |
| Add a token that isn't listed | migrate `add-new-token` |
| Save addresses in the Address Book | migrate |
| Use one address across EVM chains (custom derivation path) | migrate `cn/自定义派生路径` + Advanced Mode page |
| Activate an EOS account | migrate |
| Convert Ethereum MATIC to POL | migrate |

### Security and settings
| Page | Source |
|---|---|
| Change the language and time zone | migrate `cn/区域设置` 📷 |
| Turn on biometrics, Auto-lock and 2FA | migrate `setup/2fa` + new 📷 (Settings → Security) |
| Reset your PIN | rewrite `reset-wallet-password` (now "Security PIN") 📷 |
| Turn push notifications on or off | **new** 📷 |
| Unlock Testnet | rewrite `how-to-turn-on-testnet` (2.0.31: About App → tap logo 8×, then "Environment" appears on Customize MPC Wallet; there is no Settings toggle) 📷 |

### Fixing problems
| Page | Source |
|---|---|
| Recover assets sent to the wrong EVM network | migrate (merge the two duplicate pages) |
| "TRX balance is less than the gas fee required" | rewrite from FAQ into a how-to |
| A transfer is stuck on Pending | **new** (approval expired, not enough members, check Activity) |
| Send a debug log or report a bug | migrate `cn/Debug Log`, `cn/提交BUG` |

## 3. Reference (facts to look up, no steps)

| Page | Purpose | Source |
|---|---|---|
| Screens at a glance | Home, side panel, Crypto / NFT / Activity, transfer Details (Request / Parameter / Approval) | **new** 📷 |
| Settings | Every row in Settings, what it does | **new** 📷 |
| Transfer statuses | Pending (with timer), Confirming, Successful, Rejected, Expired; what each needs from you | **new** 📷 |
| MPC wallet options | Number of key shards, Approval/Restore threshold, Key Shard Backup, Environment; what can't be changed later | **new** 📷 |
| Supported networks and tokens | Mainnet and Testnet chains, which take a memo/tag, minimum balances (XRP reserve, TRX activation, SOL rent…) | rewrite `cn/支持网络` + research/chain-send-rules.md |
| Languages | 8 App languages; only en / zh-Hans / zh-Hant / ja are fully translated | **new** |
| Glossary | Shard, threshold, TEE, Room, invitation code, gas, memo/tag, Testnet… | **new** |
| Release notes | Version history | rewrite `product-roadmap` |

## 4. Explanation (understanding, no steps)

| Page | Purpose | Source |
|---|---|---|
| Seed Phrase vs MPC wallets | Which to choose and why ("bank account" vs "joint account") | rewrite from `setup/creating-a-wallet` |
| How MPC key shards work | No single full key, threshold, TEE, why each member claims | **new** |
| How your keys are protected on the phone | Secure hardware (2.0.25 upgrade), PIN vs biometrics vs 2FA | rewrite `what-is-wallet-security-upgrade` |
| Mainnet and Testnet | What Testnet is for, why it's hidden | **new** |
| Network fees | Gas, who pays, why fees change | migrate `what-are-gas-fees` |
| Memos and destination tags | Why exchanges need them, what happens if you forget | **new** |
| HD wallets and derivation paths | One seed, many addresses | migrate |
| Hot and cold wallets | | migrate `what-is-cold-wallet` |
| Token approvals | Why some sends need an "approve" first | migrate |

## 5. FAQ (router: short answer + link)

About 20 questions, grouped: Getting started · MPC wallets · Sending · Fees · Security · Troubleshooting. Examples:
- I lost my phone. Can I get my wallet back? → *Replace the device…* / *Import a wallet*
- Why is my MPC transfer still "Pending"? → *A transfer is stuck on Pending*
- How long do I have to approve? → 15 minutes → *Approve or reject an MPC transfer*
- How long is an invitation code valid? → 60 minutes → *Join an MPC wallet*
- I sent crypto to the wrong address. → *What if…* (rewrite) 
- Why are some words still in English in my language? → *Languages*
- Can I change the threshold later? → No → *MPC wallet options*

---

## Open points for review

1. **Replace or add?** This plan replaces the current English CoinWallet section and fixes the gap where MPC pages exist only in Chinese.
2. **CoinWallet Center (Beta)** pages (bind device, contracts) are left out; say if they belong here.
3. **iOS screenshots**: everything captured so far is Android. iOS-only differences need a check.
4. **Screens still to capture**: Seed Phrase backup, send flow, Settings → Security, Rejected/Expired status.
