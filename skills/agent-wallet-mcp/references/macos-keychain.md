# macOS Keychain Authorization

Use this policy only for a local macOS wallet service that accesses the system Keychain. It does not apply to remote/container connections, a status-only check or non-macOS hosts. Handle OS authorization once before wallet calls so the user does not have to enter the login password on every call.

## One-Time Authorization Preflight

1. Confirm that this is the intended local macOS instance. Locate an existing HTTP instance through [endpoint discovery](connection.md#endpoint-discovery); use a verified installation record for managed stdio. Do not identify it by ServerName alone.
2. Before the first wallet operation in this session that may touch secure storage, explain once that macOS may show a Keychain access dialog. The password belongs only in the macOS dialog, never in chat. If the dialog offers Always Allow and the user intends to keep using this verified service, that option requests persistent authorization; Allow authorizes only the current access.
3. Never create a wallet write merely to trigger authorization. If the task already needs a read-only wallet lookup, use that as the preflight. Before a write, use the already-required read-only object lookup or fresh `get_wallet` check so authorization is resolved before the write call begins.
4. After the first successful call, keep only a non-sensitive current-session observation that this verified instance/binary completed one Keychain authorization interaction. Do not repeat the password explanation on every call. This is not proof of a permanent ACL and must not survive a binary/identity replacement without rechecking.
5. If the user chose Always Allow and the next wallet call still prompts again, or explicitly reports that every call prompts, stop issuing further wallet business calls. Report that macOS Keychain authorization did not persist; do not diagnose by repeatedly triggering the prompt. Resume only after a service signing/ACL fix or a supported system-level remediation.
6. A changed binary, path, signing identity, or service instance invalidates the prior observation; perform one preflight again.

## Prohibited Workarounds

- Never ask for a macOS login/Keychain password or place it in chat, command arguments, or configuration.
- Never run `security -A`, grant every application access, or disable platform security automatically.
- Never delete/recreate the `com.coinsdo.wallet.secure` item automatically, export its secret, or create a plaintext fallback. ACL migration requires explicit upstream/platform evidence.

## User-Facing Wording

Before the first possible prompt:

> macOS may show a wallet Keychain access dialog. Enter the password only in the system dialog, not in chat. If you verified this wallet service and the dialog offers “Always Allow,” you can choose it so later calls should not ask every time.

If prompts continue:

> Keychain authorization did not persist. I am stopping wallet calls so each step does not trigger another password prompt. The service needs a macOS Keychain access-control or signing fix before continuing.
