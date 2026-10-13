# How each Host installs, loads and runs the skill

Research for [#4](https://github.com/mackendell/agentic-wallet/issues/4) (map [#1](https://github.com/mackendell/agentic-wallet/issues/1)). Sources read 2026-10-13, primary only: official docs and the official GitHub repos. Any claim not confirmed in a primary source is marked **UNVERIFIED**.

Source notes:
- **Codex:** `developers.openai.com/codex/*` now 308-redirects to `learn.chatgpt.com/docs/*`, so the citations use the redirect targets.
- **Hermes:** the docs were read as Markdown in `NousResearch/hermes-agent` under `website/docs/`. The page URLs below are built from the site config (`https://hermes-agent.nousresearch.com/docs/` + file path) and were not opened in a browser.

## Comparison

| | Claude Code | Codex CLI | Hermes Agent | OpenClaw |
|---|---|---|---|---|
| **Install from GitHub, and location** | Plugin marketplace: `claude plugin install <p> --marketplace owner/repo`, or copy the skill dir by hand. Skills live in `~/.claude/skills/<name>/` or `.claude/skills/`; plugins in `~/.claude/plugins/cache/...`. Hand-copied skills are picked up mid-session. | `$skill-installer` (wraps `install-skill-from-github.py --repo o/r --path p`) or copy by hand. Skills live in `~/.agents/skills`, `.agents/skills`, or the deprecated `~/.codex/skills`, which is where the installer writes. No `codex skills` subcommand. | `hermes skills install owner/repo/path` (copies SKILL.md plus the files it references), or copy by hand. Skills live in `~/.hermes/skills/<category>/<skill>/`. | `openclaw skills install git:owner/repo[@ref]` (or `--global`). Skills go to `<workspace>/skills` (default workspace `~/.openclaw/workspace`) or `~/.openclaw/skills`. A watcher rescans about every minute. |
| **Register MCP; can a skill do it itself?** | `claude mcp add ...` writes `~/.claude.json`, or use `.mcp.json`. A plugin can bundle `.mcp.json`, and its servers start when the plugin is enabled. A script running `claude mcp add` is not a documented pattern. `.mcp.json` edits need a restart. | `codex mcp add` writes `[mcp_servers.<n>]` in `~/.codex/config.toml`. **Built in:** a skill's `agents/openai.yaml` can declare an MCP dependency. Codex then offers to install it and reloads MCP in-session. | `hermes mcp add`, or `mcp_servers:` in `~/.hermes/config.yaml`. In-session config edits auto-reload, and `/reload-mcp` also works. Agent self-registration is not documented, but plausible through the terminal tool. | `openclaw mcp add/set` writes `mcp.servers` in `~/.openclaw/openclaw.json`. The CLI refuses while the Gateway is running. Changes apply at the next turn without a restart. Agent self-registration is **UNVERIFIED**. |
| **Skill text loading** | On demand. Name and description sit in the listing (cap 1,536 chars per skill; the whole listing is about 1% of context). SKILL.md loads on invoke and references on read. | On demand. Name, description and path at start (catalog ≤ 2% of context, or 8,000 chars; description ≤ 1,024 chars). SKILL.md is read when the skill is used. Reference loading is **UNVERIFIED** (presumably on read). | On demand. A name/description index sits in the system prompt. `skill_view(name)` loads SKILL.md and `skill_view(name, path)` loads one reference. The linter warns above about 24k chars. | On demand. An `<available_skills>` list of name, description and path costs about 97 chars per skill plus the field lengths. The agent reads SKILL.md itself. |
| **Cross-session memory** | CLAUDE.md files; auto memory (`~/.claude/projects/<p>/memory/MEMORY.md`, first 200 lines or 25 KB loaded); `--continue`/`--resume`; JSONL transcripts. | AGENTS.md (32 KiB cap); optional Memories (`~/.codex/memories/`, off by default); `codex resume` and `codex exec resume`; rollout JSONL files. | MEMORY.md (2,200 chars) and USER.md (1,375 chars) via the `memory` tool; `session_search` over `~/.hermes/state.db`; memory plugins (Honcho and others); agent-written skills. | MEMORY.md, `memory/YYYY-MM-DD.md`, AGENTS.md, SOUL.md and USER.md in the workspace; `memory_search` and `memory_get`; sessions in SQLite. |
| **Headless run, model, OpenRouter, metrics** | `claude -p --model X --output-format json`. Returns `num_turns`, `usage`, `modelUsage`, `duration_ms`, `total_cost_usd`. No tool-call count field: count `tool_use` blocks in `stream-json`. Non-Claude models via OpenRouter are **not supported** by Anthropic. | `codex exec -m X --json`. JSONL has `turn.completed.usage`; count tool calls from `item.completed` events. No wall-time field. Providers must use `wire_api = "responses"`, and OpenRouter use is **UNVERIFIED**. | `hermes chat --oneshot -q ... -m X --provider openrouter --format stream-json`. The result event gives tokens and `duration_ms`. `state.db` holds `tool_call_count`, tokens and start/end times. OpenRouter is first-class. | `openclaw agent exec "..." --model openrouter/<p>/<m> --json`. Returns `usage`, `costUsd`, `toolSummary.calls` and `assistantTurns`. No wall-time field in exec mode (`openclaw agent --json` has `meta.durationMs`). OpenRouter is first-class. |

## Claude Code (Anthropic)

### Install and location
- **Adding and installing plugins:**
  - Add a marketplace with `/plugin marketplace add owner/repo` in a session or `claude plugin marketplace add owner/repo` in the shell; `#ref` pins a branch or tag.
  - `claude plugin install <p>@<m> [--scope user|project|local]` installs a plugin.
  - `claude plugin install <p> --marketplace owner/repo` adds the marketplace and installs in one step (v2.1.292+).
  - Shell installs load next start or after `/reload-plugins`.
  - https://code.claude.com/docs/en/plugins/install
- **Marketplace repo layout:** the repo needs `.claude-plugin/marketplace.json` at its root. https://code.claude.com/docs/en/plugin-marketplaces
- **Skill locations:**
  - `~/.claude/skills/<name>/SKILL.md` (personal), `.claude/skills/<name>/SKILL.md` (project), `<plugin>/skills/<name>/SKILL.md` (plugin, invoked as `/plugin:skill`).
  - Directories are watched, so changes apply within the current session. A newly created top-level skills dir needs `/reload-skills`.
  - https://code.claude.com/docs/en/skills
- **Plugin storage:** under `~/.claude/plugins/` — `cache/<marketplace>/<plugin>/<version>/` (`${CLAUDE_PLUGIN_ROOT}`) and `data/<plugin-id>/` (`${CLAUDE_PLUGIN_DATA}`). https://code.claude.com/docs/en/plugins/loading

### MCP
- **Commands:** `claude mcp add --transport http <name> <url>`, `claude mcp add [--env K=V] [--scope local|project|user] <name> -- <cmd> [args]`, and `claude mcp add-json`. https://code.claude.com/docs/en/mcp
- **Where config is stored:**
  - Local and user scope go to `~/.claude.json`; project scope goes to `.mcp.json`, which needs approval.
  - Precedence: local > project > user > plugin > claude.ai connectors.
  - https://code.claude.com/docs/en/mcp
- **Plugin-bundled servers:** "Plugins define MCP servers in `.mcp.json` at the plugin root or inline in `plugin.json`... When you enable a plugin, Claude Code starts its MCP servers automatically." Under `-p`, plugin servers take effect next session. https://code.claude.com/docs/en/mcp
- **Restart rules:**
  - `.mcp.json` edits need a restart: "Claude Code reads `.mcp.json` at session start. Exit and restart the session after editing the file." https://code.claude.com/docs/en/mcp-quickstart
  - Whether `claude mcp add` mid-session needs a restart is **UNVERIFIED** in the docs.
- **Headless:** headless runs can pass `--mcp-config <file|json>`. https://code.claude.com/docs/en/cli-reference
- **Skill or script self-registration:** not documented. **UNVERIFIED** as a supported pattern; the quickstart says to run `claude mcp add` in a terminal. https://code.claude.com/docs/en/mcp-quickstart

### Skill loading
- **Progressive loading:** "skill descriptions are loaded into context... but full skill content only loads when invoked". Supporting files are read on demand. Once invoked, a skill stays in context for later turns. https://code.claude.com/docs/en/skills
- **Description cap:** `description` + `when_to_use` is truncated at 1,536 chars per skill (`skillListingMaxDescChars`). https://code.claude.com/docs/en/skills
- **Listing budget:** the listing "scales at 1% of the model's context window". On overflow, descriptions of the least-invoked skills are dropped and the names kept. https://code.claude.com/docs/en/skills
- **After compaction:** re-attached skills share a 25,000-token budget, with the first 5,000 tokens kept per skill. https://code.claude.com/docs/en/skills
- **`--bare`:** skips the skill listing. https://code.claude.com/docs/en/headless

### Memory
- **CLAUDE.md:** loaded from `~/.claude/CLAUDE.md`, `./CLAUDE.md` and `CLAUDE.local.md` at launch. https://code.claude.com/docs/en/memory
- **Auto memory:** stored in `~/.claude/projects/<project>/memory/`. "The first 200 lines of `MEMORY.md`, or the first 25KB... are loaded at the start of every conversation." https://code.claude.com/docs/en/memory
- **Transcripts and resume:**
  - Transcripts are `~/.claude/projects/<project>/<session-id>.jsonl`; the format is "internal... and changes between versions".
  - `--continue` and `--resume` resume a session; `--no-session-persistence` turns off saving for a `-p` run.
  - https://code.claude.com/docs/en/sessions

### Headless and metrics
- **Flags:** `claude -p "..." --model <id> --output-format text|json|stream-json` (stream-json needs `--verbose`), `--max-turns N` (print mode only; errors at the limit), `--max-budget-usd`. https://code.claude.com/docs/en/cli-reference
- **Result fields** (`SDKResultMessage`): `duration_ms`, `duration_api_ms`, `num_turns`, `usage`, `modelUsage`, `total_cost_usd` (a client-side estimate), `session_id`. https://code.claude.com/docs/en/agent-sdk/typescript and https://code.claude.com/docs/en/headless
  - That CLI `--output-format json` emits exactly this type is **UNVERIFIED**. It is inferred from the docs saying `-p` is the Agent SDK via the CLI.
- **Tool-call count:** there is no documented field. Counting `tool_use` blocks in `stream-json` assistant messages is an inference (**UNVERIFIED**). Subagent events carry `parent_tool_use_id`. https://code.claude.com/docs/en/headless
- **OpenRouter:**
  - Anthropic "doesn't support routing Claude Code to non-Claude models through any gateway". https://code.claude.com/docs/en/llm-gateway
  - OpenRouter's own (non-Anthropic) guide uses `ANTHROPIC_BASE_URL=https://openrouter.ai/api` and `ANTHROPIC_AUTH_TOKEN`, and says it is "only guaranteed to work with the Anthropic first-party provider". https://openrouter.ai/docs/cookbook/coding-agents/claude-code-integration.md
  - Tool search is off by default with a non-first-party `ANTHROPIC_BASE_URL`. https://code.claude.com/docs/en/mcp

## Codex CLI (OpenAI)

### Install and location
- **Skill roots:** `$CWD/.agents/skills` and parents up to the repo root, `~/.agents/skills`, `/etc/codex/skills`, plus bundled system skills. https://learn.chatgpt.com/docs/build-skills
- **Deprecated root:** `$CODEX_HOME/skills` (`~/.codex/skills`) is still loaded as a "deprecated user skills location… kept for backward compatibility". https://github.com/openai/codex/blob/main/codex-rs/ext/skills/src/host_roots.rs
- **`$skill-installer`:**
  - Runs `install-skill-from-github.py --repo <o>/<r> --path <p>` (or `--url .../tree/<ref>/<path>`, plus `--ref` and `--method auto|download|git`).
  - Installs to `$CODEX_HOME/skills/<name>`, aborts if the folder exists, and uses `GITHUB_TOKEN`/`GH_TOKEN` for private repos.
  - https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/skill-installer/SKILL.md
- **No `codex skills` subcommand:** distribution goes through `codex plugin add` and `codex plugin marketplace add`. https://github.com/openai/codex/blob/main/codex-rs/cli/src/main.rs and https://learn.chatgpt.com/docs/cli/reference
- **Pickup:** "Codex detects newly installed skills automatically; if one doesn't appear, restart Codex." https://learn.chatgpt.com/docs/build-skills

### MCP
- **CLI commands:** `codex mcp add <name> [--env K=V] -- <cmd>` or `--url <u> [--bearer-token-env-var VAR]`, plus `list`, `get`, `login`, `logout` and `remove`. https://learn.chatgpt.com/docs/extend/mcp?surface=cli and https://learn.chatgpt.com/docs/cli/reference
- **config.toml:**
  - Servers are `[mcp_servers.<name>]` in `~/.codex/config.toml`, or project `.codex/config.toml` for trusted projects only.
  - Keys: `command`, `args`, `env`, `url`, `startup_timeout_sec` (default 10), `tool_timeout_sec` (default 60), `enabled`.
  - https://learn.chatgpt.com/docs/extend/mcp?surface=cli and https://learn.chatgpt.com/docs/config-file/config-reference
- **Skill-declared MCP dependency:**
  - A skill's `agents/openai.yaml` can declare `dependencies.tools: - type: "mcp"` with `value`, `transport` and `url`. https://learn.chatgpt.com/docs/build-skills
  - When the skill is used and the server is missing, Codex prompts "Install MCP servers?". Choosing Install writes the global config and calls `refresh_mcp_servers_now` in the current session.
  - The feature flag is `skill_mcp_dependency_install`, Stable, on by default.
  - https://github.com/openai/codex/blob/main/codex-rs/core/src/mcp_skill_dependencies.rs and https://github.com/openai/codex/blob/main/codex-rs/features/src/lib.rs
- **Picking up an external `codex mcp add`:** whether a running CLI session sees it is **UNVERIFIED**. Each `codex exec` run reads config at startup.

### Skill loading
- **At startup:** only name, description and file path go into context. The full `SKILL.md` is read when the skill is used, either implicitly or via `$name` or `/skills`. https://learn.chatgpt.com/docs/build-skills
- **Catalog budget:** at most 2% of the context window, or 8,000 chars if the window is unknown. Descriptions are shortened first, then skills dropped with a warning. `skills.max_context_tokens` (≤ 10000) changes the budget. https://learn.chatgpt.com/docs/build-skills and https://learn.chatgpt.com/docs/config-file/config-reference
- **Field caps:** `name` ≤ 64 chars and `description` ≤ 1,024 chars. https://github.com/openai/codex/blob/main/codex-rs/skills/src/parser.rs
- **references/ and assets/:** when these load is not stated (**UNVERIFIED**; presumably read on demand like ordinary files).

### Memory
- **AGENTS.md:**
  - Read from `~/.codex` and the Git root down to the cwd, capped by `project_doc_max_bytes` (default 32 KiB).
  - Built once per run.
  - https://learn.chatgpt.com/docs/agent-configuration/agents-md
- **Memories:** off by default; turn on with `[features] memories = true`. Generated in the background into `~/.codex/memories/`. https://learn.chatgpt.com/docs/customization/memories.md?surface=app
  - Whether `codex exec` runs feed memories is **UNVERIFIED**.
- **Resume:** `codex resume`, `codex exec resume [ID|--last]` and `codex fork`. https://learn.chatgpt.com/docs/non-interactive-mode
- **Rollout files:** `$CODEX_HOME/sessions/YYYY/MM/DD/rollout-<ts>-<id>.jsonl`; `--ephemeral` skips writing them. https://github.com/openai/codex/blob/main/codex-rs/rollout/src/recorder.rs

### Headless and metrics
- **Running:**
  - `codex exec "<prompt>" -m <model> [-c k=v] [--profile X] --json [-o last.txt] [--ephemeral] [--skip-git-repo-check]`.
  - The default sandbox is read-only.
  - https://learn.chatgpt.com/docs/non-interactive-mode and https://learn.chatgpt.com/docs/cli/reference
- **JSONL events:** `thread.started`, `turn.started`, `turn.completed{usage}`, `turn.failed` and `item.*`. https://github.com/openai/codex/blob/main/codex-rs/exec/src/exec_events.rs
  - `usage` has `input_tokens`, `cached_input_tokens`, `output_tokens` and `reasoning_output_tokens`.
  - Item types include `command_execution`, `mcp_tool_call`, `web_search`, `file_change` and `collab_tool_call`.
- **Getting the metrics:** count tool-type `item.completed` events and sum `turn.completed.usage`. There is no duration field, so time the process externally. This is derived from the schema above.
- **Custom providers:** `[model_providers.<id>]` with `base_url`, `env_key` and `wire_api`, selected with `model_provider`. https://learn.chatgpt.com/docs/config-file/config-advanced
  - **`wire_api` accepts only `"responses"`; `"chat"` is now an error.** https://github.com/openai/codex/blob/main/codex-rs/model-provider-info/src/lib.rs and https://github.com/openai/codex/discussions/7782
  - The docs have no OpenRouter example. Whether OpenRouter's Responses endpoint works with Codex for DeepSeek or Nemotron (including tool calls) is **UNVERIFIED**.
- **`--oss`:** for local Ollama and LM Studio only. https://learn.chatgpt.com/docs/config-file/config-advanced
- **Profiles:** since 0.134.0, `--profile X` overlays `$CODEX_HOME/X.config.toml`. https://learn.chatgpt.com/docs/config-file/config-advanced

## Hermes Agent (Nous Research)

### Install and location
- **One skills directory:** `~/.hermes/skills/` is the "single source of truth" for bundled, hub-installed and agent-created skills. Layout is `<category>/<skill>/SKILL.md`, with optional `references/`, `templates/`, `scripts/` and `assets/`. https://hermes-agent.nousresearch.com/docs/user-guide/features/skills
- **Installing from GitHub:**
  - `hermes skills install owner/repo/path`; `hermes skills tap add org/repo` adds a source.
  - Only `SKILL.md` and the support files it references are copied.
  - Every install is security-scanned. Without `GITHUB_TOKEN`, the GitHub API limit is 60 requests per hour.
  - Same page.
- **Copying by hand:** "Drop it in `~/.hermes/skills/` and it's live." https://hermes-agent.nousresearch.com/docs/guides/work-with-skills
- **When a new install takes effect:** the docs disagree.
  - The guide says it applies in new sessions (or with `/reset` or `--now`).
  - The skills page says the running session gets a note, and the system prompt picks the skill up at the next compaction.
- **Extra directories:** `skills.external_dirs` in `~/.hermes/config.yaml`. https://hermes-agent.nousresearch.com/docs/user-guide/features/skills

### MCP
- **Config:** `mcp_servers:` in `~/.hermes/config.yaml`. https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp and https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference
- **CLI:** `hermes mcp add <name> [--url URL] [--command CMD] [--args ...]`, plus `list`, `test`, `login`, `catalog` and `install`. https://hermes-agent.nousresearch.com/docs/reference/cli-commands
- **Reloading:**
  - Editing `config.yaml` during a session auto-reloads MCP (30 s timeout). `/reload-mcp`, `/new` and compaction also refresh it.
  - A running gateway picks up changes within about a minute.
  - Tools are named `mcp_<server>_<tool>`.
  - https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp
- **Agent self-registration:** not documented (**UNVERIFIED**; plausible through the terminal tool and `hermes mcp add`). For OAuth servers, the docs say to run `hermes mcp login` from a fresh terminal. Same page.

### Skill loading
- **Progressive disclosure:**
  - `skills_list()` returns name, description and category (about 3k tokens).
  - `skill_view(name)` loads SKILL.md; `skill_view(name, path)` loads one reference file.
  - A name/description index is in the system prompt, which stays stable for prompt caching.
  - https://hermes-agent.nousresearch.com/docs/user-guide/features/skills
- **Preloading:** `-s/--skills` or `/skill-name` preloads a skill. Same page.
- **Linter warnings (never blocking):** SKILL.md over about 24k chars ("stays in context for the rest of the session") and more than 60 reference files. Same page.
- **Measuring cost:** `hermes prompt-size` breaks down system-prompt bytes. https://hermes-agent.nousresearch.com/docs/reference/cli-commands

### Memory
- **MEMORY.md and USER.md:**
  - Stored in `~/.hermes/memories/`, capped at 2,200 and 1,375 chars.
  - Edited through the `memory` tool and injected at session start; writes are seen in the next session.
  - https://hermes-agent.nousresearch.com/docs/user-guide/features/memory
- **Session search:** `session_search` runs full-text search over `~/.hermes/state.db`. https://hermes-agent.nousresearch.com/docs/user-guide/sessions
- **Memory plugins:** Honcho, Mem0, Supermemory and others. https://hermes-agent.nousresearch.com/docs/user-guide/features/honcho
- **Agent-written skills:** the agent can write skills with `skill_manage`. https://hermes-agent.nousresearch.com/docs/user-guide/features/skills

### Headless and metrics
- **Running one-shot:**
  - `hermes chat --oneshot -q "..." -m <model> --provider openrouter [-Q] [--max-turns N] [--source tool] [--ignore-user-config --ignore-rules]`.
  - Exit codes: 0 completed, 1 failed or budget hit, 130 interrupted.
  - `hermes -z "..."` prints only the final answer.
  - https://hermes-agent.nousresearch.com/docs/reference/cli-commands
- **OpenRouter:** first-class, using `OPENROUTER_API_KEY` in `~/.hermes/.env`. https://hermes-agent.nousresearch.com/docs/integrations/providers
- **DeepSeek and Nemotron:** documented through their own providers (`--provider deepseek`, `--provider nvidia --model nvidia/nemotron-3-super-120b-a12b`). The same models through `--provider openrouter` is **UNVERIFIED** (likely, since model ids pass through).
- **Metrics:**
  - `--format stream-json`: count `tool_use` events. The final `result` event has `tokens{input,output,total,cache_read,cache_write}` and `duration_ms`. https://hermes-agent.nousresearch.com/docs/reference/cli-commands
  - `--usage-file <path>`: tokens, `api_calls` and `estimated_cost_usd`. It has no tool-call count or wall time. Same page.
  - `state.db` `sessions` table: `tool_call_count`, `api_call_count`, token columns, and `started_at`/`ended_at`. https://hermes-agent.nousresearch.com/docs/developer-guide/session-storage
  - `hermes sessions export --session-id ID`: `timings.wall_clock_ms` and `tool_calls_emitted`. `hermes insights` also reports usage. https://hermes-agent.nousresearch.com/docs/user-guide/sessions

## OpenClaw

### Install and location
- **Installing:**
  - `openclaw skills install @owner/<slug>` (ClawHub), `git:owner/repo[@ref]`, or `./path --as name`.
  - The default target is the active workspace's `skills/`; `--global` targets `~/.openclaw/skills`.
  - npm specs and zip files are not supported.
  - https://docs.openclaw.ai/cli/skills
- **Precedence, highest first:** `<workspace>/skills`, `<workspace>/.agents/skills`, `~/.agents/skills`, `~/.openclaw/skills`, agent workshop skills, bundled skills, then `skills.load.extraDirs` and plugins. https://docs.openclaw.ai/tools/skills
- **Discovery:** SKILL.md is found up to 6 levels deep, and the skill is named by frontmatter `name`. Same page.
- **Watcher:** rescans about once a minute; sessions pick up changes on the next turn. Same page.
- **Default workspace:** `~/.openclaw/workspace`. https://docs.openclaw.ai/concepts/agent-workspace
- **Copying by hand:** not documented as an install method (**UNVERIFIED**; implied by the watcher).

### MCP
- **Config:** native, under `mcp.servers` in `~/.openclaw/openclaw.json`. stdio uses `command`/`args`/`env`; HTTP uses `url`/`transport`. https://docs.openclaw.ai/gateway/config-extensions
- **CLI:** `openclaw mcp add <name> --command ... --arg ...` or `openclaw mcp set <name> '<json>'`. These refuse while the local Gateway is running; live changes go through the Control UI. https://docs.openclaw.ai/cli/mcp/registry
- **Applying changes:** changed servers are rebuilt at the next turn's tool discovery, so no Gateway restart is needed. https://docs.openclaw.ai/gateway/config-extensions
- **Tool profiles:** MCP tools are exposed in the `coding` and `messaging` tool profiles, not in `minimal`. https://docs.openclaw.ai/cli/mcp/registry
- **Agent self-registration:**
  - The Gateway exposes `config.patch` and `config.apply`. https://github.com/openclaw/openclaw/blob/main/docs/gateway/configuration/config-rpc.md
  - Whether the agent can write `mcp.servers` itself is **UNVERIFIED**.
- **mcporter:** the bundled mcporter skill calls MCP servers through its own `./config/mcporter.json`, separate from `mcp.servers`. https://github.com/openclaw/openclaw/blob/main/skills/mcporter/SKILL.md

### Skill loading
- **What gets injected:** only a compact `<available_skills>` block (name, description, SKILL.md location) goes into the system prompt. The agent reads SKILL.md on demand. https://docs.openclaw.ai/tools/skills and https://docs.openclaw.ai/concepts/system-prompt
- **Cost:** base overhead plus about 97 chars per skill plus the field lengths (about 24 tokens per skill before fields). https://docs.openclaw.ai/tools/skills
- **Caps:** `skills.limits.maxSkillsPromptChars` (descriptions are shortened, then dropped), `maxSkillsInPrompt`, `maxSkillFileBytes`. Up to 64 library skills per new session. Same page.
- **Gating:** `metadata.openclaw.requires.{bins,env,config}` gates a skill. Same page.

### Memory
- **Workspace files:**
  - `MEMORY.md` loads in the main private session only.
  - Today's and yesterday's `memory/YYYY-MM-DD.md` load on `/new`.
  - `AGENTS.md`, `SOUL.md` and `USER.md` load every session.
  - https://docs.openclaw.ai/concepts/memory
- **Bootstrap caps:** 20,000 chars per file and 60,000 in total. https://docs.openclaw.ai/concepts/system-prompt
- **Tools:** `memory_search`/`memory_get` (memory-core plugin), `sessions_search`/`sessions_history`, and a memory flush before compaction. https://docs.openclaw.ai/concepts/memory
- **Session storage:** sessions are in `~/.openclaw/agents/<agentId>/agent/openclaw-agent.sqlite`; JSONL transcripts are legacy. https://docs.openclaw.ai/concepts/session

### Headless and metrics
- **`openclaw agent exec`:**
  - `openclaw agent exec "<prompt>" --model <provider/model> --thinking <level> --json [--timeout 600] [--state-dir d]`.
  - No Gateway is needed and state is temporary by default. Workspace bootstrap files are skipped by default.
  - Exit codes: 0 success, 1 error, 2 timeout.
  - https://docs.openclaw.ai/cli/agent
  - Its JSON has `usage{input,output,total}`, `costUsd`, `assistantTurns`, `toolSummary{calls,tools,totalToolTimeMs}`, `model` and `sessionId`. It has no wall-time field. Same page.
- **`openclaw agent`:** `--agent <id> --message "..." --local --json` returns `meta.durationMs` and `meta.toolSummary.calls`. Same page.
- **Usage tracking:** `/status`, `/usage`, `openclaw status --usage` and the `sessions.usage` gateway method. https://docs.openclaw.ai/concepts/usage-tracking
- **OpenRouter:**
  - Set `OPENROUTER_API_KEY`; model refs are `openrouter/<provider>/<model>`, resolved against OpenRouter's live catalog.
  - DeepSeek refs are documented (`openrouter/deepseek/deepseek-v4-flash`).
  - If a model's OpenRouter `supported_parameters` lack `tools`, OpenClaw sends no tool definitions.
  - https://docs.openclaw.ai/providers/openrouter
  - Nemotron is not mentioned (**UNVERIFIED**).

## What this means for a lean skill

- **Loading cost:** all four Hosts load skills on demand. At session start only the name, description and path are in context. SKILL.md loads when the skill is used, and reference files load only when read (Hermes: `skill_view(name, path)`; Codex's handling of references is unverified). Every Host keeps a loaded SKILL.md in context for the rest of the session.
- **Description limits:** they are capped and can be shortened or dropped under budget pressure. Claude Code caps a description at 1,536 chars, with the listing at about 1% of context. Codex caps it at 1,024 chars, with the catalog at 2% of context or 8,000 chars. OpenClaw charges about 97 chars per skill plus the field lengths.
- **Self-service MCP install is first-party only in Codex:** a skill can declare an MCP dependency in `agents/openai.yaml`, and Codex prompts to install it and reloads in-session. The other Hosts expose a CLI (`claude mcp add`, `hermes mcp add`, `openclaw mcp add/set`), and none documents a skill calling it. OpenClaw's CLI refuses while the Gateway runs. Claude Code needs a restart after `.mcp.json` edits.
- **Measuring a Task budget headlessly:** the four Hosts expose different fields.
  - Tool-call count is a field only in OpenClaw (`toolSummary.calls`) and Hermes (`state.db`, export); Claude Code and Codex need event counting.
  - Wall time is a field in Claude Code (`duration_ms`), Hermes and `openclaw agent` (not `agent exec`); Codex needs external timing.
- **OpenRouter models:** first-class only in Hermes and OpenClaw. Anthropic does not support non-Claude models in Claude Code. Codex accepts only Responses-API providers, and OpenRouter use there is unverified.

## Unknowns

1. Claude Code: does a server added with `claude mcp add` mid-session appear without a restart? Is a skill/script running `claude mcp add` a supported pattern?
2. Claude Code: does `--output-format json` emit exactly `SDKResultMessage` (`num_turns`, `duration_ms`, `usage`)? No official tool-call count field.
3. Claude Code with OpenRouter DeepSeek or Nemotron: unsupported by Anthropic. Whether tool calling works in practice is untested.
4. Codex: whether OpenRouter's Responses endpoint works with Codex for DeepSeek or Nemotron, including tool calls. Whether references/ files are loaded only on read. Whether a running CLI session sees an external `codex mcp add`. Whether `codex exec` runs feed Memories.
5. Hermes: whether a newly installed skill applies only in a new session or mid-session (the docs conflict). Whether OpenRouter ids for DeepSeek and Nemotron work under `--provider openrouter`. Whether agent self-registration of MCP via `hermes mcp add` works. The Hermes docs URLs were built from the site config, not opened.
6. OpenClaw: whether the agent can write `mcp.servers` via the gateway tool or `config.patch`. Nemotron via OpenRouter and its tool support. Manual copy as an install method. Current on-disk transcript layout (SQLite vs legacy JSONL).
7. All Hosts: real token cost of this repo's two skills (`agent-wallet`, `agent-wallet-mcp`) at session start, measured with each Host's own tooling (`/context`, `hermes prompt-size`, `/context list`). Not measured here.
