# User Tasks and Execution Workflows

For transaction approval, use [approve or reject](#approve-transaction); for custom address paths, use the [local switch](#custom-address-path). Both are writes. A request to inspect a transaction or add an address does not authorize them.

Choose the function that serves the user's goal. Do not run through the entire tool list. The [entry point](../SKILL.md) contains the common rules for authorization, connection, object discovery, ONLINE checks and results; [Runtime API](runtime-api.md) defines parameters and response objects. Read only the current function and the sections it needs.

Discovery steps can be reused across functions, but the request must not expand. For example, initiating a transfer may require wallet, asset, and address lookups; failure to find one does not authorize joining a wallet or adding an asset/address. Skip steps already satisfied below. If a write result is unknown, stop under the entry-point rules; never repeat a write merely to obtain its ID again.

When speaking to users, use wallet names, assets, networks and complete receiving addresses. Keep IDs in context unless tracking or disambiguation requires showing them. On failure, explain what completed and what remains unconfirmed, then give a next step supported by the evidence.

<a id="guidance"></a>
## Guidance Throughout Every Workflow

Use [user interaction](user-interaction.md) for questions/results and complete [transaction-specific review](transaction-policy.md#confirmation) before sending funds.

Explain the current result and any action needed from the user at each relevant stage:

- **Start:** Acknowledge the user's goal. If the wallet goal is unclear, follow [user interaction](user-interaction.md) to suggest two or three suitable options, explain their results and help the user choose. Once clear, query and answer directly for a simple request; for a longer task, say briefly what you will do. Do not recite tools or checklists.
- **Missing information:** Look up what you can first, then ask for remaining items using wallet names, assets, chains, or complete receiving addresses. Explain why a choice is needed and do not ask again for an existing answer. Explain unfamiliar terms by their purpose, not by demanding internal IDs.
- **In progress:** Continue when possible. Only when waiting for external approval, wallet creation, or connection recovery, state what completed, why work paused, and who must do what. Resume the same target after the user responds; do not restart discovery without cause.
- **Failure or unknown:** State precisely which step failed and which result cannot be confirmed. Perform independent read-only checks within authorization. Ask the user only for a step supported by current evidence. If no reliable recovery is known, say the service operator must investigate; do not invent “try again,” create again, or resend advice.
- **Complete:** Deliver the requested address, balance, status, or other result. End naturally when the task is complete and no action is needed. Suggestions do not become automatic tool calls; do not pitch transfers or installation after every query.

Use the following guidance with names, networks, counts, addresses and statuses obtained from this task's queries or user confirmation:

| Workflow | Guidance for missing information or a pause | Delivering the result |
| --- | --- | --- |
| Check connection | Refresh once. If a wallet task still lacks a connection, let the MCP skill prepare it; ask only if purpose or target is unclear. Give one step if the host requires manual reconnect | For an independent read-only check, say whether it connects. After preparation, resume the original task without asking the user to repeat it |
| Get started / connect wallet | Explain how to get an invitation code from the App. After joining, ask the creator to complete creation only when that is the actual wait | Say the wallet is connected when ready. If still unready, identify completed steps without guessing a cause from non-ONLINE alone |
| Wallet overview | For multiple candidates, ask “Which wallet?” with names and networks. An empty successful list means no wallet was found; a view-only request does not join automatically | Show wallets and understandable statuses within the requested scope. A list failure means unknown, not “no wallets” |
| Asset discovery | Ask “Which chain is this asset on?” using actual candidates. A support-list request need not select one | Name supported assets, networks, and necessary contracts. No match is scoped to the query; it does not mean the user owns no assets |
| Addresses and balances | Use known wallet, address, and asset candidates to fill gaps. Keep successes if some queries fail | Deliver full addresses or balances with asset and network; identify unknown items without making the user parse fields |
| Receive | Look for an existing address first; ask whether to add one only after confirming none. If pending approval, explain who must approve before another lookup | Give full address, asset, and chain/network; remind the sender to use the same network. Do not claim funds were received |
| Add token/NFT project | Clarify whether “add an asset” means a receiving address or a missing catalog token. Ask for the project's full published contract and chain when needed, not a `protocolId` | Explain that the asset entered the searchable catalog, which does not imply a balance or receiving address. Do not append address creation |
| Add wallet address | Ask only for missing wallet/chain. For pending approval, identify the wallet approver instead of calling it a generic failure | Give actual added, existing, failed, and pending results. A receiving goal also requires finding the address; state if it is still unknown |
| Transfer / send NFT | Ask once for missing amount, recipient address, or network. Describe a required memo as the recipient's tag/note. Never advise resending an unknown submission | Give the known submission, transaction identifier, and progress. Do not say funds arrived without evidence. Distinguish “not sent” from “cannot confirm whether sent” |
| Transaction progress | Resolve “the previous one” from context when possible. For several transactions, let the user choose by asset, amount, and time instead of searching for an ID | Pending approval means waiting for approval; approval does not mean receipt. A lookup failure preserves the original submission fact and does not resubmit |
| Leave room | Check the target first. If creation is unclear, ask “Has the creator completed wallet creation in the App?” | On success, say this membership was exited. For a created wallet, explain that only an uncreated room can be left; do not propose shard deletion or reset |

See [Updates](../../agent-wallet-mcp/references/updates.md) and [Memory](memory.md) for service updates and cross-session recovery steps.

| Function | Section |
| --- | --- |
| Get started | [First use and recovery](#get-started) |
| Receive | [Find and deliver a receiving address](#receive) |
| Service preparation | [Check connection and version](#account-access) |
| Wallet onboarding | [Join, wait for creation, and check status](#wallet-onboarding) |
| Leave room | [Leave before creation](#leave-room) |
| Wallet overview | [List and detail](#wallet-overview) |
| Asset discovery | [Chains, protocols, assets, and NFT catalog](#asset-discovery) |
| Addresses and balances | [Find addresses and balances](#address-and-balance) |
| Add catalog asset | [Add token or NFT project](#add-asset) |
| Add wallet address | [Add and verify result](#add-wallet-address) |
| Initiate transaction | [Normal transfer and NFT send](#initiate-transaction) |
| Transaction history | [List and detail](#transaction-history) |

<a id="account-access"></a>
## Service Preparation

**Trigger and input:** Inspect the service or prepare a connection for another function. No login password is required.

1. Discover the target connection and tools using [Connection](../../agent-wallet-mcp/references/connection.md). Call [status](runtime-api.md#status) on first use or after a rebuild; a changed service name is no reason to refuse. On missing tools or connection failure, refresh once. If a wallet task still cannot proceed, enter [agent-wallet-mcp](../../agent-wallet-mcp/SKILL.md) without a refresh loop. Stay read-only and do not run `ensure` when the user asks only to inspect or explain, or forbids configuration writes.
2. For an independent check, report the connection result and actual version/environment if requested; mark a missing version unknown. For a business prerequisite, resume the task.
3. If the user asks only to register or log in, explain that connecting a wallet requires no login and ask which wallet operation they want to complete.
4. End an independent check here. When this is a prerequisite, continue the original function. Save authorized non-sensitive facts under [Memory](memory.md); never claim a failed save succeeded.

When service preparation is needed, say “I'll prepare the wallet connection, then continue.” Pass the original goal, completed steps, and unknown writes to the MCP skill. It identifies the host, reuses an existing installation, asks the purpose for a first install, and runs its script. The user need not understand ports or PIDs or separately request “install.” Clarify the target only among multiple instances. Do not replace a failed remote connection with a local install. If the host requires manual reconnect, give one exact step and retain the pause point; do not report the connection ready yet. Resume only unexecuted business steps after the host rediscovers needed tools and status passes. Never resubmit an unknown write.

<a id="get-started"></a>
## Get Started

Enter only when the user explicitly wants to start using or connect a wallet; an ordinary greeting does not trigger this. If the user supplies an invitation code and asks to join, go directly to [Wallet onboarding](#wallet-onboarding). If an explicit paused record exists, resume at its step without forcing a fresh full-list query.

1. Check the connection, call `get_wallets`, and validate the result. A failed query is not “no wallets,” and data attached to an error cannot form candidates.
2. If a successful query returns an empty list, give brief guidance: “Start creating an MPC wallet in the [CoinWallet](https://coinwallet.coinsdo.com/en) App and find the invitation code. Send me the code and the name you want me to display in the wallet, such as ‘My Assistant’.” If the App is not installed, point to that official page. Then wait for complete information before joining. Do not repeat or persist the code.
3. If wallets exist, show choices by name and mainnet/testnet; use a single unambiguous choice directly. Query the selected wallet's detail. If it succeeds and is ONLINE, say “Wallet state is verified. You can query balances/receiving addresses or prepare transfers; submission remains subject to transaction policy.” Do not join again.
4. If the wallet is not ONLINE, check the verified join and creation progress. Ask the user to finish creation in the App only when joining is confirmed and creation is pending. Once the user explicitly reports creation complete, query the same wallet's detail again. If the wallet is still not ready or the query fails, explain the result and preserve the current join progress.

This guidance solves only first use; it does not automatically check balances, add an address, or transfer. App guidance follows the product path. Reachability of the page does not prove every App version has the same interface. Use the user's actual information if their interface differs; do not invent button names.

<a id="wallet-onboarding"></a>
## Wallet Onboarding

**Trigger and input:** “Join a wallet” and “connect to a wallet” enter the join-and-wait-for-creation flow. For “connect my wallet” without a target, start with [Get started](#get-started). First-time joining requires an invitation code and a display name, mapped to `invitationCode` and `custodianName`. Reuse the same `walletId` when progress is clear. Ask only for missing information; users need not understand the internal custody workflow.

After joining, wait for the creator to finish creating the wallet in the App, then query that wallet's actual status. The returned `walletId` identifies the wallet; it does not mean creation is complete or the wallet is ready.

**Steps:**
1. Ensure the connection and required tools are ready; do not repeat verified preparation that remains valid.
2. Before joining, explain the assistant's participant role, verified permission and approval boundaries, and anything still unknown. Explain that closing the chat does not revoke wallet permissions. Obtain the invitation code and name, call [join_mpc_wallet](runtime-api.md#join-mpc-wallet) once, and verify and retain `walletId` and `walletName`. Skip only with clear evidence that joining this target already succeeded; an ID or lookup record alone does not prove that. Clarify unclear progress instead of replaying a join whose result is unknown.
3. After success say, “I joined <wallet name>. Please have the creator finish creation in the CoinWallet App and tell me when it is done; I will then check the wallet status.” Pause without polling when creation completion is unknown. If the user only says “continue,” ask whether creation is complete unless that fact is already known. Cancellation or join-only scope stops later work.
4. After the user confirms creation, call [get_wallet](runtime-api.md#get-wallet) with the same walletId and verify ID/status. ONLINE means the wallet state is ready for queries or transfer preparation, still subject to transaction policy. For another valid status, report it and only evidenced limitations. On lookup failure, say readiness cannot yet be confirmed and preserve the current join progress.

**Completion and pause:** Report completed and remaining stages. If a valid `walletName` changes for the same ID, report the name change. The user confirms creation completion; the subsequent status query determines wallet readiness. While creation completion is unknown, pause and ask the user to report when it is done, then resume the status query.

**Atomic boundary:** Join-only ends after a successful join. Full onboarding includes join, waiting for user-reported creation completion, and the following status lookup only. It does not add assets/addresses or send. Stop dependent steps on failure/unknown; do not compensate automatically.

<a id="leave-room"></a>
## Leave Room

**Trigger and input:** “Leave the wallet” or “exit the room.” The target `walletId` must be clear and the wallet must not yet be created. A created wallet cannot be left through this action.

**Steps:**
1. Ensure connection and required tools are ready. Identify the target through [Wallet overview](#wallet-overview), clarifying multiple candidates.
2. Call [get_wallet](runtime-api.md#get-wallet), verify returned ID and required fields. On failure, missing fields, or mismatched ID, say “I cannot confirm whether this wallet has been created, so I have not left the room,” then stop. Not found does not prove uncreated.
3. If ONLINE or if creation completion is otherwise evidenced (for example, an explicit user statement), say “This wallet has been created. Leaving is supported only before creation.” Do not call leave or substitute shard deletion, deactivation, or rejoining.
4. Non-ONLINE does not prove uncreated. Ask about current creation status if missing. Once the user confirms it has not been created and there is no contrary evidence, call [leave_mpc_wallet](runtime-api.md#leave-mpc-wallet) once without extra confirmation. Stop on conflicting information; do not probe by trying the call.
5. Verify business success and returned ID. On success say “I have left the room.” Do not retry failure or unknown. `ErrCodeTee6052` / absence of an uncreated wallet means there is no uncreated room available to leave; that error alone does not prove the wallet was created.

**Completion and boundary:** The prerequisite query is not a status lock, so report the actual leave result. ONLINE is not required. “Call leave only” does not waive the uncreated-wallet check.

<a id="wallet-overview"></a>
## Wallet Overview

**Trigger and input:** List wallets, find one, or inspect detail/status. The list has no business arguments. Detail requires `walletId` from explicit user input or a list result.

**Steps:**
1. Ensure connection and required tools are ready. Call [get_wallets](runtime-api.md#get-wallets) for a list request; return the records needed without forcing detail queries for each.
2. If the user requests a particular wallet but its ID is unknown, identify it from the list under their criteria. Clarify same-name or multiple candidates by name, mainnet/testnet, and available description first; request an ID only if still indistinguishable. Report no match; do not pick the first or join automatically.
3. Call [get_wallet](runtime-api.md#get-wallet) for detail/current status, verify the ID, and return actual information. A known ID does not require listing first.

If the list errors or is truncated, do not extract wallet names, networks, counts, or candidate IDs from the error fragment. With an explicit ID or prior successful record, detail for that ID can be independently queried. On success, separately report “This wallet's detail was verified” and “The list still failed; total wallet count is unknown.” When correcting an earlier answer, retract unsupported names, networks, and counts. A successful detail does not mean the list recovered.

**Completion and boundary:** End an independent query here. As a prerequisite, pass the verified ID/network back to the original workflow rather than ending it early. A detail query does not authorize wallet creation. Returned status is not a creation-complete enum. Sending and adding an address still require a fresh pre-call check.

<a id="asset-discovery"></a>
## Discover Supported Assets

**Trigger and input:** Query supported chains, protocols, currencies, or NFT projects, or locate an object for another function. `netType` must be clear from the user or selected wallet. An independent catalog query need not select a wallet.

**Steps:**
1. Ensure connection and tools are ready; identify category and network. Clarify only if intent does not distinguish normal currency from NFT project.
2. Call only the matching category tool; do not walk the whole catalog:

| Category | Query path | Identity and notes |
| --- | --- | --- |
| Chain | [get_chains](runtime-api.md#get-chains) / [search_chains](runtime-api.md#search-chains) | A chain record's `currencyId` serves as `chainId`; search if a chain name is known, otherwise list |
| Protocol | [get_protocols](runtime-api.md#get-protocols) / [search_protocols](runtime-api.md#search-protocols) | `protocolId` is distinct; for adding an NFT project verify `nftState=1` |
| Normal currency | [search_currencies](runtime-api.md#search-currencies); use [get_currencies](runtime-api.md#get-currencies) and local filtering without a valid required name | `currencyId` is the asset ID; do not pass `nftState` to `get_currencies` |
| NFT project | [search_nft_projects](runtime-api.md#search-nft-projects); use [get_nft_projects](runtime-api.md#get-nft-projects) and local filtering without a valid required project name | A project record's `currencyId` does not automatically map to send `projectId` |

3. Verify candidate network, chain, name, and contract/protocol. Disambiguate only when the next business step needs one unique object. For a list-only request, show all candidates in scope. A record missing identity cannot feed a write that depends on it.

**Completion and boundary:** Return supported catalog entries or a verified target ID to the original function. A supported catalog is not wallet holdings or balance. No match does not trigger adding. An NFT project record does not prove ownership of a `tokenId`. An independent query adds no wallet ONLINE check.

<a id="address-and-balance"></a>
## Query Addresses and Balances

**Trigger and input:** Find an address; check one balance, an asset balance in a wallet, or balances for all wallet addresses. Determine whether only addresses or also balances are requested. Do not expand “address only” into balances.

**Steps:**
1. Ensure connection and tools are ready. Select a path from known inputs:

| Known target | Atomic step |
| --- | --- |
| Explicit address ID and balance request | Call [get_address_balance](runtime-api.md#get-address-balance) directly with lowercase `addressId` |
| Full address, known `currencyId`, and balance request | Call [query_address_balance](runtime-api.md#query-address-balance) directly with `addressStr`/`currencyId` |
| Wallet address or an asset balance in a wallet | Identify wallet; use [Asset discovery](#asset-discovery) only if needed to limit asset/chain; call [get_addresses](runtime-api.md#get-addresses) with `walletId` and needed filters |
| Partial address or account name | Call [search_addresses](runtime-api.md#search-addresses) with API minimum search length and optional known currency; complete insufficient search input rather than treating a fragment as a full address |

2. For the two direct-balance paths, do not look up wallet ownership, join state, or ONLINE; do not force `get_wallet`, `get_addresses`, or `search_addresses`. After success go directly to step 5, skipping steps 3 and 4 without repeating the balance lookup. Query catalog and disambiguate only when an asset name is given and is non-unique. Lack of wallet association or non-ONLINE does not block a balance query.
3. When finding addresses by list/search, verify scope, asset, and full address. Disambiguate if one target must be selected. If all matching addresses are requested, no per-address choice is required. Page through the full set under the entry-point rule and state incomplete coverage.
4. For addresses only, display records and end. If balances are also requested, call `get_address_balance` for each verified address in scope. Use the lowercase `addressId` request parameter. Do not merge assets merely because address strings match. Report no match without adding an address.
5. Verify balance network and asset against the request; keep the amount as a string. Record actual query time; if source-data update time is unknown, state that without guaranteeing live chain data. Mark each failed item failed/unknown while retaining other successes. Independent read-only items may continue, but identify unknowns in the final answer. Do not sum across assets into a unitless “total balance” or estimate fiat value or maximum sendable amount.

**Completion and boundary:** Report asset, network, address, balance, and coverage. A response `addressId=0` cannot feed a later send. Missing optional extension fields do not invalidate the core balance; handle type conflicts under the API. The NFT project catalog is not an NFT holdings tool. Do not call a project list a balance or invent an NFT holdings query.

If the whole address list fails format validation, neither addresses nor balances can be inferred from its error fragment. Without independent, valid balance-query parameters, stop dependent queries. Do not repeat the same error without a reason to expect a fix. Report independently successful earlier balance results only in their original scope; they cannot become a full balance for a failed list.

Externally show “asset · chain/network · balance,” identifying ownership for multiple addresses. For “What assets do I have?”, use actual address and balance queries rather than a catalog of supported currencies. If no NFT holdings endpoint exists, say NFT holdings were not queried. For a failed balance, say “I could not retrieve this balance yet,” not 0.

<a id="receive"></a>
## Receive

**Trigger:** “I want to receive USDT” or “Give me a receiving address.” Deliver a full address for the relevant wallet, asset, and network without requiring internal IDs from the user.

1. Use [Wallet overview](#wallet-overview) and [Asset discovery](#asset-discovery) to identify wallet, mainnet/testnet, and receiving chain. Reuse a clear existing choice. If USDT has candidates on multiple chains, name the real chains and ask “Which network will the sender use?” Do not default to a chain or mainnet.
2. Query addresses for that wallet and asset. For a valid match, deliver full address, asset, and chain/network. If several addresses require a choice, show distinguishable address candidates without demanding `addressId`. An existing-address query does not require ONLINE.
3. Only after a successful query covering the target scope confirms no address, ask “This wallet has no <asset> receiving address on <chain>. Would you like me to add one?” On agreement, enter [Add wallet address](#add-wallet-address), then query and deliver the address. A failed or incomplete paged query is not proof of absence. Stop on explicit refusal.
4. If the original request already said “Add a USDT receiving address,” enter the add flow directly without asking again; ask only for missing wallet/network.

If approval is pending, say “The address request was submitted and awaits approval, so I cannot provide a new address yet. Tell me once approval is complete and I'll look it up,” without adding again. When an address is usable, remind the sender to choose the same chain/network. Do not claim funds arrived or automatically transfer or add a catalog asset.

<a id="add-asset"></a>
## Add Asset to Catalog

**Trigger and input:** An explicit request to add a token or NFT project. Requires network, chain/protocol, and complete `flag`. “Add an asset address to my wallet” goes to [Add wallet address](#add-wallet-address). If “add an asset” could mean either catalog token or wallet address, ask “Do you want a receiving address for this asset, or to add a token that you cannot currently find?” Do not require the user to understand “catalog,” and do not perform both writes.

**Steps:**
1. Ensure connection and tools, complete network, protocol, and full contract address/token ID, and obtain `protocolId` through [protocol discovery](#asset-discovery). Reuse a verified protocol record. Disambiguate candidates; `chainId`/`currencyId` are not substitutes.
2. For an NFT project, verify protocol `nftState=1`. Stop if unsupported or unknown; do not switch to adding a normal currency.
3. Once parameters and target are clear, call [add_currency](runtime-api.md#add-currency) or [add_nft_project](runtime-api.md#add-nft-project) once with only `protocolId`/`flag`. Wallet ONLINE is not a prerequisite.
4. Interpret the response under the current `outputSchema`. Verify selected protocol network, chain, and `flag`; record actual `currencyId`. If single-object versus array wrapping is unclear and cannot be recognized, report unknown without another write.

**Completion and boundary:** Report only the catalog-add result. If the user also explicitly requested a wallet address, confirm that the returned asset can be used for that operation, then hand off to its function; do not append it automatically. If the response was lost, finding a same-name catalog asset does not justify resending or claiming this add succeeded.

<a id="add-wallet-address"></a>
## Add Wallet Address

**Trigger and input:** Add an asset address to a specified wallet. `walletId` and `currencyId` are required. Discover unclear names/networks; do not default the wallet or asset.

**Steps:**
1. Ensure connection and tools. Identify wallet/network through [Wallet overview](#wallet-overview) and a same-network currency through [Asset discovery](#asset-discovery). Reuse verified records. Report a missing currency instead of adding it to the catalog automatically.
2. Perform the entry-point ONLINE check for the target wallet; stop if it fails or is non-ONLINE. Once ready, call [add_address](runtime-api.md#add-address) once with `walletId`/`currencyId`.
3. Check `success`/`existed`/`failed`/`pending` counts separately. Explain “added,” “already existed,” “failed,” and “pending approval,” showing counts when useful instead of raw field names. Counts alone cannot supply an `addressId` or address string. Pending is not completed creation. Any `failed > 0` is a failure or partial failure; do not resend.
4. `success` or `existed` establishes an address exists. When a real address must be delivered, query [get_addresses](runtime-api.md#get-addresses) with the same `walletId`/`currencyId` and verify records. “Add a receiving address,” agreement to add during Receive, and “add and give me the address” all require delivering the actual address; counts alone are insufficient. If no match appears, query fails, or only some pages return, say “The add result returned, but the address is not yet known,” and do not call `add_address` again.

**Completion and pause:** For an add-only request, report actual counts. For a request needing an address, return a verified record as well. If only pending, report approval pending and pause. When the user reports approval complete, resume at address lookup without adding again or polling in the background. Report completed and pending portions separately for mixed counts; finding one address does not mean all approvals completed.

<a id="initiate-transaction"></a>
## Initiate Transaction

**Trigger and input:** “Initiate a transaction,” “transfer,” or “send an NFT.” Determine normal currency versus NFT first, asking only if unclear. A normal transfer needs sending asset/address, full recipient address, and an `amount` string. An NFT additionally needs verified `projectId` and `tokenId`, plus a `tokenAmount` string for ERC1155.

**Steps:**
1. Ensure connection and tools. Resolve necessary objects through [Wallet overview](#wallet-overview), [Asset discovery](#asset-discovery), and [Address discovery](#address-and-balance). Read only needed scope; locating the sending address does not require an extra balance query. Verify wallet ownership of the address and consistency of network and asset/NFT-project chain. With only an `addressId` and no ownership evidence, select the wallet and page through its address records to verify.
2. Obtain the full user-specified recipient address and this send's parameters. Do not derive an amount from query results or examples. Pause for a missing target, no match, or ambiguous candidates; do not join a wallet or add an asset/address automatically.
3. Prepare parameters by category:

| Branch | Parameter rules and stop conditions |
| --- | --- |
| Normal transfer | [send_transaction](runtime-api.md#send-transaction): `addressId`/`toAddress`/`amount`/`comment` are required; ask the user for a missing comment without inventing one. Keep `amount` as a decimal string, never float. Omit an absent memo. Omit evmNonce for normal sends; replacement requires the API's association evidence, fee evidence, and confirmation. Ask for a memo only when the recipient is known to require one. An XRP/TRON memo, if provided, is a numeric string; do not impose that constraint on other chains |
| NFT send | [send_nft_transaction](runtime-api.md#send-nft-transaction): verify the association between `projectId` and the target project and use the user's Token ID. Do not rename `currencyId` or use an amount as `tokenId`. For verified ERC1155, obtain the user's `tokenAmount` string without defaulting to 1. Omit it for other protocols. `comment` is required; ask if missing without inventing one |

4. Prepare a review under [transaction policy](transaction-policy.md): complete source/recipient addresses, wallet, asset, chain/mainnet or testnet, amount, supplied notes and fee evidence; state not submitted. Without necessary mainnet preflight, fee or trusted-confirmation evidence, stop at preparation or hand off to an actually verified trusted interface.
5. Obtain transaction-specific approval, reusing equivalent trusted host/App confirmation. Changed bound inputs or a new session invalidate approval and require fresh review. Cancellation before confirmation sends nothing; read-only queries do not acquire this gate.
6. Only after approval and all gates pass, obtain a fresh ONLINE result for the same wallet, then call the chosen send once. Approval does not replace ownership, network, precision or recipient checks. Cancellation after calling does not prove revocation.
7. Classify under the API. On success first say “The transfer was submitted.” For `PENDING_APPROVAL` add “It is waiting for approval; receipt cannot yet be confirmed.” Present the actual `bundleId` as the “transaction ID”; show a returned nonempty `txHash` when useful, without conflating them. Interpret other states only within known meaning; do not claim broadcast or receipt. Stop on failure/unknown. On timeout say “I cannot yet confirm whether this transfer was submitted, and I did not send it again.” If an actual `bundleId` exists, query it under authorization; without a reliable link, explain that the original operation needs further investigation instead of asking the user to guess an ID. Non-ONLINE can lead to a later new readiness check only before submission.

**Completion and boundary:** If gates are unmet, deliver prepared content and missing conditions without claiming a send. After an actual submission report only its verified acceptance/state, not approval or receipt. Do not automatically poll, accelerate, cancel, compensate, or resend. If the user also requested a lookup, use the verified `bundleId` in [Transaction history](#transaction-history). A balance does not prove fees are sufficient or the full balance sendable. An NFT catalog does not prove ownership of all tokens. An atomic send request still requires ownership, parameter meaning, and ONLINE verification.

If NFT semantics are unclear, tell the user “The wallet service cannot yet identify this NFT send precisely, so I did not submit it. The service operator needs to confirm it before I can continue.” Provide field details for troubleshooting only when needed; do not make a normal user solve the field mapping.

<a id="approve-transaction"></a>
## Approve or reject a transaction

When the user explicitly requests approval, locate the target through [transaction queries](#transaction-history) and show understandable transaction contents. Let the user select among candidates; never approve the first entry or the entire list by default. Obtain the approve/reject decision and approval comment. Apply the [approval policy](transaction-policy.md#approval) to authority, contents, state, and applicable funding conditions, then call [approval_transaction](runtime-api.md#approval-transaction) once. Report the actual resulting state. If other approvals remain, explain the wait without claiming receipt. Validate a rejection response too; report uncertainty without retrying.

<a id="custom-address-path"></a>
## Set the custom address path switch

When the user explicitly requests enabling or disabling it, verify the target MCP instance and explain that this local HD setting affects the index of subsequently added addresses when enabled. Once the instance and choice are clear, call [custom_address_path](runtime-api.md#custom-address-path) once without requiring walletId or ONLINE. Ask only for an ambiguous instance or direction. A request to inspect current state stays read-only; without a query interface, report that it cannot be queried and do not write to "read" it.

Verify that the returned enable matches the choice before reporting enabled or disabled. Do not add addresses automatically or promise that disabling restores a historical index. On an unknown result, stop without retrying or reversing the switch. Pause later additions that depend on its state until the service operator verifies it.

<a id="transaction-history"></a>
## Transaction History

**Trigger and input:** View wallet transaction records or one transaction's progress. Detail requires a clear `bundleId`. The list requires only `walletId`; filter by address, type, status, or pages only as requested.

If the user says “the previous one” and context has an exact transaction ID, use it. Without an ID, query records for the target wallet and let the user choose by asset, amount, and time. Do not require the user to find a `bundleId` themselves. This selection identifies a record to view; it does not prove association with an unknown submission.

**Steps:**
1. Ensure connection and tools. With an explicit `bundleId`, call [get_transaction](runtime-api.md#get-transaction) directly, then present the result under step 4. Do not additionally demand wallet, address, status, or ONLINE. If `bundleId` is missing, first locate the target transaction.
2. For a list, identify the wallet. Verify address ownership only if filtering by address. Call [get_transactions](runtime-api.md#get-transactions) with valid user-specified `txType`/`status` and pagination. Page through all matches if requested. Omit unspecified optional filters; do not invent `ALL`.
3. Query detail when the user selects one list item or context contains an exact `bundleId`. If several records remain indistinguishable, show candidates and clarify. Similar amount, address, and time alone do not establish that a record is an unknown submission. An empty list does not authorize resending.
4. Show actual status, asset, amount or applicable NFT fields, and nonempty `txHash`. Do not invent NFT fields for normal transfers. `APPROVED` is not on-chain receipt; `PENDING_APPROVAL` means only awaiting approval. State when missing fields prevent a conclusion.

**Completion and boundary:** Return the requested list/detail and its coverage, without automatic polling. A DApp transaction-record query does not authorize contract calls; `accelerates` or associated IDs do not authorize acceleration, retry, or cancellation. Detail is a query, not a reason to submit a pending transfer again.
