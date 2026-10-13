# Agent Wallet installation

The archive contains `skills/agent-wallet` and `skills/agent-wallet-mcp` at its root, alongside this file and `MANIFEST.json`. Install both complete directories into the same supported host. Do not install only SKILL.md, copy macOS metadata, or use an old dist directory.

For a ZIP shared through GitLab, use the actual file download link and the publisher's SHA-256. Verify the ZIP checksum, MANIFEST.json file hashes and both VERSION files before installing. Reject path traversal and symlinks, extract into a temporary directory, and back up existing paired skills outside the host's skill search directory. Copy both complete directories, including VERSION, without changing other skills. Verify installed files against the archive and restore both old directories if replacement fails. Start a new conversation to load updated instructions. If the request is only to install or upgrade skills, do not modify MCP programs, service configuration or wallet data. Private downloads require existing authorized access; stop on an authentication or login-page response.

Wallet features require the CoinsDo wallet MCP service. When helping install the skills, the assistant should explain this dependency and offer a choice:

1. **Install and connect MCP**: Check and reuse an existing connection. If no previous installation exists, establish whether this is for real use or testing, then download, install and configure MCP v1.0.8. Guide the user through loading the connection in the current host.
2. **Skip MCP for now**: Complete only the skill installation and explain that wallet features need an MCP connection before they can be used. Do not download MCP or change service configuration.

Wait for the user's choice before preparing MCP. If the user already requested both installations, continue without asking again. Running a skills CLI installation command alone installs only the skills; it does not offer this interaction or install MCP.

Use an existing Codex, Hermes or OpenClaw host with Python 3.9+ on a supported macOS/Linux architecture, or reuse a verified existing connection. Installing the skill alone does not download MCP. When a wallet task needs a missing MCP connection, the skill prepares the service automatically, pinned to the packaged contract baseline v1.0.8. An empty verification record does not block first installation. The current host must still load and verify tools and status before wallet work continues. Existing connections can still be used within their verified limits.

Start with “Connect my wallet”, “Show my assets”, “Give me a receiving address”, “Prepare a transfer”, or “Check the previous transfer”. By default, consumer mainnet transfers stop at preparation because the required fee, preflight and trusted-confirmation evidence is incomplete. Keep these requirements in place even if they prevent an unverified setup from proceeding. Managed services support checking for updates; replacing their binaries is not supported.

See [wallet instructions](skills/agent-wallet/SKILL.md), [transaction policy](skills/agent-wallet/references/transaction-policy.md), and [connection instructions](skills/agent-wallet-mcp/SKILL.md). Closing a chat does not revoke wallet permissions. No real wallet, host or App end-to-end qualification is claimed by this archive.
