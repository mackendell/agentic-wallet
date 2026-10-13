# Service Preparation Script Interface

The script at `scripts/mcp.py` requires Python 3.9+ and has no pip dependencies. Automatic management supports amd64 and arm64 on macOS/Linux. Under macOS Rosetta, detect the actual hardware. Configure only the current Codex, Hermes or OpenClaw host; do not install or upgrade it.

## Commands

| Command | Input and behavior |
| --- | --- |
| inspect | Requires `--host codex|hermes|openclaw`; read-only inspection of CLI capabilities, connections, managed records, and known old data/processes; no download, startup, or configuration write |
| ensure | Same host argument; a first install requires `--env prod|test`, which can be omitted when a record exists; downloads and registers if needed, without upgrading an existing installation |
| run | Startup entry point invoked by the host; verifies the managed binary and executes fixed stdio arguments; stdout carries no management JSON; failure JSON goes to stderr |
| verify | Starts a brief managed stdio probe, checking status by default; repeat `--require-tool get_wallets` and similar logical tool names as needed; does not execute business tools |

All commands accept an absolute `--root` for the managed directory. Defaults: macOS `~/Library/Application Support/agent-wallet-mcp`; Linux `$XDG_DATA_HOME/agent-wallet-mcp` or `~/.local/share/agent-wallet-mcp`. Normal use does not require the user to choose a path. The registered startup command contains absolute Python, script, and root paths. Moving the skill or uninstalling Python makes an old startup command unusable; diagnose and verify the original target before installing anything else.

`inspect` and `ensure` accept `--server` to name an existing connection. If the specified connection is absent, do not silently switch to a new install. OpenClaw accepts the current `--profile`; otherwise use `OPENCLAW_PROFILE`. Follow `OPENCLAW_CONFIG_PATH`/`OPENCLAW_STATE_DIR` for configuration paths and `CODEX_HOME`/`HERMES_HOME` for the other hosts. Never execute commands with placeholder values.

## Results

Management commands write one JSON object to stdout, except for normal help output. Exit code 0 means this command's inspection or isolated verification completed; 2 means a purpose, target choice, wait, or host load is required; 1 means failure. Exit code 0 does not mean the wallet or host business tools are ready.

Fields include `state`, `stage`, `completed`, `installation`, `connection`, `protocol`, `host_tools`, `error`, and `next_step`. A verified installation record also provides version/environment; a completed configuration backup provides backup. `host_tools` returns `not_checked`. Continue with tool discovery and status through the current host, then report the connection ready after both pass.

| state | Agent's next step |
| --- | --- |
| not_installed | If purpose is unknown, ask real use or testing, then run ensure |
| installed / interrupted_install | Continue ensure using the recorded version/environment |
| existing_connection | Use the original connection; do not reinstall, replace, migrate, or force restart |
| pending_host_load | Try a refresh in the current host; give an exact step if a human must reconnect |
| protocol_verified | Isolated probe passed; verify tools/status in the current host |
| needs_action / failed | Diagnose using `error.code`, `completed`, and `next_step`; do not replay an unknown write |

## Compatibility Gate

First installation uses the stable version specified by `contract_baseline.mcp_version` in `compatibility/manifest.json`. Fetch metadata through the official tag endpoint and verify the platform asset, official URL and SHA-256; do not select another version from latest. A missing or invalid manifest or baseline returns `COMPATIBILITY_UNKNOWN`. An interrupted installation whose version differs from the current baseline returns `UNSUPPORTED_RELEASE`; preserve its record and binary without silently switching versions.

`verified_installations` does not select the installation version; an empty list permits first installation. Check host adaptation through current CLI capabilities and configuration readback. Reuse existing installations/connections without upgrading. After installation, complete current-session tool discovery, status and business prerequisites.

Managed installations support read-only update inspection. Preserve the managed binary and integrity record. See [Updates](updates.md#managed-installation-boundary).

## Installation and Concurrency

The GitHub tag endpoint retrieves the stable Release matching the packaged baseline. Before downloading, `pending.json` records the tag, platform asset, official URL, and SHA-256. A download retry uses that same selection and must not silently switch versions. After verification, atomically move the binary and write `installation.json`. After an interruption, verify any binary already on disk before completing the record. Stop when records and files disagree; do not interpret an unknown state as an old version or overwrite it. Downloads accept only the official CoinsDo Release and GitHub release-asset redirects; arbitrary download-source overrides are unsupported.

The install lock prevents concurrent downloads/registration. The run lock prevents starting the same managed instance twice and is released by the OS when the service exits; do not infer liveness from a PID file. A second host/session trying to start that managed binary receives `BUSY`. Use the original owning session, or request an authorized handoff after it is no longer in use. Independent stdio clients cannot attach to its existing stream. Do not kill other sessions or copy wallet data to bypass the lock. The script does not manage the lifecycle of unknown external instances.

The binary, environment, startup arguments, and hash are management records, not user memory or wallet secrets. The service still manages the real wallet database and secure storage; the script never copies, clears, or migrates them. If old data exists without a verified managed record, stop the first installation. Detection covers the packaged default paths and identifiable wallet processes, but cannot prove that arbitrary custom directories are absent. The agent must first verify a user-specified or existing host target.

Configuration backups are stored under `backups` in the managed directory with mode 0600. They may contain existing host secrets; do not print or commit their content. A CLI error may occur after a write; report `unknown_after_write`. If readback disagrees, preserve the backup and partial result; do not overwrite the whole configuration as an automatic rollback.

## Host Commands

- Codex: read connections with `codex mcp list --json` and register a startup command with `mcp add NAME -- COMMAND...`. Back up `config.toml` before adding. [Official documentation](https://developers.openai.com/learn/docs-mcp)
- Hermes: read configuration with `config get --json` and write the target connection with `config set mcp_servers.NAME '<JSON>'`. Use the native configuration interface for YAML and have the host load it after readback confirms it. Preserve host tool approval and omit bypass/accept-hooks arguments.
- OpenClaw: use `mcp show --json` to read full connection objects and `mcp add --command ... --arg=... --no-probe` to register. Check that the runtime CLI supports these arguments. Do not convert existing HTTP connections. CLI reload does not prove that the Gateway/agent session refreshed. [Official commands and limitations](https://docs.openclaw.ai/cli/mcp/registry)

Verify the behavior of the actual host version in its execution environment. If a format is unknown or a required command capability is missing, stop with a failure; do not edit configuration directly to bypass the CLI. Add only the current target. Do not set approval, automatic tool approval or other permission options.
