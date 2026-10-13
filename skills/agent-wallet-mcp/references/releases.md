# Service Releases and Deployment Reference

Use this file to inspect releases or select an MCP binary. For the complete inspection, approval, and upgrade procedure, see [Updates](updates.md). When a wallet task lacks a connection, [agent-wallet-mcp](../SKILL.md) prepares the service through its managed first-install flow. Stay read-only if the user requests inspection only or explicitly forbids changes. Upgrading an existing service, switching environments, and migrating data are outside automatic preparation.

## Current Release Baseline

The latest stable release verified on 2026-10-12 is `v1.0.8`, published at 2026-10-09T08:29:57Z, tag commit `675fe4a3a1f66bc1d218d18c8c074129289f9923`. The default branch `master` matches the tag; the recent release list shows no newer prerelease. Official documentation adds approval_transaction and custom_address_path, corrects the normal-transfer nonce location, marks NFT comment required, and identifies tokenId as the Token ID.

This review compares pinned v1.0.7 and v1.0.8 README files, CHANGELOG, and Release metadata. No binary was downloaded or executed and no v1.0.8 live tools/list was captured. Asset digests come from official metadata and do not represent a completed download check. Historical static-type findings apply only to their original versions.

| Version | CHANGELOG entry |
| --- | --- |
| v1.0.8 | Add transaction approval and custom address path switch; revise parameter descriptions and README |
| v1.0.7 | Log storage; normal-transfer nonce; dataDir; renamed cleanup flag; TRON fix |
| v1.0.6 | Remove claim_key_shard; improve list result structure; validate tool inputs |
| v1.0.5 | Fix Linux secure-storage path |
| v1.0.4 | Remove user_login; rename service; fix cross-compilation |
| v1.0.0 | First stable release |

## Contract Evidence and Verification Scope

The packaged API parameter baseline covers the release's 26 tools. Core fields for wallet-ref, wallet, service-status, address-counts and balance have historical outputSchema evidence. Extended transaction fields and other records were compiled from upstream documentation; this Release's real business responses have not completed integration verification.

Upstream ambiguities remain: the NFT currencyId-to-projectId mapping is undefined; token/NFT additions do not specify object versus array response structures; balance.addressStr type descriptions conflict with examples; transaction field non-null declarations do not fully match conditional applicability. The execution contract retains the corresponding checks and stop conditions; editing documentation does not resolve these ambiguities.

Fee preflight, trusted confirmation, unique recovery of unknown operations, receipt evidence and revocation lack complete business verification. Offline documentation and simulated trace checks do not prove enforcement by the host or funds execution service.

## Platforms and Assets

Identify the operating system and CPU architecture where the service actually runs. For a remote server or container, use the target environment's architecture rather than the current computer's. `x86_64` maps to amd64; `aarch64` and Apple Silicon map to arm64. Stop if no asset matches. Do not assume a native Windows ARM64 or other platform build exists.

| Platform | Architecture | Release asset |
| --- | --- | --- |
| macOS | Intel x86_64 | service-darwin-amd64 |
| macOS | Apple Silicon arm64 | service-darwin-arm64 |
| Linux | x86_64 | service-linux-amd64 |
| Linux | aarch64/arm64 | service-linux-arm64 |
| Windows | x86_64 | service-windows-amd64.exe |

The download URL template is `https://github.com/CoinsDo/coinsdo-wallet-mcp/releases/download/v1.0.8/<asset-name>`. Replace the asset name with the matching entry above. This is the service repository, not the skill repository; do not use this URL as the skills CLI install source.

GitHub Release metadata provides these SHA-256 values. Hash the downloaded asset and compare exactly; stop on a mismatch. These hashes apply only to these assets at this version.

| Asset | SHA-256 |
| --- | --- |
| service-darwin-amd64 | 257e69546563a7ed7b63a1ea3aad04df94a9ba5b9af66f644bbb1cea8fa43dac |
| service-darwin-arm64 | e82ce35d0a5a9b8de3edaa0092a055434d143f8d4dd2267111bd4f19831e5569 |
| service-linux-amd64 | c7df2333f20175ca18793a4a514900ff59a7c3929c4d122ed8452f1ad27b9092 |
| service-linux-arm64 | ff3b06ae9826da77c0d5f01f96246e8d997028664e19d6d796071808f08d1a46 |
| service-windows-amd64.exe | f62f0c9e27d1eae8b4a5fe7187a92516501622d7ef2e03624bb197bd68ce0319 |

A matching hash proves consistency with the release metadata, not that the service started or the wallet is ready.

## macOS Keychain Note

The v1.0.6 Darwin arm64 asset inspected on 2026-09-30 is ad-hoc signed (Identifier=`a.out`, no TeamIdentifier) and contains `99designs/keyring v1.2.1` and `go-keychain`. CHANGELOG does not claim a Keychain ACL or code-signing fix. The v1.0.8 signature was not inspected; do not carry forward the old signature finding. Unattended and ordinary-user end-to-end Keychain verification has not passed; existing-item ACL migration and authorization persistence after binary replacement remain unverified. Follow [Keychain authorization](macos-keychain.md) on local macOS, and block further wallet calls while repeated prompting remains unresolved.

## Data Paths and Startup Arguments

The README lists default paths: macOS `/Users/<username>/Library/Application Support/coinsdo-wallet-mcp/` and Linux `/home/<username>/.config/coinsdo-wallet-mcp/`. Use these only as discovery clues, not as evidence of the actual runtime user, database, or secure storage. Windows paths and cross-version migration behavior are undocumented. Do not copy an old directory to a new one and call it a verified migration.

`-v` prints the binary version; `-e` selects test/prod (default prod); `-t` selects stdio/http (default stdio); `-p` controls only the HTTP port (default 8080). `-clean-data` deletes the database, logs, and secure password; never use it for connection repair, updates, or migration. The same prohibition applies to legacy `-r`. Defaults do not establish an existing instance's configuration; preserve its verified arguments during an update.

## Connecting After Deployment

1. Preserve existing instances, data, and host configuration. Before an upgrade, identify the target instance, backup, and recovery method. The documentation does not guarantee database migration or downgrade compatibility; do not overwrite a running binary or delete data directly.
2. Use the MCP skill script for automatic first installation; if the purpose is unknown, ask whether this is for real use or testing. For other manual deployments, retain the verified environment, transport, and paths. On macOS/Linux, set only the needed execute permission. If the OS blocks execution, report the actual issue; do not automatically remove system security attributes.
3. See [Connection](connection.md) for startup arguments and protocol. `service` is a command placeholder; replace it with the selected asset's actual path. The deployment chooses the HTTP port; discover existing instances by PID and listening port rather than assuming a fixed port. The host launches stdio as a separate process; it cannot connect to an existing HTTP instance through stdio.
4. After an authorized connection, have the host perform initialize, tool discovery, and status; do not register or log in. Verify the tools and parameters required for this task. If a tool is missing, pause only work that depends on it. Do not automatically replace an old instance or replay a prior write with an unknown result.

## Sources

- [v1.0.8 Release](https://github.com/CoinsDo/coinsdo-wallet-mcp/releases/tag/v1.0.8)
- [Release metadata](https://api.github.com/repos/CoinsDo/coinsdo-wallet-mcp/releases/tags/v1.0.8)
- [Current documentation snapshot](https://github.com/CoinsDo/coinsdo-wallet-mcp/blob/675fe4a3a1f66bc1d218d18c8c074129289f9923/README.md)

These sources support maintenance and download traceability. The instructions needed for business calls are included in this package.
