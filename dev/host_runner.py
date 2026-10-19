#!/usr/bin/env python3
"""Seam 1 on OpenClaw, Claude Code and Codex: run a Test plan case headless, N times, one JSON line per run.
Same record as dev/hermes_runner.py (Hermes has its own runner).

Usage:
  python3 dev/host_runner.py --host openclaw --case setup --runs 3          # DeepSeek Flash via OpenRouter
  python3 dev/host_runner.py --host claude-code --case setup --runs 1       # Sonnet (your Claude Code login)
  python3 dev/host_runner.py --host codex --case setup --runs 1             # Codex default model (your Codex login)
  python3 dev/host_runner.py --host openclaw --source local                 # before a push: skill from this checkout

Each run gets a fresh throwaway HOME, so every Host config (~/.openclaw, ~/.claude.json + ~/.claude, ~/.codex) is
new and empty; the user's real Host configs are never read for MCP or written. Credentials:
- OpenClaw: OPENROUTER_API_KEY (env, else ~/.hermes/.env), model openrouter/<--model>.
- Claude Code: the macOS keychain login (the throwaway HOME gets a symlink to ~/Library/Keychains, CLAUDE_CONFIG_DIR is
  left unset, so the same login item is used). Linux: set ANTHROPIC_API_KEY.
- Codex: a copy of ~/.codex/auth.json in the throwaway ~/.codex. The runner checks the real file is unchanged.
macOS: the MCP service runs under a throwaway account (COINWALLET_TEST_USER=cwr-...), so the real keychain items are
never used. Each macOS run leaves one test keychain item (empty test wallet).

--source github: the agent gets the README sentence with the repo swapped to --repo; the Host's install command
  (`... CoinsDo/agentic-wallet ...`) is redirected to --repo by a shim.
--source local: the agent gets "Install the CoinWallet skill from <this checkout>/README.md"; the install command is
  redirected to this checkout (each Host can install a marketplace from a local path).

Turns after the first are fixed scripted replies (--reply), sent by resuming the same session:
  OpenClaw `openclaw agent --local --json --session-id <id>`, Claude Code `claude -p --resume <id>`,
  Codex `codex exec resume <id> --json`.
"""
import argparse
import hashlib
import json
import os
import shlex
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hermes_runner  # noqa: E402
from hermes_runner import (AGENTTEST_URL, PROXY, SKILL_PATH, NeedsHuman, RunningService, ThrowawayService, newbie_service, service_stub,  # noqa: E402
                           human_value, openrouter_key, probe_entry, read_log, read_truth, sent_bundles, wait_settled)
from test_cases import CASES, HOOKS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REAL_HOME = Path.home()
IS_MAC = sys.platform == "darwin"
REAL = {name: shutil.which(name) or str(REAL_HOME / ".local" / "bin" / name) for name in ("openclaw", "claude", "codex")}
DEFAULT_MODEL = {"openclaw": "deepseek/deepseek-v4-flash", "claude-code": "sonnet", "codex": None}
TOOL = {"openclaw": "openclaw", "claude-code": "claude", "codex": "codex"}


def make_run_dir(base, host, target):
    run = Path(tempfile.mkdtemp(prefix=host + "-run-", dir=base))
    home, bin_dir, work = run / "home", run / "bin", run / "work"
    for d in (home, bin_dir, work):
        d.mkdir()
    if IS_MAC:
        (home / "Library").mkdir()
        os.symlink(str(REAL_HOME / "Library" / "Keychains"), str(home / "Library" / "Keychains"))
    if host == "codex":
        (home / ".codex").mkdir()
        shutil.copyfile(str(REAL_HOME / ".codex" / "auth.json"), str(home / ".codex" / "auth.json"))
        os.chmod(str(home / ".codex" / "auth.json"), 0o600)
    # Host shim: the install command names CoinsDo/agentic-wallet; point it at the repo under test.
    real = REAL[TOOL[host]]
    shim = bin_dir / TOOL[host]
    shim.write_text(
        "#!/bin/bash\n"
        "args=()\n"
        "for a in \"$@\"; do\n"
        "  case \"$a\" in *CoinsDo/agentic-wallet) a=" + shlex.quote(target) + ";; esac\n"
        "  args+=(\"$a\")\n"
        "done\n"
        "exec " + shlex.quote(real) + " \"${args[@]}\"\n", encoding="utf-8")
    os.chmod(str(shim), 0o755)
    return run, home, bin_dir, work


def run_env(host, home, bin_dir, user):
    env = {
        "PATH": str(bin_dir) + os.pathsep + os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "USER": os.environ.get("USER", ""),
        "LANG": os.environ.get("LANG", "en_US.UTF-8"),
        "TERM": "dumb",
        "COINWALLET_TEST_USER": user,
    }
    if host == "openclaw":
        env["OPENROUTER_API_KEY"] = openrouter_key()
    if host == "claude-code" and os.environ.get("ANTHROPIC_API_KEY"):
        env["ANTHROPIC_API_KEY"] = os.environ["ANTHROPIC_API_KEY"]
    assert not IS_MAC or (home / "Library" / "Keychains").exists()
    return env


def run_turn(argv, env, work, timeout):
    started = time.monotonic()
    try:
        proc = subprocess.run(argv, env=env, cwd=str(work), capture_output=True, text=True, timeout=timeout,
                              stdin=subprocess.DEVNULL)
        stdout, stderr, timed_out = proc.stdout, proc.stderr, False
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr, timed_out = "", True
    return stdout, stderr, time.monotonic() - started, timed_out


def json_lines(text):
    events = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                events.append(json.loads(line))
            except ValueError:
                pass
    return events


# ---------- per-Host turn + transcript ----------

class OpenClaw:
    def __init__(self, args, number):
        self.model = "openrouter/" + args.model
        self.session = "cw-" + time.strftime("%H%M%S") + "-" + str(number)
        self.calls, self.tokens, self.cached, self.cost, self.reply = 0, 0, 0, 0.0, ""

    def turn(self, prompt, env, work, timeout):
        argv = [REAL["openclaw"], "agent", "--local", "--json", "--session-id", self.session, "--model", self.model,
                "--message", prompt, "--timeout", str(timeout)]
        stdout, stderr, secs, timed_out = run_turn(argv, env, work, timeout + 30)
        start = stdout.find("{")
        try:
            data = json.loads(stdout[start:]) if start >= 0 else {}
        except ValueError:
            data = {}
        meta = data.get("meta") or {}
        agent = meta.get("agentMeta") or {}
        self.calls += (meta.get("toolSummary") or {}).get("calls", 0)
        self.tokens += (agent.get("usage") or {}).get("total", 0)
        self.cached += (agent.get("usage") or {}).get("cacheRead", 0)
        self.cost += agent.get("costUsd") or 0.0
        texts = [p.get("text", "") for p in data.get("payloads") or [] if p.get("text")]
        self.reply = "\n".join(texts) or meta.get("finalAssistantVisibleText") or ""
        return [data], secs, timed_out, stderr[-2000:]

    def tool_uses(self, home):
        """Tool calls (name + arguments) from OpenClaw's session store; big events are zstd-compressed."""
        db_path = home / ".openclaw" / "agents" / "main" / "agent" / "openclaw-agent.sqlite"
        uses = []
        try:
            db = sqlite3.connect(str(db_path))
            rows = db.execute("select event_json, event_zstd from transcript_events where session_id = ? order by seq",
                              (self.session,)).fetchall()
            db.close()
        except sqlite3.Error:
            return uses
        for text, blob in rows:
            if text is None and blob is not None:
                text = subprocess.run(["zstd", "-dc"], input=blob, capture_output=True).stdout.decode("utf-8", "replace")
            try:
                event = json.loads(text or "{}")
            except ValueError:
                continue
            message = event.get("message") or {}
            if message.get("role") == "assistant" and isinstance(message.get("content"), list):
                for block in message["content"]:
                    if block.get("type") == "toolCall":
                        uses.append({"name": block.get("name"), "input": block.get("arguments") or {}})
        return uses

    def registered(self, home):
        try:
            return json.loads((home / ".openclaw" / "openclaw.json").read_text())["mcp"]["servers"]["coinwallet"]
        except (OSError, ValueError, KeyError):
            return None

    def skill_dir(self, home):
        return home / ".openclaw" / "extensions" / "coinwallet" / "skills" / "coinwallet"


class ClaudeCode:
    def __init__(self, args, number):
        self.model = args.model
        self.session, self.events = None, []
        self.calls, self.tokens, self.cached, self.cost, self.reply = 0, 0, 0, 0.0, ""

    def turn(self, prompt, env, work, timeout):
        argv = [REAL["claude"], "-p", prompt, "--output-format", "stream-json", "--verbose", "--model", self.model,
                "--dangerously-skip-permissions"]
        if self.session:
            argv += ["--resume", self.session]
        stdout, stderr, secs, timed_out = run_turn(argv, env, work, timeout)
        events = json_lines(stdout)
        for event in events:
            if event.get("session_id"):
                self.session = event["session_id"]
            if event.get("type") == "result":
                usage = event.get("usage") or {}
                self.tokens += sum(usage.get(k, 0) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens",
                                                              "cache_creation_input_tokens"))
                self.cached += usage.get("cache_read_input_tokens", 0)
                self.cost += event.get("total_cost_usd") or 0.0
                self.reply = event.get("result") or ""
        self.events += events
        self.calls = len(self.tool_uses(None))
        return events, secs, timed_out, stderr[-2000:]

    def tool_uses(self, home):
        uses = []
        for event in self.events:
            if event.get("type") == "assistant" and not event.get("parent_tool_use_id"):
                for block in (event.get("message") or {}).get("content") or []:
                    if block.get("type") == "tool_use":
                        uses.append({"name": block.get("name"), "input": block.get("input") or {}})
        return uses

    def registered(self, home):
        try:
            return json.loads((home / ".claude.json").read_text())["mcpServers"]["coinwallet"]
        except (OSError, ValueError, KeyError):
            return None

    def skill_dir(self, home):
        found = sorted(home.glob(".claude/plugins/cache/coinsdo/coinwallet/*/skills/coinwallet"))
        return found[-1] if found else home / ".claude" / "plugins" / "missing"


class Codex:
    TOOL_ITEMS = ("command_execution", "mcp_tool_call", "file_change", "web_search", "collab_tool_call")

    def __init__(self, args, number):
        self.model = args.model
        self.session, self.events = None, []
        self.calls, self.tokens, self.cached, self.cost, self.reply = 0, 0, 0, None, ""

    def turn(self, prompt, env, work, timeout):
        flags = ["--json", "--skip-git-repo-check", "--dangerously-bypass-approvals-and-sandbox"]
        if self.model:
            flags += ["-m", self.model]
        argv = [REAL["codex"], "exec"] + (["resume", self.session] if self.session else []) + flags + [prompt]
        # "Selected model is at capacity": the turn failed before the model ran (no tokens). Wait and send the
        # same turn again (at most 4 times); the record counts the retries. Only that error is retried.
        for _ in range(4):
            stdout, stderr, secs, timed_out = run_turn(argv, env, work, timeout)
            if "at capacity" not in stdout or '"turn.completed"' in stdout:
                break
            self.capacity_retries = getattr(self, "capacity_retries", 0) + 1
            time.sleep(45)
        events = json_lines(stdout)
        for event in events:
            if event.get("type") == "thread.started":
                self.session = event.get("thread_id") or self.session
            if event.get("type") == "turn.completed":
                usage = event.get("usage") or {}
                self.tokens += usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                self.cached += usage.get("cached_input_tokens", 0)
            item = event.get("item") or {}
            if event.get("type") == "item.completed" and item.get("type") == "agent_message":
                self.reply = item.get("text") or ""
        self.events += events
        self.calls = len(self.tool_uses(None))
        return events, secs, timed_out, stderr[-2000:]

    def tool_uses(self, home):
        uses = []
        for event in self.events:
            item = event.get("item") or {}
            if event.get("type") == "item.completed" and item.get("type") in self.TOOL_ITEMS:
                uses.append({"name": item.get("type"), "input": {k: item.get(k) for k in ("command", "tool", "arguments",
                                                                                         "changes", "query") if k in item}})
        return uses

    def registered(self, home):
        try:
            import tomllib
        except ImportError:
            return None
        try:
            data = tomllib.loads((home / ".codex" / "config.toml").read_text())
            return data["mcp_servers"]["coinwallet"]
        except (OSError, ValueError, KeyError):
            return None

    def skill_dir(self, home):
        found = sorted(home.glob(".codex/plugins/cache/coinsdo/coinwallet/*/skills/coinwallet"))
        return found[-1] if found else home / ".codex" / "plugins" / "missing"


HOSTS = {"openclaw": OpenClaw, "claude-code": ClaudeCode, "codex": Codex}


def skill_files(use):
    """Skill files a tool call read: a read tool's path, or a shell command naming a card (not running mcp.py)."""
    name, data = (use.get("name") or "").lower(), use.get("input") or {}
    text = json.dumps(data)
    found = []
    for match in SKILL_PATH.findall(text):
        if not match.endswith(".py") or name in ("read", "read_file"):
            found.append(match)
    return found


def check_setup(driver, host, home, env, reply):
    skill = driver.skill_dir(home)
    checks = {
        "skill_installed": (skill / "SKILL.md").is_file() and (skill / "references" / "cards" / "setup.md").is_file(),
        "mcp_binary": any(home.rglob("coinsdo-wallet-mcp/coinwallet/service")),
    }
    entry = driver.registered(home)
    ok, why = probe_entry(entry, env) if entry else (False, "no coinwallet MCP server in the Host config")
    checks["mcp_registered_and_answers"] = ok
    checks["mcp_detail"] = why
    checks["replied"] = bool(reply.strip())
    if host in ("claude-code", "codex"):
        checks["says_new_chat"] = "new chat" in reply.lower()
    passed = all(v for k, v in checks.items() if k != "mcp_detail")
    return passed, checks


def auth_digest():
    path = REAL_HOME / ".codex" / "auth.json"
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


INSTALL = {
    "claude-code": lambda t: [[REAL["claude"], "plugin", "install", "coinwallet", "--marketplace", t]],
    "codex": lambda t: [[REAL["codex"], "plugin", "marketplace", "add", t], [REAL["codex"], "plugin", "add", "coinwallet@coinsdo"]],
    "openclaw": lambda t: [[REAL["openclaw"], "plugins", "install", "coinwallet", "--marketplace", t, "--force",
                            "--accept-capabilities"]],
}


def preinstall(host, driver, env, work, target, url, policy, hide, mcp_log, fail=()):
    """Skill installed with the README command and the `coinwallet` MCP server registered (as dev/mcp_proxy.py), as
    after a finished setup. Neither step counts toward the run."""
    out = ""
    for argv in INSTALL[host](target):
        run = subprocess.run(argv, env=env, cwd=str(work), capture_output=True, text=True, timeout=300,
                             stdin=subprocess.DEVNULL)
        out += run.stdout[-1500:] + run.stderr[-1500:]
    home = Path(env["HOME"])
    if not (driver.skill_dir(home) / "SKILL.md").is_file():
        raise SystemExit("skill install failed:\n" + out)
    proxy = [str(PROXY), "--url", url, "--policy", policy, "--log", str(mcp_log)]
    for wallet_id in hide:
        proxy += ["--hide-wallet", str(wallet_id)]
    for tool in fail:
        proxy += ["--fail-tool", tool]
    service_stub(env["HOME"])
    entry = {"command": sys.executable, "args": proxy}
    if host == "claude-code":
        argv = [REAL["claude"], "mcp", "add-json", "--scope", "user", "coinwallet",
                json.dumps(dict({"type": "stdio"}, **entry))]
    elif host == "codex":
        argv = [REAL["codex"], "mcp", "add", "coinwallet", "--", sys.executable] + proxy
    else:
        argv = [REAL["openclaw"], "mcp", "set", "coinwallet", json.dumps(entry)]
    run = subprocess.run(argv, env=env, cwd=str(work), capture_output=True, text=True, timeout=120,
                         stdin=subprocess.DEVNULL)
    if run.returncode or not driver.registered(home):
        raise SystemExit("register failed: " + run.stdout[-1500:] + run.stderr[-1500:])


SHELL_TOOLS = {"bash", "exec", "shell", "command_execution", "exec_command", "process", "terminal"}
ROGUE_HINTS = ("curl", "wget", "sqlite", "lsof", "ps ", "mcp_proxy", "127.0.0.1", "localhost", "service -t",
               "http", "python3 -c", "python -c", "nc ")


def normalized(use):
    """(name, input) in the Hermes names the checks know: a shell call -> terminal, except one that only reads skill
    files (Codex and OpenClaw read cards with cat/sed); a question tool -> ask_user."""
    name, data = use.get("name") or "", use.get("input") or {}
    low = name.lower()
    if low in SHELL_TOOLS:
        text = json.dumps(data)
        skill_dir = "coinwallet" in text and any(d in text for d in ("skills/", "plugins/", "extensions/", ".codex",
                                                                         ".openclaw", ".claude"))
        if skill_dir and "mcp.py" not in text and not any(h in text for h in ROGUE_HINTS):
            return "read_skill", data
        if str(data.get("command", "")).strip() in ("true", ":"):  # Claude Code's no-op Bash call
            return "noop", data
        return "terminal", data
    if low in ("askuserquestion", "ask_user", "request_user_input", "question"):
        return "ask_user", data
    return name, data


def case_run(args, number, base, services):
    """A case after setup: same fixture, turns, human steps and checks as dev/hermes_runner.py."""
    case = CASES[args.case]
    fixture = case["fixture"]
    user = "cwr-" + time.strftime("%Y%m%d%H%M%S") + "-" + str(number)
    target = str(ROOT) if args.source == "local" else args.repo
    run_dir, home, bin_dir, work = make_run_dir(base, args.host, target)
    env = run_env(args.host, home, bin_dir, user)
    driver = HOSTS[args.host](args, number)
    values = dict(case.get("values", {}))
    values.update(dict(item.split("=", 1) for item in (args.set or [])))
    mcp_log = run_dir / "mcp.jsonl"
    if fixture == "newbie":
        newbie_service(base, number, services)
    url = args.agenttest_url if fixture == "agenttest" else services[fixture].url
    policy = case.get("policy") or ("own" if fixture == "own" else "read")
    preinstall(args.host, driver, env, work, target, url, policy, case.get("hide", []), mcp_log, case.get("fail", []))
    truth = read_truth(url, "all" if case.get("balances") else ())
    if case.get("hide"):
        truth["wallets"] = [w for w in truth["wallets"] if w["walletId"] not in case["hide"]]
    turns = list(case["turns"]) + list(args.reply or [])
    events, secs, timed_out, replies, marks, sent, settled, errors = [], 0.0, False, [], [], [], [], ""
    for turn in turns:
        if isinstance(turn, dict):
            if "hook" in turn:
                values.update(HOOKS[turn["hook"]](values, url))
            elif "settle" in turn:
                settled[:] = wait_settled(url, read_log(mcp_log), turn["settle"])
            elif "ask" in turn:
                values[turn["key"]] = values.get(turn["key"]) or human_value(turn["ask"])
            else:
                human_value(turn["wait"])
            continue
        prompt = turn.format(**values)
        sent.append(prompt if "{code}" not in turn else turn)
        driver.reply = ""
        events_turn, turn_secs, turn_timeout, stderr = driver.turn(prompt, env, work, args.timeout)
        events += events_turn
        secs += turn_secs
        errors += stderr
        timed_out = timed_out or turn_timeout
        replies.append(driver.reply)
        marks.append(len(read_log(mcp_log)))
        if turn_timeout:
            break
    (run_dir / "events.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    (run_dir / "stderr.txt").write_text(errors[-20000:], encoding="utf-8")
    uses = driver.tool_uses(home)
    (run_dir / "tool_uses.jsonl").write_text("\n".join(json.dumps(u) for u in uses) + "\n", encoding="utf-8")
    files = []
    for use in uses:
        for path in skill_files(use):
            if path not in files:
                files.append(path)
    mcp = read_log(mcp_log)
    ctx = {"card": case.get("card"), "lang": case.get("lang"), "mcp": mcp,
           "mcp_by_turn": [mcp[(marks[i - 1] if i else 0):m] for i, m in enumerate(marks)],
           "replies": replies, "truth": truth, "values": values, "files": files, "prompts": sent,
           "tool_inputs": [normalized(u) for u in uses], "db_tool_calls": [],
           "truth_after": read_truth(url) if fixture == "own" else {}, "settled": settled,
           "sent_bundles": sent_bundles(mcp), "state": {}}
    try:
        checks = case["check"](ctx)
    except Exception as exc:  # noqa: BLE001 - a broken fixture or reply shape is a failed run, not a crash
        checks = {"check_crashed: " + repr(exc)[:200]: False}
    passed = all(checks.values())
    calls = driver.calls if args.host == "openclaw" else len(uses)
    budget = case.get("budget", {})
    account = "agenttest (read tools only)" if fixture == "agenttest" else services[fixture].user
    record = {
        "case": args.case, "host": args.host, "model": args.model or "codex default", "source": args.source,
        "run": number, "ok": bool(passed) and not timed_out, "checks": checks, "timed_out": timed_out,
        "calls": calls, "mcp_calls": [e["tool"] for e in mcp], "secs": round(secs, 1), "tokens": driver.tokens,
        "tokens_uncached": driver.tokens - driver.cached,
        "cost_usd": round(driver.cost, 5) if driver.cost is not None else None,
        "skill_files_read": files, "tools": [u.get("name") for u in uses],
        "prompts": sent, "replies": [r[:600] for r in replies], "reply": (replies[-1] if replies else "")[:600],
        "budget": budget,
        "within_budget": bool(budget) and calls <= budget["calls"] and secs <= budget["secs"]
        and driver.tokens <= budget["tokens"],
        "session": getattr(driver, "session", None), "transcript": str(run_dir / "events.jsonl"),
        "mcp_log": str(mcp_log), "service_account": account, "date": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "provider_retries": getattr(driver, "capacity_retries", 0),
    }
    if fixture == "newbie":
        services["newbie"].stop()
    return record, run_dir


def one_run(args, number, base):
    user = "cwr-" + time.strftime("%Y%m%d%H%M%S") + "-" + str(number)
    target = str(ROOT) if args.source == "local" else args.repo
    run_dir, home, bin_dir, work = make_run_dir(base, args.host, target)
    env = run_env(args.host, home, bin_dir, user)
    driver = HOSTS[args.host](args, number)
    source = str(ROOT / "README.md") if args.source == "local" else "https://github.com/" + args.repo
    prompts = [p.format(source=source) for p in CASES[args.case]["turns"]] + list(args.reply or [])
    events, secs, timed_out, errors = [], 0.0, False, ""
    for prompt in prompts:
        turn, turn_secs, turn_timeout, stderr = driver.turn(prompt, env, work, args.timeout)
        events += turn
        secs += turn_secs
        errors = stderr
        timed_out = timed_out or turn_timeout
        if turn_timeout:
            break
    (run_dir / "events.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    (run_dir / "stderr.txt").write_text(errors, encoding="utf-8")
    uses = driver.tool_uses(home)
    (run_dir / "tool_uses.jsonl").write_text("\n".join(json.dumps(u) for u in uses) + "\n", encoding="utf-8")
    files = []
    for use in uses:
        for path in skill_files(use):
            if path not in files:
                files.append(path)
    passed, checks = check_setup(driver, args.host, home, env, driver.reply) if args.case == "setup" else (None, {})
    calls = driver.calls if args.host == "openclaw" else len(uses)
    budget = CASES[args.case].get("budget", {})
    record = {
        "case": args.case, "host": args.host, "model": args.model or "codex default", "source": args.source,
        "run": number, "ok": bool(passed) and not timed_out, "checks": checks, "timed_out": timed_out,
        "calls": calls, "secs": round(secs, 1), "tokens": driver.tokens,
        "tokens_uncached": driver.tokens - driver.cached,
        "cost_usd": round(driver.cost, 5) if driver.cost is not None else None,
        "skill_files_read": files, "tools": [u.get("name") for u in uses],
        "reply": driver.reply[:600], "budget": budget,
        "within_budget": bool(budget) and calls <= budget["calls"] and secs <= budget["secs"]
        and driver.tokens <= budget["tokens"],
        "session": getattr(driver, "session", None), "transcript": str(run_dir / "events.jsonl"),
        "service_account": user, "date": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    return record, run_dir


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", choices=sorted(HOSTS), required=True)
    parser.add_argument("--case", choices=sorted(c for c in CASES if CASES[c]["fixture"] != "seeded"), default="setup")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--model", help="default: openclaw deepseek/deepseek-v4-flash, claude-code sonnet, codex its own")
    parser.add_argument("--source", choices=("github", "local"), default="github")
    parser.add_argument("--repo", default="mackendell/agentic-wallet")
    parser.add_argument("--reply", action="append", help="fixed scripted reply for the next turn (repeatable)")
    parser.add_argument("--set", action="append", help="KEY=VALUE for the case's turns, e.g. wallet=my-test")
    parser.add_argument("--agenttest-url", default=AGENTTEST_URL)
    parser.add_argument("--own-home", default=str(REAL_HOME / ".cache" / "coinwallet-dev" / "own"))
    parser.add_argument("--own-user", default="cwr-own")
    parser.add_argument("--own-url", help="an already running throwaway service (--own-user's) for the 'own' fixture")
    parser.add_argument("--wait-file", help="wait for this file instead of Enter at human steps (its text = the value)")
    parser.add_argument("--timeout", type=int, default=600, help="seconds per turn before the run is killed")
    parser.add_argument("--out", help="append JSON lines here (default: stdout only)")
    parser.add_argument("--workdir", help="where run folders go (default: a temp folder); kept for transcripts")
    args = parser.parse_args()
    args.model = args.model or DEFAULT_MODEL[args.host]
    hermes_runner.WAIT_FILE = args.wait_file
    if not args.own_user.startswith("cwr-"):
        raise SystemExit("--own-user must be a throwaway account starting with cwr-")
    base = Path(args.workdir or tempfile.mkdtemp(prefix="host-runner-"))
    base.mkdir(parents=True, exist_ok=True)
    before = auth_digest() if args.host == "codex" else None
    fixture = CASES[args.case]["fixture"]
    services = {}
    if fixture == "fresh":
        services["fresh"] = ThrowawayService(base / "fresh-service", "cwr-fresh-" + time.strftime("%Y%m%d%H%M%S"))
    elif fixture == "own" and args.own_url:
        services["own"] = RunningService(args.own_url, args.own_user)
    elif fixture == "own":
        services["own"] = ThrowawayService(args.own_home, args.own_user)
    for service in services.values():
        service.start()
    try:
        run_all(args, base, before, services)
    finally:
        for service in services.values():
            service.stop()


def run_all(args, base, before, services):
    for number in range(1, args.runs + 1):
        try:
            if args.case == "setup":
                record, _ = one_run(args, number, str(base))
            else:
                record, _ = case_run(args, number, str(base), services)
        except NeedsHuman as need:
            record = {"case": args.case, "host": args.host, "run": number, "ok": None, "needs_human": str(need)}
        if args.host == "codex":
            record["real_codex_auth_unchanged"] = auth_digest() == before
        line = json.dumps(record, ensure_ascii=False)
        print(line, flush=True)
        if args.out:
            with open(args.out, "a", encoding="utf-8") as stream:
                stream.write(line + "\n")


if __name__ == "__main__":
    main()
