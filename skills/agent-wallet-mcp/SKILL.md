---
name: agent-wallet-mcp
description: Inspect and prepare the Agent Wallet MCP service. Reuse an existing connection; when necessary, download, install, configure the current host, and start on demand. Enter from a wallet task when the connection is unavailable, or when the user explicitly requests service inspection, installation, or updates. An ordinary greeting does not trigger this skill. Do not automatically upgrade an existing service or switch environments.
---

# Agent Wallet MCP

For skill version questions, read this directory's [VERSION](VERSION) without starting or connecting to MCP. If it is missing or unreadable, report “installed version unknown”; never substitute the MCP program version. For the paired skills, read both VERSION files separately and report any mismatch.

Prepare the wallet service so the user does not need to choose download files, ports or startup commands. [agent-wallet](../agent-wallet/SKILL.md) handles business operations. Install both skills together. If the companion directory is missing, report an incomplete installation; do not substitute an arbitrary script from another directory.

## When to Enter

- If a wallet task already has usable tools, return directly to that task without running installation checks.
- If tools are missing or the connection fails, the wallet skill refreshes once, then hands off the original goal, target connection, required tools, and completed or unknown writes. Perform necessary service preparation without requiring a separate “install” request. Respect explicit read-only or no-configuration limits and host approvals; do not bypass them by changing methods.
- If the user asks only for service status or version, inspect only. For update checks or upgrades, read the [update workflow](references/updates.md). An upgrade requires approval of a concrete plan; `ensure` does not perform upgrades.

## Preparation Flow

1. Identify the current host and profile. Prefer a user-selected or already configured connection. Operate only on the current host; do not configure every host after scanning. Check Python and host CLI availability yourself. See [Script interface](references/script.md) for supported hosts and commands.
2. Call the script's `inspect` command using this skill's absolute path, for example `python3 <this-directory>/scripts/mcp.py inspect --host codex`. When the host and existing connection are known, pass the real `--host` and `--server`; do not infer identity from a service name.
3. Reuse a usable original connection. Do not convert HTTP/remote connections to stdio or install a local replacement for a failed remote connection. If an old binary, running process, or wallet data exists but the connection is not yet located, investigate the original instance using [Connection](references/connection.md#endpoint-discovery). Ask the user only if multiple targets remain indistinguishable. If the original installation cannot be established, pause the new install; do not move data, kill processes, or delete directories.
4. If no original installation exists and the intended use is unknown, ask only “Is this for real use or for testing?” Map real use to `--env prod` and testing to `--env test`. Reuse an answer or verified installation record from this session; do not ask twice. Service environment does not determine wallet `netType`.
5. Run `ensure`. It pins an official release, verifies the download, installs it, and registers a startup command. Repeated calls reuse existing results. A new install is host-managed stdio, without a port, login startup item, or separate daemon. `run` is the host's startup entry point, not a normal shell background job.
6. Try the host's current-session refresh or reconnect facility. If the user must act, give one step for that host, explain that service preparation is complete but reconnection is needed, and preserve the original task's pause point. CLI configuration readback and an isolated probe do not prove that the current session loaded the tools. OpenClaw CLI reload affects only its own process; do not call that a Gateway-session refresh.
7. After the host rediscovers tools, call status. First check tool and host errors; then verify version, environment, and transport against the installation or original-instance evidence. Verify the schema of tools needed for this task. Only then say “The connection is ready” and resume the wallet task. The business flow separately checks whether the wallet is ONLINE.

A local macOS instance also follows [Keychain authorization](references/macos-keychain.md) before wallet work may touch secure storage. This applies even when tools are already usable: explain the authorization prompt once, and if it still repeats after Always Allow, stop triggering wallet calls instead of treating repeated password entry as normal.

Read the first-install version from `contract_baseline.mcp_version` in `compatibility/manifest.json`. Verify official release metadata and the binary's SHA-256, then have the current host load and verify tools and status before reporting the connection ready. Reuse usable existing connections. Managed services support update inspection only; follow the [managed boundary](references/updates.md#managed-installation-boundary).

## Interpreting Script Results

Check exit code and JSON first. Do not treat objects attached to errors as success. `completed` describes only stages actually finished. `pending_host_load` means configuration is prepared but the host still needs to load it. `protocol_verified` means only an isolated probe passed. `existing_connection` requires verification through the original host connection; it does not prove installation or runtime readiness.

For troubleshooting a new installation, `verify` may perform an isolated protocol probe limited to initialize, tools/list, and status. It briefly starts and closes a managed stdio instance. If an instance is already running, do not start a second one; verify through the original host. Do not use registration, joining, address creation, or transfers as health checks.

On failure, explain what completed, where the process stopped and what the available evidence supports doing next. Do not expose raw configuration, service logs or tokens. If a script error may have followed a write, run `inspect` or read back host configuration before retrying. Investigate external connection failures, permission limits, incompatible versions or unknown data locations, and pause installation steps that depend on resolving them.

## Business Boundary

Service preparation covers only necessary download, first installation, registration, and on-demand startup. Do not automatically upgrade, switch environments, reset, or migrate data. Never run `-clean-data` / `-r`. Do not edit AGENTS.md/SOUL.md or automatically install Python, a host, or dependencies. Keep existing state storage in its original location; the managed directory holds only the program and management records.

Restoring the service connection does not resolve an unknown wallet write or justify replaying a join, add, or send. If the original request was only to check balance, continue only that request. After cancellation, do not resume unexecuted business steps.

See [Service releases](references/releases.md) for release evidence, [Script interface](references/script.md) for arguments, exit codes, and host adapters, and [Updates](references/updates.md) for the required separate upgrade procedure.
