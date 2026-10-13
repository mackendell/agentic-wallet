# Fee, reserve and tag rules for each supported chain

Research for [#13](https://github.com/mackendell/agentic-wallet/issues/13). Gathered 2026-10-13.

## Which chains the MCP service supports

Source: `get_chains` and `get_currencies` (read-only) on a local MCP service, `coinsdo-wallet-mcp v1.0.5`, Service environment `test`, called on 2026-10-13 [MCP]. Mainnet (`netType 2`) returns **44 chains**. Testnet returns 41: the same list minus xDai, Matchain and Ethereum Proof of Work. The chain list might be different in `prod`, which I did not check.

`get_currencies` (Mainnet) returns 599 assets: 46 native coins (`currencyType 1`) and 553 tokens (`currencyType 3`). Only 17 chains have any token: ETH 333, BSC 102, SOL 31, TRX 21, POL 17, AVAXC 16, FTM 10, HT 9, ARB1 8, OP 5, BASE 4, XDAI 4, BTC 3 (Omni), VET 2, SONIC 2, OKT 2, CRO 2. On the other 27 chains only the native coin can be sent.

### Things that hold for every chain

- **The MCP can only send a memo on some chains.** Per the `send_transaction` docs, `memo` works on `xrp, eos, trx, trc20, sol, spl, algo, atom`, and on XRP it must be a number [README]. Stellar, TON, Symbol and Vaulta are missing from that list, yet exchanges on those chains usually need a memo. **If the receiver needs a memo on a chain without memo support, the agent must stop.** It must not send without the memo.
- **The MCP has no fee tool.** The fee is shown in the App when the user approves (see the #7 resolution). What follows tells the agent what the fee is paid in and what can make a send fail.
- **Some of the service's coin names are not the real gas coin ticker.** ARB1, OPT, BASE and ZK all pay gas in ETH. MATIC is now POL. AVAXC is AVAX. SONIC is S. XLAYER is OKB. TON is now Gram. VAULTA is A. When telling the user what to top up, use the real name ("send some ETH on Arbitrum").
- **Fake tokens.** A USDT or USDC whose contract is not in the "real" row for that chain is a fake or a bridged copy. Tether's list [TETHER] and Circle's list [CIRCLE] are the only sources used for "real".

### Chains the service still lists that are shut down or being shut down

| Chain (service code) | Status | Source |
|---|---|---|
| OKT Chain (OKT) | OKX said it would shut down on 2026-01-01; OKT was converted to OKB | [OKTC] |
| Huobi Token / HECO (HT) | HECO DAO said operations would stop on 2025-01-15 | [HECO] |
| Fantom (FTM) | Opera is legacy infrastructure; the Opera FTM→S bridge closed 2026-06-30 17:00 GMT | [SONIC-OPERA] |
| Polkadot relay (DOT_OLD) | Balances and transfers moved to Asset Hub on 2025-11-04 | [DOT-ED] |
| EOS (EOS) | Rebranded to Vaulta with a 1:1 EOS→A swap (May 2025); the service lists both | [VAULTA] |

The agent should warn the user, and probably block sends, on these chains. That decision belongs to #14.

---

## Account and tag chains (where most sends go wrong)

### Tron (TRX)

| | |
|---|---|
| Gas coin | TRX |
| Fees | Paid in Bandwidth (every tx) and Energy (smart-contract calls, which includes TRC20/USDT). Each activated account gets 600 free Bandwidth per day. Energy has no free amount. Resources come from staking TRX or from **another account delegating them** (`DelegateResourceContract`; this is how energy "rental" works). Whatever is not covered is paid by **burning TRX**: 1,000 sun per Bandwidth and 100 sun per Energy at the moment. Both rates are chain parameters (#3, #11) and can change [TRON-RES] [TRON-PAY] [TRON-BE] |
| Activation | A direct TRX/TRC10 transfer to an address that has never been used costs an extra **1 TRX** account-creation fee, and free Bandwidth cannot pay for it. Creating an account inside a contract call (for example, sending USDT to a new address) adds **25,000 Energy** [TRON-PAY] |
| Min balance | None. But a TRC20 send with 0 TRX and no staked or delegated energy fails, because the fee is burned TRX |
| Tag/memo | Not used for deposits (each user gets their own address). The MCP accepts a memo on TRX/TRC20 [README] |
| USDT (real) | `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t` [TETHER] (the service lists the same) |
| USDC | **Discontinued.** Circle stopped minting USDC on Tron in Feb 2024; transfers and redemptions continued only until Feb 2025 [CIRCLE-TRON]. The service still lists `TEkxiTehnzSmSe2XqrBj4w32RUN966rdz8`. Warn before any send |

### XRP Ledger (XRP, "Ripple")

| | |
|---|---|
| Gas coin | XRP (the fee is burned; very small) |
| Min balance | **Base reserve 1 XRP** plus **0.2 XRP for each owned object** (trust line, offer, etc.). Reserved XRP cannot be sent, only spent on fees [XRP-RES] |
| Activation | A new address only exists once it receives at least the base reserve [XRP-RES]. Sending less than 1 XRP to a new address fails |
| Tag | **Destination tag** (32-bit unsigned integer) tells an exchange which customer to credit. If the receiver set `RequireDest`, a payment without a tag is rejected. If not, the funds arrive but may not be credited, and getting them back takes manual work [XRP-TAG]. The MCP requires a numeric memo on XRP [README] |
| USDT | No Tether deployment [TETHER] |
| USDC (real) | `USDC` issued by `rGm7WCVp9gb4jZHWTEtGUr4dd74z2XuWhE` [CIRCLE]. The service does not list it, so it cannot be sent |

### Stellar (XLM)

| | |
|---|---|
| Gas coin | XLM. Minimum 100 stroops (0.00001 XLM) per operation, more during surge pricing [XLM-FEE] |
| Min balance | **2 base reserves = 1 XLM**, plus 0.5 XLM for each subentry (trustline, offer, signer, data) [XLM-LUMENS] |
| Activation | A Payment to an account that does not exist fails with `PAYMENT_NO_DESTINATION`. The account must first be created with Create Account. Non-native assets need a trustline (`PAYMENT_NO_TRUST`) [XLM-OPS] |
| Tag/memo | Memo types: text (up to 28 bytes), id (uint64), hash, return. They are used to tell pooled (exchange) accounts apart, and muxed accounts are the newer way to do this [XLM-TX]. **The MCP does not support a memo on XLM** [README] |
| USDT | No Tether deployment [TETHER]. (USDT0 has a Stellar contract, but the service does not list it [USDT0]) |
| USDC (real) | `USDC-GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN` [CIRCLE]. Not listed by the service |

### EOS (EOS) and Vaulta (VAULTA)

| | |
|---|---|
| Gas coin | No per-tx fee. The sender needs **CPU and NET**, rented for 24 h through PowerUp, and **RAM**, bought on a market (0.5% trade fee) [VAULTA-RES] |
| Activation | Accounts are 12-character names, not addresses. A new account must be created and paid for by an existing account [VAULTA-ACCT] |
| Memo | The memo is how exchanges route deposits. A transfer without one may be rejected or not credited [EOS-MEMO]. The MCP supports a memo on `eos` but does not list `vaulta` [README]. Check this before a Vaulta send |
| Rebrand | EOS became Vaulta in May 2025 with a 1:1 EOS→A swap [VAULTA]. The service lists both the EOS and VAULTA chains |
| USDT | **Deprecated.** Tether no longer issues or redeems USDT on EOS/Vaulta [TETHER] |
| USDC | None [CIRCLE] |

### Solana (SOL)

| | |
|---|---|
| Gas coin | SOL. Base fee 5,000 lamports per signature, plus an optional priority fee [SOL-FEE] |
| Min balance | Every account must keep a rent-exempt minimum that depends on its size. A plain wallet (0 data) needs 890,880 lamports ≈ 0.00089 SOL [SOL-ACCT] |
| Token accounts | SPL tokens sit in an **associated token account (ATA)** for each wallet and mint. Creating one costs 2,039,280 lamports (0.00203928 SOL) of rent, or 0.00207408 SOL for Token-2022, paid by whoever creates it. The rent comes back when the account is closed [SOL-ATA]. Sending USDT/USDC to a wallet with no ATA means the sender pays to create it |
| Memo | The MCP accepts a memo on `sol`/`spl` [README]. Some exchanges use one |
| USDT (real) | `Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB` [TETHER] |
| USDC (real) | `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v` [CIRCLE] |

### The Open Network (TON)

| | |
|---|---|
| Gas coin | **Gram** (ticker GRAM). Toncoin/TON was renamed on 2026-06-15; no swap is needed, and any site that asks you to "swap" or "claim" is a scam [TON-GRAM]. The service still calls it TON |
| Fees | Compute, forward and storage fees. Storage fees build up over time, and an account that cannot pay them can be frozen [TON-FEE] |
| Addresses | `EQ…` = bounceable, `UQ…` = non-bounceable. Send to wallets with the non-bounceable form so the funds are credited even if the receiving wallet is not yet deployed. Check that the recipient is initialized before sending [TON-ADDR] |
| Memo | Exchanges use a text comment. **The MCP does not support a memo on TON** [README] |
| USDT (real) | Jetton `EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRv7Nw2Id_sDs` [TETHER]. Not listed by the service |
| USDC | None [CIRCLE] |

### Algorand (ALGO)

| | |
|---|---|
| Gas coin | ALGO. Minimum fee 0.001 ALGO [ALGO-PARAM] |
| Min balance | **0.1 ALGO**, plus 0.1 ALGO for each asset opt-in [ALGO-PARAM] |
| Opt-in | The receiver must opt in to an asset before it can hold it [TETHER] |
| Memo | Note field, up to 1,024 bytes [ALGO-PARAM]. The MCP accepts a memo on `algo` [README] |
| USDT | **Deprecated** (asset 312769) [TETHER] |
| USDC (real) | Asset `31566704` [CIRCLE]. Not listed by the service |

### Cosmos Hub (ATOM)

| | |
|---|---|
| Gas coin | ATOM. Fee = ceil(gas × gas price), where gas price is set by the feemarket module [ATOM] |
| Memo | A standard tx field. Exchanges need it [ATOM]. The MCP accepts a memo on `atom` [README] |
| USDT / USDC | No Cosmos Hub deployment (Tether's "Cosmos" entry is on Kava) [TETHER] [CIRCLE] |

### Polkadot Asset Hub (DOT) and Polkadot relay (DOT_OLD)

| | |
|---|---|
| Gas coin | DOT |
| Min balance | **Existential deposit 0.01 DOT on Asset Hub** (1 DOT on the relay chain). An account that falls below it is reaped and loses the remainder [DOT-ED] |
| Migration | Balances and transfers moved from the relay chain to Asset Hub on 2025-11-04 [DOT-ED]. Prefer DOT (Asset Hub) and avoid DOT_OLD |
| USDT (real) | Asset ID `1984` on Asset Hub. It is a "sufficient" asset, so the receiver needs no DOT [TETHER] [DOT-ED]. Not listed by the service |
| USDC (real) | Asset ID `1337` [CIRCLE]. Not listed |

### NEAR Protocol (NEAR)

| | |
|---|---|
| Gas coin | NEAR |
| Min balance | Storage staking: 1 NEAR per 100 KB. A new account gets 770 bytes for a one-time 0.007 NEAR. A tx fails if the account cannot cover new storage [NEAR-STORAGE] |
| USDT (real) | `usdt.tether-token.near` [TETHER]. Not listed |
| USDC (real) | `17208628f84f5d6ad33f0da3bbbeb27ffcb398eac501a31bd6ad2011e36133a1` [CIRCLE]. Not listed |

### Cardano (ADA)

| | |
|---|---|
| Gas coin | ADA |
| Min balance | Every output needs a **minimum amount of ADA** ((160 + output size) × coinsPerUTxOByte, about 1 to 1.5 ADA). Smaller outputs are rejected [ADA-EX] [ADA-NT] |
| Memo | None |
| USDT / USDC | None [TETHER] [CIRCLE] |

### Symbol (XYM)

| | |
|---|---|
| Gas coin | XYM |
| Memo | Transfers can carry a message (up to 1,023 characters), and exchanges use it. Mosaics can be sent to any valid address, even one with no history [XYM]. **The MCP does not support a memo on XYM** [README] |

### Filecoin (FIL)

| | |
|---|---|
| Gas coin | FIL |
| Addresses | `f1`/`f3` (native) and `f4`/`f410` (= `0x`) addresses. Some exchanges do not take f4/0x addresses. Sending from 0x to f1/f3 needs the FILForwarder contract [FIL] |

### Sui (SUI)

| | |
|---|---|
| Gas coin | SUI. Computation plus storage fees, with up to 99% of storage refunded when it is freed. The gas budget must cover the whole fee [SUI] |
| USDC (real) | `0xdba3…900e7::usdc::USDC` [CIRCLE]. Not listed |

### VeChain (VET)

| | |
|---|---|
| Gas coin | **VTHO**, not VET. Holding VET generates VTHO [VET]. The service lists 2 assets on VET, probably VET and VTHO |

---

## UTXO chains (no tags, no reserves, but dust and address formats)

| Chain | Gas coin | Rules | Source |
|---|---|---|---|
| Bitcoin (BTC) | BTC | No memo. The service lists both `BTC` and `BTC_SEGWIT` address types. Service also lists **Omni USDT (property 31): deprecated**, Tether no longer issues or redeems it | [TETHER] |
| Litecoin (LTC) | LTC | No memo. The service lists `LTC` and `LTC_SEGWIT` | [MCP] |
| Dogecoin (DOGE) | DOGE | Outputs under 0.001 DOGE are invalid. Outputs under 0.01 DOGE need an extra 0.01 DOGE fee each. Recommended fee 0.01 DOGE/kB | [DOGE] |
| Bitcoin Cash (BCH) | BCH | CashAddr format `bitcoincash:q…/p…`, different from legacy Base58 addresses. Do not mix up BTC and BCH addresses | [BCH] |
| Dash (DASH) | DASH | No memo | [MCP] |
| Zcash (ZEC) | ZEC | Transparent `t…` addresses are public; shielded and unified addresses hide amounts. Many exchanges only take transparent addresses. Wallet fee is ZIP-317: 5,000 zatoshis per logical action, minimum 2 actions | [ZEC-317] [ZEC-UA] |

---

## EVM chains (gas coin pays every send; no memo; no reserve)

Every EVM chain has the same rules: the sender needs the gas coin for **every** send, including token sends. There is no memo, no reserve and no activation. A replacement can only be made with `evmNonce` [README].

| Chain (service code / name for its coin) | Real gas coin | Quirks | USDT (real) | USDC (real) | Source |
|---|---|---|---|---|---|
| Ethereum (ETH) | ETH | — | `0xdac17f958d2ee523a2206206994597c13d831ec7` | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` | [TETHER] [CIRCLE] |
| BNB Smart Chain (BSC / BNB) | BNB | **Neither Tether nor Circle issues on BSC.** The service's USDT `0x55d3…7955` and USDC `0x8ac7…580d` are Binance-Peg tokens | none official | none official | [TETHER] [CIRCLE] [BSC-USDT] [BSC-USDC] |
| Polygon PoS (POL / MATIC) | **POL** (MATIC→POL on 2024-09-04; wallets may still say MATIC) | **USDC vs USDC.e**: both listed. USDC.e `0x2791…4174` is the older bridged version | `0xc2132D05D31c914a87C6611C10748AEb04B58e8F` (became USDT0 on 2025-08-27, same address) | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` | [POL] [USDT0] [USDT0-POL] [CIRCLE] |
| Avalanche C-Chain (AVAXC) | AVAX | — | `0x9702230a8ea53601f5cd2dc00fdbc13d4df4a8c7` | `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E` | [TETHER] [CIRCLE] |
| Arbitrum One (ARB1) | **ETH** | Fee = L2 execution + L1 calldata, changes over time | USDT0 `0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9` (**not listed by service**) | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` | [ARB] [USDT0] [CIRCLE] |
| OP Mainnet (OP / OPT) | **ETH** | Fee = execution + L1 data (+ operator fee after Isthmus) | USDT0 `0x01bFF41798a0BcF287b996046Ca68b395DbC1071` (not listed) | `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` | [OP] [USDT0] [CIRCLE] |
| Base (BASE) | **ETH** | L2 execution + L1 "security" fee | none | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | [BASE] [CIRCLE] |
| ZKsync Era (ZK) | **ETH** | Gas prices differ from Ethereum and depend on L1 prices; native account abstraction | none | `0x1d17CBcF0D6D143135aE902365D2E5e2A16538D4` (not listed) | [ZKSYNC] [CIRCLE] |
| Sonic (SONIC) | **S** | Successor to Fantom (FTM→S 1:1) | none | `0x29219dd400f2Bf60E5a23d13Be72B486D4038894` | [SONIC-OPERA] [CIRCLE] |
| Fantom Opera (FTM) | FTM | **Legacy chain**. Service's USDC `0x0406…5B75` is **Multichain-bridged USDC, de-pegged after the July 2023 Multichain hack** | none | none | [SONIC-OPERA] [FTM-USDC] |
| Cronos (CRO) | CRO | Service's USDT `0x66e4…8770` is **bridged** (Cronos Bridge), not Tether-issued | none | `0x3D7F2C478aAfdB65542BCB44bCeeC05849999d2D` (not listed) | [CRO-USDT] [TETHER] [CIRCLE] |
| Gnosis (XDAI) | xDAI | Native xDAI is not ERC-20 (wxDAI `0xe91D…a97d` is) | none | none | [GNOSIS] |
| X Layer (XLAYER) | **OKB** | Circle warns that X Layer `USDC.e` is bridged and not Circle-backed | USDT0 `0x779Ded0c9e1022225f8E0630b35a9b54bE713736` (not listed) | `0xB6CEceAB302E2E4948951eE7843FC24E92933061` (not listed) | [XLAYER] [USDT0] [CIRCLE] |
| Kaia (KAIA) | KAIA | Dynamic base fee | `0xd077a400968890eacc75cdc901f0356c943e4fdb` (not listed) | none | [KAIA] [TETHER] |
| Core (CORE) | CORE | — | none | none | [MCP] |
| Ethereum Classic (ETC) | ETC | Different chain from ETH; same address format | none | none | [MCP] |
| Ethereum PoW (ETHW) | ETHW | Same address format as ETH | none | none | [MCP] |
| Matchain (MATCH) | BNB per secondary sources (unverified) | — | none | none | [MATCH] |
| AB (AB) | AB (formerly Newton; unverified) | — | none | none | [AB] |
| OKT Chain (OKT) | OKT | **Shut down 2026-01-01** | — | — | [OKTC] |
| HECO (HT) | HT | **Shut down 2025-01-15** | — | — | [HECO] |

"none" means neither Tether's nor Circle's official list has a deployment on that chain. Any USDT/USDC there is bridged or fake.

---

## Lookalike tokens

| Chain | Real | Lookalike in the service list | What to say |
|---|---|---|---|
| Polygon | USDC `0x3c49…3359` | USDC.e `0x2791…4174` | "USDC.e is the older bridged version; many exchanges only take USDC" |
| Tron | — | USDC `TEkx…dz8` | "Circle stopped supporting USDC on Tron; most places will not accept it" |
| BSC | — | USDT, USDC (Binance-Peg) | Normal on BSC, but not issued by Tether or Circle; the receiver must accept BEP20 |
| Fantom | — | USDC `0x0406…5B75` | De-pegged Multichain token, worth cents |
| Cronos | — | USDT `0x66e4…8770` | Bridged; check the receiver accepts it |
| Bitcoin | — | Omni USDT (31) | Deprecated by Tether |

---

## Uncertain

- The chain list comes from the `test` Service environment (v1.0.5). `prod` may list different chains or tokens.
- Whether `memo` really works on Vaulta. The README lists `eos` but not `vaulta`.
- Matchain and AB gas coins come only from secondary sources.
- Exact Tron burn rates and Stellar/XRP reserves can change by governance vote. Values are correct as of the cited pages.
- Whether the service blocks sends on dead chains (OKT, HT) or just lets them fail.

## Sources

- [MCP] Local `coinsdo-wallet-mcp v1.0.5`, `get_chains` netType 1 and 2, `get_currencies` netType 2, called 2026-10-13
- [README] CoinsDo wallet MCP README, `send_transaction`: https://github.com/CoinsDo/coinsdo-wallet-mcp/blob/main/README.md
- [TETHER] Tether supported protocols: https://tether.to/en/supported-protocols/
- [CIRCLE] Circle USDC contract addresses: https://developers.circle.com/stablecoins/usdc-contract-addresses
- [CIRCLE-TRON] Circle, discontinuing USDC on Tron: https://www.circle.com/en/usdc-multichain/tron ; https://www.theblock.co/post/278303/circle-ceases-usdc-support-on-tron
- [USDT0] USDT0 deployments: https://docs.usdt0.to/technical-documentation/deployments
- [USDT0-POL] Polygon, USDT0 on Polygon: https://polygon.technology/blog/native-usdt0-comes-to-polygon-for-lower-fees-and-deeper-liquidity
- [TRON-RES] https://developers.tron.network/docs/resource-model
- [TRON-PAY] https://developers.tron.network/docs/paying-for-resources
- [TRON-BE] https://developers.tron.network/docs/bandwidth-and-energy
- [XRP-RES] https://xrpl.org/docs/concepts/accounts/reserves
- [XRP-TAG] https://xrpl.org/docs/concepts/transactions/source-and-destination-tags
- [XLM-LUMENS] https://developers.stellar.org/docs/learn/fundamentals/lumens
- [XLM-FEE] https://developers.stellar.org/docs/learn/fundamentals/fees-resource-limits-metering
- [XLM-OPS] https://developers.stellar.org/docs/learn/fundamentals/transactions/list-of-operations
- [XLM-TX] https://developers.stellar.org/docs/learn/fundamentals/transactions/operations-and-transactions
- [VAULTA-RES] https://support.token.im/hc/en-us/articles/360006466354 (third party; official Antelope docs unreachable)
- [VAULTA-ACCT] https://token.im/hc/en/articles/4577033800601 ; https://unicove.com/en/vaulta/proposals/vp-0002
- [VAULTA] https://support.token.im/hc/en-us/articles/47178735073689-EOS-Network-Has-Upgraded-to-Vaulta
- [EOS-MEMO] https://github.com/EOSIO/eos/wiki/Tutorial-Exchange-Deposit-Withdraw/3ac107e7f36976af4bcc1807f08a0fb3c38a9a4a ; https://github.com/eosnetworkfoundation/evm-bridge-frontend/releases?page=2
- [SOL-FEE] https://solana.com/docs/core/fees
- [SOL-ACCT] https://solana.com/docs/core/accounts
- [SOL-ATA] https://solana.com/docs/tokens/basics/create-token-account
- [TON-FEE] https://docs.ton.org/develop/smart-contracts/fees
- [TON-ADDR] https://docs.ton.org/foundations/addresses/formats
- [TON-GRAM] https://ton.org/en ; https://ton.org/media ; https://t.me/s/toncoin
- [ALGO-PARAM] https://dev.algorand.co/concepts/protocol/protocol-parameters/
- [ATOM] https://docs.cosmos.network/hub/latest/hub-tutorials/gaiad ; https://docs.cosmos.network/sdk/latest/learn/concepts/transactions
- [DOT-ED] https://wiki.polkadot.com/general/chain-state-values/ ; https://support.polkadot.network/support/solutions/articles/65000190561-polkadot-asset-hub-migration-what-you-must-know
- [NEAR-STORAGE] https://docs.near.org/protocol/storage/storage-staking
- [ADA-EX] https://developers.cardano.org/docs/developers/exchange-integrations/
- [ADA-NT] https://developers.cardano.org/docs/developers/curriculum/native-tokens/overview/
- [XYM] https://docs.symbol.dev/concepts/transfer-transaction.html
- [FIL] https://docs.filecoin.io/smart-contracts/filecoin-evm-runtime/address-types ; https://docs.filecoin.io/basics/assets/transfer-fil
- [SUI] https://docs.sui.io/concepts/tokenomics/gas-in-sui
- [VET] https://docs.vechain.org/introduction-to-vechain/dual-token-economic-model
- [DOGE] https://github.com/dogecoin/dogecoin/blob/master/doc/fee-recommendation.md
- [BCH] https://reference.cash/protocol/blockchain/encoding/cashaddr
- [ZEC-317] https://zips.z.cash/zip-0317
- [ZEC-UA] https://zcash.readthedocs.io/en/master/rtd_pages/addresses.html ; https://z.cash/upgrade/nu5/
- [BSC-USDT] https://bscscan.com/token/0x55d398326f99059fF775485246999027B3197955
- [BSC-USDC] https://bscscan.com/token/0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d
- [POL] https://polygon.technology/blog/matic-to-pol-migration-is-now-live-everything-you-need-to-know
- [ARB] https://docs.arbitrum.io/how-arbitrum-works/gas-fees
- [OP] https://docs.optimism.io/stack/transactions/fees
- [BASE] https://docs.base.org/base-chain/network-information/network-fees
- [ZKSYNC] https://docs.zksync.io/zksync-protocol/era-vm/transactions/fee-model
- [SONIC-OPERA] https://www.soniclabs.com/blog/sonics-successful-network-migration-what-this-means-for-fantom-opera/
- [FTM-USDC] https://www.coingecko.com/en/coins/multichain-bridged-usdc-fantom ; https://www.fxstreet.com/amp/cryptocurrencies/news/fantom-price-crashes-by-12-in-a-day-as-multichain-users-dump-110-million-worth-of-assets-202307062313
- [CRO-USDT] https://www.coindesk.com/price/cbusdt ; https://coingecko.com/en/coins/cronos-bridged-usdt-cronos/usd
- [GNOSIS] https://docs.gnosischain.com/about/tokens/xdai
- [XLAYER] https://web3.okx.com/xlayer/docs/developer/build-on-xlayer/network-information
- [KAIA] https://docs.kaia.io/learn/transaction-fees/
- [OKTC] https://www.theblock.co/post/367090/okx-okb-token-burn ; https://support.token.im/hc/en-us/articles/53764789236377-OKTChain-Decommission-Notice
- [HECO] https://ellipal.com/blogs/news/important-heco-network-to-shut-down-protect-your-assets-now (secondary)
- [MATCH] https://revoke.cash/token-approval-checker/matchain (secondary)
- [AB] https://www.htx.com/tokens/ab (secondary)
