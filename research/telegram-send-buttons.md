# Tap buttons for the Send check on Telegram Hosts

Research for [#15](https://github.com/mackendell/agentic-wallet/issues/15) (map [#1](https://github.com/mackendell/agentic-wallet/issues/1)). Sources read 2026-10-13. I used only primary sources: official docs and official GitHub repos. Any claim not confirmed in a primary source is marked **UNVERIFIED**. Nothing here was run against a live Telegram bot.

Source snapshots:
- **Hermes Agent:** `NousResearch/hermes-agent` at [`63d0b94`](https://github.com/NousResearch/hermes-agent/tree/63d0b94120027d487c9a5235b9ec64b696af1b26) (main, 2026-10-12). Latest release is `v0.21.7` (2026-10-12). Doc URLs are built from the site config, as in [host-skill-loading](https://github.com/mackendell/agentic-wallet/blob/research/host-skill-loading/research/host-skill-loading.md). The docs were read as Markdown under `website/docs/`.
- **OpenClaw:** `openclaw/openclaw` at [`a217b99`](https://github.com/openclaw/openclaw/tree/a217b99a2ef7ce7caee90ae6add3955879d2432a) (main, `package.json` version `2026.10.2`). Latest stable release is `v2026.10.2` (2026-10-12).

Short links below: `H/` = `https://github.com/NousResearch/hermes-agent/blob/63d0b94120027d487c9a5235b9ec64b696af1b26/` and `O/` = `https://github.com/openclaw/openclaw/blob/a217b99a2ef7ce7caee90ae6add3955879d2432a/`.

## Answer in one table

| | Hermes Agent | OpenClaw | Claude Code | Codex |
|---|---|---|---|---|
| **Telegram channel** | Built in (gateway) | Built in (channel) | Opt-in plugin, research preview | None |
| **Agent-callable buttons** | `clarify` tool | `ask_user` tool; also `message` tool with `presentation.blocks[].buttons` | No. The `reply` tool is text and files only | n/a |
| **What a tap returns** | The `clarify` **tool result** in the same turn: `{"responses":[{"user_response":"Yes",...}],"outcome":"submitted"}` | `ask_user`: the **tool result** in the same turn: `{"status":"answered","answers":{"answers":{"<id>":["Yes"]}}}`. `message` buttons: a **new inbound user message** with the text `callback_data: <value>` | n/a | n/a |
| **Typed "yes" while buttons are up** | Resolves the prompt if it matches a choice label (case-insensitive) or its number; other prose cancels the prompt and goes on as a normal message | Resolves the prompt: a number, a label (case-insensitive) or free text, all accepted as the answer | Plain chat | Plain chat |
| **Version** | Buttons since `v2026.5.16`; typed label/number replies since `v2026.7.1`; prose-cancels-prompt since `v2026.7.30` | `ask_user` since `2026.8.1` (Telegram native controls fixed in the same release) | Channels research preview | n/a |
| **Config needed** | None. `clarify` is in the default Telegram toolset | None by default. `ask_user` is in the `coding` and `messaging` profiles, and an unset profile does not filter core tools. Buttons need `channels.telegram.capabilities.inlineButtons` not `off` (default `allowlist`) | `--channels plugin:telegram@claude-plugins-official` | n/a |
| **Without buttons** | Numbered text list; any typed reply is captured | Plain text; a reply with a number, label or own answer works | n/a | n/a |

## Hermes Agent

### Which tool, and how a skill triggers it
- **The tool is `clarify`.** It is the Host's own tool, and a skill triggers it only by telling the model to call it. The schema ([H/tools/clarify_tool.py](https://github.com/NousResearch/hermes-agent/blob/63d0b94120027d487c9a5235b9ec64b696af1b26/tools/clarify_tool.py)):
  - `questions`: array of 1-5 `{question, choices?, multi_select?}`. Choices are capped at 4: `MAX_CHOICES = 4  # the UI always appends an "Other (type your answer)" row`.
  - Tool description: "single-select (up to 4 choices — put your recommended option FIRST, the UI marks it '(Recommended)' and auto-appends an 'Other' free-text row)".
- **Older schema:** `v2026.5.16` had a different schema, top-level `question` + `choices`. `v2026.9.24` and main use `questions: [...]`. So the skill should name the tool, not hard-code its JSON. The model sees the schema anyway.
- **"(Recommended)" label:** with two or more choices the first one is shown with a "(Recommended)" suffix automatically (`mark_recommended`, `RECOMMENDED_LABEL = "(Recommended)"`). The suffix is stripped from the answer the agent gets back, but the user sees it. A skill cannot turn it off.
- **Skill precedent:** a bundled skill tells the model to use it by name: "Use the `clarify` tool to confirm options with the user. Put the independent questions below in one `questions` array" ([H/skills/creative/baoyu-infographic/SKILL.md](https://github.com/NousResearch/hermes-agent/blob/63d0b94120027d487c9a5235b9ec64b696af1b26/skills/creative/baoyu-infographic/SKILL.md)).
- **Nothing in the tool text forbids confirmations.** It says "Prefer deciding low-stakes questions yourself; don't use this for dangerous-command confirmation (the terminal tool handles that)". That second part is about shell commands.

### What Telegram shows
- **Docs** ([telegram.md, "Interactive Prompts (clarify)"](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram)): "When the agent calls the `clarify` tool … Telegram renders the question with **inline keyboard buttons**".
- **Buttons are numbers, not words.** In the adapter ([H/plugins/platforms/telegram/adapter.py](https://github.com/NousResearch/hermes-agent/blob/63d0b94120027d487c9a5235b9ec64b696af1b26/plugins/platforms/telegram/adapter.py) `send_clarify`), the full option text goes in the message body and the buttons are labelled `1`, `2`, … plus "✏️ Other (type answer)":
  ```python
  # Full option text in the body (mobile truncates button labels); buttons keep numeric labels.
  text += "\n\n" + "\n".join(f"{i + 1}. {_html.escape(str(c))}" for i, c in enumerate(choices))
  rows = [[InlineKeyboardButton(str(idx + 1), callback_data=f"cl:{clarify_id}:{idx}")] for idx in range(len(choices))]
  ```
  So the user sees "1. Yes / 2. No" in the text and taps **1** or **2**, not a **Yes, send** button.
- **No toolset change needed.** `clarify` is in the core tool list, and `hermes-telegram` is `_bundle(...)` of it ([H/toolsets.py](https://github.com/NousResearch/hermes-agent/blob/63d0b94120027d487c9a5235b9ec64b696af1b26/toolsets.py) L26, L208). It is not in `_DEFAULT_OFF_TOOLSETS` ([H/hermes_cli/tools_config.py](https://github.com/NousResearch/hermes-agent/blob/63d0b94120027d487c9a5235b9ec64b696af1b26/hermes_cli/tools_config.py) L110).
  - It is removed only from `hermes-acp` and `hermes-api-server`, which have no chat UI.

### How the tap comes back
- **Same turn, as a tool result.** The tool blocks the agent thread until a tap, a typed reply or the timeout ([H/tools/clarify_gateway.py](https://github.com/NousResearch/hermes-agent/blob/63d0b94120027d487c9a5235b9ec64b696af1b26/tools/clarify_gateway.py) module docstring). The tap handler resolves it with the choice text: `resolve_gateway_clarify(clarify_id, resolved_text)` (`_handle_clarify_callback`).
- **Result shape:** `{responses: [{question, choices_offered, status, user_response}], outcome}`, where `outcome` is `submitted | cancelled | timed_out | undelivered` (tool description). It is **not** a new user message.
- **Who can tap:** taps go through `_claim_callback_state`, which runs `_callback_authorized` first. A non-allowed group member cannot answer.
- **Typed answers.** `_coerce_text_response_detailed` handles a typed reply while a choice prompt is pending:
  - A number, or text equal to a choice label ignoring case and the "(Recommended)" suffix (`_match_label`), resolves the prompt.
  - `skip` skips it.
  - An out-of-range number keeps the prompt armed.
  - Other prose is `rejected_prose`. The gateway then **cancels** the prompt and routes the text as a normal message ([H/gateway/run_inbound.py](https://github.com/NousResearch/hermes-agent/blob/63d0b94120027d487c9a5235b9ec64b696af1b26/gateway/run_inbound.py) L434: "Native-choice prompts reject unmatched prose so it continues through normal busy routing. Release this clarify first").
  - **What this means for labels:** with choices `["Yes", "No"]`, a typed `yes` resolves to `Yes`. With `["Yes, send", "No"]`, a typed `yes` does **not** match. The clarify returns `outcome: cancelled` and the `yes` arrives as a separate follow-up message, which a cheap model could misread.
- **Timeout:** `agent.clarify_timeout`, default 3600 s; `0` means unlimited (`resolve_clarify_timeout`; [configuration.md "Clarify"](https://hermes-agent.nousresearch.com/docs/user-guide/configuration)).

### Versions (from the GitHub commit history and release tags)
- **Buttons:** [`29d7c24`](https://github.com/NousResearch/hermes-agent/commit/29d7c244c5d55230e838c049afb13d307168679c) "feat(gateway): wire clarify tool with inline keyboard buttons on Telegram (#24199)", 2026-05-12. It is in `v2026.5.16` and not in `v2026.5.7`.
- **Typed label/number answers:** [`d7f655f`](https://github.com/NousResearch/hermes-agent/commit/d7f655f370) "fix: accept typed clarify choice replies", 2026-06-28. First release `v2026.7.1`.
- **Prose cancels the prompt:** [`07cbb50`](https://github.com/NousResearch/hermes-agent/commit/07cbb500b62f4cbd29929c265962763531c51e49) "reject arbitrary prose for native interactive multi-choice clarifies", 2026-07-22. First release `v2026.7.30`. Before that, the exact behaviour for typed prose is **UNVERIFIED**.
- **Current result shape:** [`5eea878`](https://github.com/NousResearch/hermes-agent/commit/5eea87882aebdeded8204b083b36acb17f7247f8) "one question shape and one result shape on every surface", 2026-09-29. It is in `v0.21.7`.

### Channels without buttons
- **Default adapter behaviour:** the base adapter's `send_clarify` sends a numbered list and calls `mark_awaiting_text`, so **any** typed reply becomes the answer ([H/gateway/platforms/base.py](https://github.com/NousResearch/hermes-agent/blob/63d0b94120027d487c9a5235b9ec64b696af1b26/gateway/platforms/base.py) `send_clarify`).
- **Adapters with buttons:** Telegram, Slack, Discord, WhatsApp, Google Chat and Photon override `send_clarify` (grep for `InlineKeyboardButton`/`send_clarify` under `plugins/platforms/`).
- **Telegram fallback:** "If Telegram cannot render the button card … Hermes re-asks the same question as a plain numbered-list message and your typed reply (a number or the option text) is taken as the answer. When even that cannot be delivered, the agent is released at once with `[clarify prompt could not be delivered]`" ([telegram.md](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram)).

## OpenClaw

### Two ways to get buttons
1. **The `ask_user` tool.** This is the structured path ([docs/tools/ask-user.md](https://docs.openclaw.ai/tools/ask-user), [O/src/agents/tools/ask-user-tool-normalization.ts](https://github.com/openclaw/openclaw/blob/a217b99a2ef7ce7caee90ae6add3955879d2432a/src/agents/tools/ask-user-tool-normalization.ts)):
   - Schema: `{questions: [{id, header (≤12 chars, truncated), question, options: [{label (≤64 chars), description?}] (2-4), multiSelect?}] (1-3), timeoutSeconds? (default 900, clamped 30-3600)}`.
   - Free-text "Other" is always added (`isOther: true`).
   - Telegram: "Telegram renders each choice as a full-width native button for one single-select question. **Other…** switches to Telegram's reply input without resolving the question."
   - Unlike Hermes, the **button text is the label**, so a real **Yes** / **No** button is possible.
2. **The `message` tool, `action: "send"`, with `presentation.blocks: [{type: "buttons", buttons: [{label, action: {type: "callback", value}, style?}]}]`** ([docs/channels/telegram/rich-messages.md](https://docs.openclaw.ai/channels/telegram/rich-messages), "Inline buttons"; the docs example is literally Yes/No/Cancel).
   - A tap is **not** tied to the turn: "Callback action values not claimed by a registered plugin interactive handler are passed to the agent as text: `callback_data: <value>`" ([O/extensions/telegram/src/bot-handlers.callback-router.ts](https://github.com/openclaw/openclaw/blob/a217b99a2ef7ce7caee90ae6add3955879d2432a/extensions/telegram/src/bot-handlers.callback-router.ts) L142: ``const genericCallbackText = data.startsWith("/") ? data : `callback_data: ${data}`;``).
   - So the tap arrives as a new user message in a new turn.
   - It needs a `to` chat id. Whether `to` can be left out to mean "this chat" is **UNVERIFIED**.
   - It also needs the `message` tool allowed and `channels.telegram.actions.sendMessage` not disabled.

### The catch with `ask_user`: its own description says not to use it for this
- **The tool description sent to the model** ([O/src/agents/tool-description-presets.ts](https://github.com/openclaw/openclaw/blob/a217b99a2ef7ce7caee90ae6add3955879d2432a/src/agents/tool-description-presets.ts) L180): "Use only when blocked on a decision genuinely theirs that cannot be resolved from the request, code, or sensible defaults; **never ask whether to proceed or confirm a plan.**"
- **The docs agree:** "The agent should not use `ask_user` to ask whether it may proceed or to confirm its own plan."
- **This is guidance only.** The code does not block it. A Send check is arguably "a decision genuinely theirs", since the user's money moves.
- **Risk on cheap models:** a skill that says "use `ask_user`" contradicts the Host's own tool text, and a cheap Target model may follow either one. The failure mode is safe if the skill still requires a typed yes when no tool answer arrives. It is never "send without asking", provided the skill states the Send check as mandatory.
- **Model behaviour is UNVERIFIED.** No test was run.
- **Another model-facing rule:** "Put the recommended option first and suffix its label with ` (Recommended)`". The model adds this itself, so the skill can tell it not to mark either option.

### How the tap comes back (`ask_user`)
- **Same turn, as a tool result:** `{"status":"answered","answers":{"answers":{"<id>":["Yes"]}}}`, or `status: "no_answer"` on timeout or cancel ([ask-user.md](https://docs.openclaw.ai/tools/ask-user)).
- **Telegram taps** use a private callback envelope `tgq1:<ask_id>:<index>` ([O/extensions/telegram/src/question-callback-data.ts](https://github.com/openclaw/openclaw/blob/a217b99a2ef7ce7caee90ae6add3955879d2432a/extensions/telegram/src/question-callback-data.ts)). They resolve through the gateway question runtime, not through chat text.
- **Typed answers** ([O/src/agents/harness/user-input-bridge.ts](https://github.com/openclaw/openclaw/blob/a217b99a2ef7ce7caee90ae6add3955879d2432a/src/agents/harness/user-input-bridge.ts) `normalizeAgentHarnessUserInputOption`):
  - A number maps to the option.
  - A label match ignores case (`option.label.toLowerCase() === trimmed.toLowerCase()`).
  - Because `isOther` is true, any other text is taken as a free-text answer.
  - Docs: "a plain-text reply works on any channel when your current permissions match the creator's. Reply with a number, an option label, or your own answer."
  - So a typed `yes please` comes back as the answer string `"yes please"`. The model has to read it as a yes.
- **Who can tap:** button-tap authorization follows Telegram access policy. The default `"allowlist"` applies sender authorization (rich-messages.md).

### Availability and config
- **Profiles:** `ask_user` is in the `coding` and `messaging` tool profiles ([O/src/agents/tool-catalog.ts](https://github.com/openclaw/openclaw/blob/a217b99a2ef7ce7caee90ae6add3955879d2432a/src/agents/tool-catalog.ts) L208; [tool-policy docs](https://docs.openclaw.ai/gateway/config-tools/tool-policy)). Docs: "An unset profile also leaves core tools unfiltered".
- **Main session only:** "The tool is available only in the main session. Subagents and other non-primary runs do not receive it."
- **Buttons setting:** inline-button scope is `channels.telegram.capabilities.inlineButtons`: `off | dm | group | all | allowlist` (default `allowlist`). Whether `inlineButtons: "off"` turns `ask_user` into text-only, rather than dropping the prompt, is **UNVERIFIED**. The docs state the scope only for `message`-tool sends and exec approvals.
- **Version:** release notes for `2026.8.1` list "Add structured ask_user questions across chat surfaces [#109922]" and "fix(telegram): make ask_user controls native and reliable [#130262]" ([docs/releases/2026.8.1/messaging.md](https://github.com/openclaw/openclaw/blob/a217b99a2ef7ce7caee90ae6add3955879d2432a/docs/releases/2026.8.1/messaging.md)). The earliest version with `presentation` buttons on the `message` tool is **UNVERIFIED**.

### Channels without buttons
- **Docs:** "Discord, Slack, and Mattermost render native buttons for a single-choice, single-question prompt." Other channels get readable text, and a typed reply answers it. "Multi-question and multi-select prompts degrade to readable text on messaging channels."
- **So:** use one question, single-select, to get buttons on Telegram.

### Exec approvals (not usable for this)
OpenClaw also has Telegram approval buttons (`channels.telegram.execApprovals`), but these are for the Host's own exec/plugin approvals ([rich-messages.md](https://docs.openclaw.ai/channels/telegram/rich-messages), "Exec approvals in Telegram"). A skill cannot raise them for a wallet transfer. **UNVERIFIED** whether an MCP tool call can be routed through them.

## Claude Code and Codex
- **Claude Code** has no Telegram channel by default.
  - The Telegram "channel" is an opt-in plugin in **research preview**, started with `claude --channels plugin:telegram@claude-plugins-official` ([code.claude.com/docs/en/channels](https://code.claude.com/docs/en/channels)).
  - Its `reply` tool takes `chat_id, text, reply_to?, files?, format?`, with no buttons ([plugin source](https://github.com/anthropics/claude-plugins-official/tree/main/external_plugins/telegram), `server.ts`).
  - Its only inline keyboard is the Host's **permission relay** (`✅ Allow` / `❌ Deny` on a tool-permission prompt). That is driven by Claude Code's permission system, not by a skill.
  - The terminal itself has a multiple-choice question tool, but "When you run channels in non-interactive mode with `-p`, tools that need terminal input, such as multiple-choice questions … are disabled."
  - Typed "yes" is the only route.
- **Codex** has no Telegram channel. A GitHub code search for `telegram` in `openai/codex` returned no results (2026-10-13). Typed "yes" is the only route.

## Recommendation for the skill

1. **Keep the typed yes as the base contract on every Host.** Buttons are a convenience on top of it, never a replacement. Nothing changes for Claude Code or Codex.
2. **On Hermes or OpenClaw, add one short conditional line to the Send check.** For example: "If you have a `clarify` tool (Hermes) or an `ask_user` tool (OpenClaw), ask the Send check with it as one single-choice question. Choices are exactly `Yes` and `No`. Do not add an Other option or a '(Recommended)' mark. Otherwise end with: Reply **yes** to send."
   - **Put the full one-line Send check in the question text.** On Hermes that text is the message the buttons hang under. On OpenClaw `question` is meant to be one sentence but has no hard length limit, so the Send check line still fits.
   - **Labels must be exactly `Yes` / `No`** (in the user's language), not "Yes, send". Then a typed `yes` (or `1`) also resolves the prompt on both Hosts. On Hermes, a longer label makes a typed `yes` cancel the prompt instead.
   - **Treat only `user_response == "Yes"` (Hermes) or `answers[id] == ["Yes"]` (OpenClaw) as the user's yes.**
     - Anything else (`No`, free text, `skipped`, `cancelled`, `timed_out`, `undelivered`, `no_answer`) is not a yes. The skill should then fall back to "Reply yes to send" in plain chat.
     - On Hermes `cancelled`, the user's typed text arrives as the next message. Read that as the reply.
3. **Don't use OpenClaw's `message`-tool buttons for the Send check.** The tap arrives as a new turn with the text `callback_data: yes`. It is not bound to the question, it needs a chat id, and a cheap model must recognise that string. `ask_user` is bound to the waiting turn.
4. **Known risks to test on a Target model before shipping:**
   - Whether cheap models call the tool at all.
   - On OpenClaw, whether they obey the tool's "never ask whether to proceed" line over the skill.
   - Whether they read the tool result correctly.
   - All three are **UNVERIFIED**. If a model skips the tool, the typed-yes fallback still holds, as long as the skill makes the Send check itself mandatory.
5. **Tell the user about Hermes's numbered buttons.** On Hermes the buttons read **1** and **2**, with "1. Yes / 2. No" in the text above them. It still saves typing, but it is not a labelled **Yes, send** button.

## Unknowns
- **OpenClaw `inlineButtons: "off"`:** how `ask_user` renders with this setting (text fallback assumed).
- **OpenClaw `message` tool:** whether `to` can be omitted for the current chat.
- **Target models:** how reliably cheap models (Nemotron, DeepSeek Flash) call `clarify`/`ask_user` from a skill instruction and parse the result. No evals exist yet.
- **Hermes before `v2026.7.30`:** how typed prose behaved.
