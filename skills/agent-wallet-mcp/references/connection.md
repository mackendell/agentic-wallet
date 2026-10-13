# Connection and Response Transport

Connect to the wallet service and make business calls through the current host's MCP client.

## Connection Responsibilities

| State | Action |
| --- | --- |
| Host exposes the required tools | Use discovered tools directly; do not initialize again |
| Host does not expose tools | Refresh once. If a wallet task still cannot use them, have the [MCP skill](../SKILL.md) inspect, reuse, or prepare the service. A read-only inspection does not change configuration |
| Service is already running | Reuse the original instance; do not launch a second instance or switch to stdio. Register the verified original endpoint only if the host lacks a connection |
| Session has definitely expired | Rebuild the host session and tool definitions; do not replay an unknown write |

<a id="endpoint-discovery"></a>
## Endpoint Discovery

Use a user-selected or host-configured wallet connection. Do not require the connection name, process name, or returned `ServerName` to equal a fixed string. If several candidate connections cannot be distinguished, ask the user to choose; do not filter with a service-name allowlist. The HTTP path is `/mcp` and the currently running instance determines the port. Do not treat a fixed port, startup default, historical record, or sample port as evidence of a current listener. A backend URL returned by status is not the MCP address.

1. If the host already exposes the required tools, use the current connection directly; do not create another session just to find a port. A configured stdio connection does not need an HTTP port.
2. If a local HTTP endpoint must be located and the user did not supply an address, search wallet service processes read-only and verify the PID and executable path. The process may be named `service` or a release asset such as `service-darwin-*`, `service-linux-*`, or `service-windows-amd64.exe`. Names identify candidates only, not identity. Prefer host process-inspection facilities. On macOS/Linux, `ps -axo pid=,comm=` can list PIDs and executable names; verify each candidate PID separately. Do not print complete startup arguments, environment variables, or potentially credential-bearing configuration.
3. Query TCP LISTEN sockets for the verified service PID. On macOS/Linux with lsof, use `lsof -nP -a -p <PID> -iTCP -sTCP:LISTEN`, replacing `<PID>` with the actual PID. On other systems use an equivalent read-only tool that shows process ownership. The port must belong to this process's current listener; do not infer it from startup arguments or scan arbitrary ports.
4. Only when the target instance and HTTP listener are unambiguous, form a candidate endpoint from its reachable address, port, and `/mcp`. A same-host process listening on a wildcard address can use the loopback address of the matching address family. Enclose IPv6 URL hosts in brackets. A listener does not prove protocol readiness; the host MCP client must still initialize and discover tools as below. Do not send a password to an unverified service.
5. If process ownership is unclear, instances/listeners cannot be distinguished, no listener is found, permission is insufficient, or no process-inspection tool exists, stop automatic discovery and request the full MCP endpoint (scheme, host, port, path). Explain verified partial information if useful, but do not pick the first candidate or guess a default port. A remote host, container port mapping, or reverse proxy cannot be inferred from a local process; ask for its reachable endpoint.

Use an endpoint already specified by the user without asking again. Finding an endpoint is not the same as connecting the host. Return the verified original connection to the MCP skill for host registration and verification; do not download a replacement for an HTTP instance. The script does not create managed records for external instances. Before registering an endpoint with the current host's native CLI, check its HTTP capability in help, back up current configuration, and check for name conflicts. After a write, read back the target and unrelated entries. Codex uses `mcp add --url`; Hermes uses `config set mcp_servers.NAME.url`; OpenClaw uses `mcp add --url` and `--no-probe`. If the actual CLI lacks the capability, stop instead of editing configuration directly or upgrading the host. A newly managed installation uses stdio and needs no port discovery. Do not try historical ports in turn after a connection fails or replace a remote instance with a new local install.

## HTTP Client Protocol

Use these protocol details to understand or diagnose the host connection. They do not need to be run before every business operation. The host MCP client performs the following steps:

1. POST to the endpoint with Content-Type `application/json` and Accept `application/json, text/event-stream`.
2. Send initialize and negotiate the protocol. This credential-free example uses `clientInfo` as a client label, not a wallet identity.

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"agent-wallet-client","version":"1.0.0"}}}
```

3. Keep the response header `Mcp-Session-Id` in the current client session. Send it and the negotiated `MCP-Protocol-Version` on later calls. Do not use a sample session ID or store a real one in summaries or files.
4. Send an initialized notification without a request ID:

```json
{"jsonrpc":"2.0","method":"notifications/initialized"}
```

5. Discover tools:

```json
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
```

If `result.nextCursor` exists, pass it as the next `params.cursor` until the list is complete. A generic tool-call envelope follows. Its business `name` and `arguments` must come from this package's API section and real inputs; this example queries only status:

```json
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"status","arguments":{}}}
```

Hosts usually ask for tool arguments only; do not put the full JSON-RPC envelope into business parameters. The client handles response types, notifications, and request-ID matching. Do not assume every HTTP response is business JSON.

## Checks After Reconnecting

After upgrading or switching services, refresh the current host's tool definitions and check the parameters and response structures needed for this request. Pause affected operations if definitions differ, preserving completed steps and unknown write states.

For local macOS wallet calls, follow [macOS Keychain authorization](macos-keychain.md). A working MCP connection does not prove persistent Keychain ACL access; perform one authorization preflight again after a binary identity change.

## Service Preparation and Version Identification

Call status when this client first uses the service or after rebuilding a session, and query again if the user explicitly requests a refresh. Connecting a wallet requires no login password. If the user asks only to register or log in, explain this and ask which wallet operation they want to complete.

Record actual `ServerVersion`, `ServerName`, `environmentName`, `transportType`, source, and observation time. `ServerName` is display data, not authentication. Status, successful initialization, and a session ID prove only their respective connection steps, not that a wallet is ONLINE. Service environment is not wallet network.

See [Memory](../../agent-wallet/references/memory.md) for recovery and persistence in a new session. Remembered endpoints and versions are discovery clues; reverify them when current evidence is needed.

## Business Response Parsing

See [API result rules](../../agent-wallet/references/runtime-api.md#result-rules) for the common classifications and required fields. HTTP status 200 is not success by itself. Check JSON-RPC errors, then `result.isError`, then parse business data. Prefer `result.structuredContent`; otherwise parse JSON text in `result.content`. If both exist and conflict, the result is unknown.

Tool annotations are neither execution authorization nor evidence of business success. Even read-only tools may conservatively carry `destructiveHint`. Do not bypass host-required approval.

## Deployment Argument Reference

Choose assets using [Service releases](releases.md) and start the selected file by its actual path. After connecting, verify the running version and required tool schemas while preserving task progress and unknown write states.

These arguments describe an existing HTTP deployment, not automatic first installation. The first install registers a stdio startup command through `scripts/mcp.py`:

```text
service -t http -p <deployment-port> -e test
```

`service` stands for the executable path supplied by the deployer. Replace the port placeholder; never execute it literally. `-t` accepts stdio/http, default stdio. `-p` applies only in HTTP mode; the service's default port is not endpoint-discovery evidence. `-e` accepts test/prod, default prod. Stdio starts a separate process and cannot connect to an existing HTTP instance. Service test/prod and wallet Testnet/Mainnet are not equivalent.

`-v` prints the binary version. `-clean-data` / `-r` reinitializes and clears data; never use it for connection repair, updates, or migration. Confirm the running version through status on the target connection; `-v` on a disk binary does not prove that binary is running.
