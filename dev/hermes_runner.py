#!/usr/bin/env python3
"""Seam 1 on Hermes: run a Test plan case headless, N times, one JSON line per run.

Usage:
  python3 dev/hermes_runner.py --case setup --runs 3 --out runs.jsonl
  python3 dev/hermes_runner.py --case setup --source local    # before a push: skill from this checkout
  python3 dev/hermes_runner.py --case update --source local   # "Update CoinWallet" + "yes" on a seeded older install

Each run gets a fresh throwaway HOME with a fresh ~/.hermes in it (only the OpenRouter key and a model line).
macOS: that HOME gets a symlink to the real ~/Library/Keychains (a HOME without it makes macOS offer to reset
the login keychain) and the MCP service runs under a throwaway account (COINWALLET_TEST_USER=cwr-...), so the
real keychain items are never used. Each macOS run leaves one test keychain item (empty test wallet).

--source github: the agent gets the README sentence with the repo swapped to --repo (default
  mackendell/agentic-wallet); `hermes skills install CoinsDo/agentic-wallet/...` is redirected to --repo.
--source local: the agent gets "Install the CoinWallet skill from <this checkout>/README.md"; `hermes skills install
  */agentic-wallet/skills/coinwallet` installs this checkout through Hermes' real install code
  (dev/hermes_local_install.py: same quarantine, scan and install path, only the GitHub fetch replaced).

Turns after the first are fixed scripted replies, sent by resuming the same session
(`hermes chat --oneshot --format stream-json --resume <id>`). Never rely on one-shot `clarify`: it auto-answers.

Record: case, host, model, source, run, ok, checks, calls, secs, tokens (+ non-cached), cost, skill files read,
tools used, reply (short), budget and within_budget.
"""
import argparse
import json
import os
import re
import selectors
import shlex
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REAL_HOME = Path.home()
IS_MAC = sys.platform == "darwin"
HERMES = shutil.which("hermes") or str(REAL_HOME / ".local" / "bin" / "hermes")
HERMES_AGENT = Path(os.environ.get("HERMES_AGENT_DIR", str(REAL_HOME / ".hermes" / "hermes-agent")))
HERMES_PY = HERMES_AGENT / "venv" / "bin" / "python"

# Task budget, worst of 3 runs on DeepSeek Flash (spec #29).
BUDGETS = {"setup": {"calls": 10, "secs": 180, "tokens": 150_000}}

CASES = {
    "setup": {
        "prompts": ["Install the CoinWallet skill from {source}"],
    },
    # Seeded: an older skill (VERSION 0.0.1, tested MCP v1.0.7) and MCP v1.0.7 registered in Hermes.
    "update": {
        "prompts": ["Update CoinWallet", "yes"],
    },
}


def openrouter_key():
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key
    env_file = REAL_HOME / ".hermes" / ".env"
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("OPENROUTER_API_KEY="):
            return line.split("=", 1)[1].strip().strip("'\"")
    raise SystemExit("No OPENROUTER_API_KEY in the environment or ~/.hermes/.env")


def make_run_dir(base, model, source, repo):
    run = Path(tempfile.mkdtemp(prefix="hermes-run-", dir=base))
    # Fresh empty home with Hermes at its default place (~/.hermes), like a Newbie's machine.
    home, bin_dir, work = run / "home", run / "bin", run / "work"
    hermes_home = home / ".hermes"
    for d in (home, hermes_home, bin_dir, work):
        d.mkdir()
    if IS_MAC:
        (home / "Library").mkdir()
        os.symlink(str(REAL_HOME / "Library" / "Keychains"), str(home / "Library" / "Keychains"))
    env_file = hermes_home / ".env"
    env_file.write_text("OPENROUTER_API_KEY=" + openrouter_key() + "\n", encoding="utf-8")
    os.chmod(str(env_file), 0o600)
    (hermes_home / "config.yaml").write_text(
        "model:\n  default: " + model + "\n  provider: openrouter\n  base_url: https://openrouter.ai/api/v1\n",
        encoding="utf-8")
    # `hermes` shim: redirect the skill install to the repo under test, pass everything else through.
    if source == "local":
        install = (shlex.quote(str(HERMES_PY)) + " " + shlex.quote(str(ROOT / "dev" / "hermes_local_install.py"))
                   + " " + shlex.quote(str(ROOT)) + ' "$@"')
    else:
        install = shlex.quote(HERMES) + ' skills install "$(echo "$3" | sed "s#^[^/]*/agentic-wallet/#' + repo + '/#")" ' + '"${@:4}"'
    shim = bin_dir / "hermes"
    # local: `hermes skills update coinwallet` also reads this checkout (same patched GitHub fetch).
    update = ""
    if source == "local":
        update = ('if [ "$1" = skills ] && [ "$2" = update ]; then\n  exec ' + shlex.quote(str(HERMES_PY)) + " "
                  + shlex.quote(str(ROOT / "dev" / "hermes_local_install.py")) + " " + shlex.quote(str(ROOT))
                  + ' "$@"\nfi\n')
    shim.write_text(
        "#!/bin/bash\n"
        'if [ "$1" = skills ] && [ "$2" = install ] && [[ "$3" == */agentic-wallet/skills/coinwallet* ]]; then\n'
        "  exec " + install + "\n"
        "fi\n" + update +
        "exec " + shlex.quote(HERMES) + ' "$@"\n', encoding="utf-8")
    os.chmod(str(shim), 0o755)
    return run, home, hermes_home, bin_dir, work


def run_env(home, hermes_home, bin_dir, user):
    env = {
        "PATH": str(bin_dir) + os.pathsep + os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "USER": os.environ.get("USER", ""),
        "LANG": os.environ.get("LANG", "en_US.UTF-8"),
        "TERM": "dumb",
        "COINWALLET_TEST_USER": user,
    }
    assert not IS_MAC or (home / "Library" / "Keychains").exists()
    return env


def hermes_turn(prompt, env, work, model, session, timeout):
    argv = [HERMES, "chat", "-q", prompt, "--oneshot", "--format", "stream-json", "-m", model, "--provider", "openrouter"]
    if session:
        argv += ["--resume", session]
    started = time.monotonic()
    try:
        proc = subprocess.run(argv, env=env, cwd=str(work), capture_output=True, text=True, timeout=timeout)
        stdout, timed_out = proc.stdout, False
    except subprocess.TimeoutExpired as exc:
        stdout, timed_out = (exc.stdout or b"").decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or ""), True
    secs = time.monotonic() - started
    events = []
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                events.append(json.loads(line))
            except ValueError:
                pass
    return events, secs, timed_out


SKILL_PATH = re.compile(r"skills/coinwallet/((?:SKILL\.md|references/[\w./-]+\.md|scripts/mcp\.py))")


def skill_files(event):
    """Skill files a tool call read: skill_view, read_file, or a terminal command naming the file."""
    name, data = event.get("name", ""), event.get("input") or {}
    found = []
    if name == "skill_view" and str(data.get("name", "")).endswith("coinwallet"):
        found.append(data.get("file_path") or data.get("path") or "SKILL.md")
    elif name in ("read_file", "terminal", "execute_code", "search_files"):
        text = json.dumps(data)
        for match in SKILL_PATH.findall(text):
            if not match.endswith(".py") or name == "read_file":
                found.append(match)
    return found


def probe_registered(hermes_home, home, env):
    """Start the service the way Hermes would (registered command, Hermes' env filter) and call get_wallets."""
    dump = subprocess.run([str(HERMES_PY), "-c", "import json, sys, yaml; print(json.dumps(yaml.safe_load(open(sys.argv[1]))))",
                           str(hermes_home / "config.yaml")], capture_output=True, text=True)
    try:
        entry = (json.loads(dump.stdout) or {}).get("mcp_servers", {}).get("coinwallet")
    except ValueError:
        entry = None
    if not entry:
        return False, "no mcp_servers.coinwallet in Hermes config"
    return probe_entry(entry, env)


def probe_entry(entry, env):
    """Start a registered MCP entry ({command, args, env}) with a Host-style small env and call get_wallets."""
    child_env = {k: env[k] for k in ("PATH", "HOME", "USER", "LANG") if env.get(k)}
    child_env.update(entry.get("env") or {})
    try:
        proc = subprocess.Popen([entry["command"]] + list(entry.get("args", [])), stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=child_env)
    except OSError as exc:
        return False, "registered command does not start: " + str(exc)
    sel = selectors.DefaultSelector()
    sel.register(proc.stdout, selectors.EVENT_READ)
    buffer = b""

    def ask(msg_id, method, params):
        nonlocal buffer
        proc.stdin.write((json.dumps({"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params}) + "\n").encode())
        proc.stdin.flush()
        end = time.monotonic() + 60
        while time.monotonic() < end:
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                if msg.get("id") == msg_id:
                    return msg
            if not sel.select(end - time.monotonic()):
                break
            chunk = os.read(proc.stdout.fileno(), 65536)
            if not chunk:
                return {"error": proc.stderr.read().decode("utf-8", "replace")[-300:]}
            buffer += chunk
        return {"error": "timeout"}

    try:
        ask(1, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "runner", "version": "1"}})
        proc.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
        proc.stdin.flush()
        for attempt in range(30):
            reply = ask(2 + attempt, "tools/call", {"name": "get_wallets", "arguments": {}})
            result = reply.get("result") or {}
            if result and not result.get("isError"):
                return True, "get_wallets answered"
            if "uninitialized" not in json.dumps(reply):
                return False, "get_wallets failed: " + json.dumps(reply)[:300]
            time.sleep(1)
        return False, "service stayed uninitialized"
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def check_setup(hermes_home, home, env, reply):
    skill = hermes_home / "skills" / "coinwallet"
    checks = {
        "skill_installed": (skill / "SKILL.md").is_file() and (skill / "references" / "cards" / "setup.md").is_file(),
        "mcp_binary": any(home.rglob("coinsdo-wallet-mcp/coinwallet/service")),
    }
    ok, why = probe_registered(hermes_home, home, env)
    checks["mcp_registered_and_answers"] = ok
    checks["mcp_detail"] = why
    checks["replied"] = bool(reply.strip())
    passed = all(v for k, v in checks.items() if k != "mcp_detail")
    return passed, checks


def data_dir(home):
    if IS_MAC:
        return home / "Library" / "Application Support" / "coinsdo-wallet-mcp"
    return home / ".config" / "coinsdo-wallet-mcp"


def service_version(binary):
    run = subprocess.run([str(binary), "-v"], capture_output=True, text=True)
    match = re.search(r"v\d+\.\d+\.\d+", run.stdout + run.stderr)
    return match.group(0) if match else None


def seed_update(run_dir, home, hermes_home, env, user, source, repo):
    """An older install: the skill with VERSION 0.0.1 and only MCP v1.0.7 tested, MCP v1.0.7 placed and registered.
    The registered copy runs as account <user>-host; mcp.py upgrade runs as <user>. On macOS that keeps every
    keychain item first-made (silent): v1.0.8 never opens an item v1.0.7 made, which would show a popup."""
    sys.path.insert(0, str(ROOT / "tests"))
    from test_mcp_cli import HASHES, asset, cached_asset
    old = run_dir / "old-repo"
    shutil.copytree(str(ROOT / "skills" / "coinwallet"), str(old / "skills" / "coinwallet"))
    (old / "skills" / "coinwallet" / "VERSION").write_text("0.0.1\n")
    (old / "skills" / "coinwallet" / "mcp-tested.json").write_text(json.dumps(
        {"minimum": "v1.0.7", "tested": {"v1.0.7": HASHES["v1.0.7"]}, "no_fallback": []}))
    identifier = ("CoinsDo" if source == "local" else repo.split("/")[0]) + "/agentic-wallet/skills/coinwallet"
    install = subprocess.run([str(HERMES_PY), str(ROOT / "dev" / "hermes_local_install.py"), str(old), "skills",
                              "install", identifier, "--yes"], env=env, capture_output=True, text=True)
    if install.returncode or not (hermes_home / "skills" / "coinwallet" / "VERSION").is_file():
        raise SystemExit("seeding the old skill failed: " + install.stdout[-500:] + install.stderr[-500:])
    binary = data_dir(home) / "coinwallet" / "service"
    binary.parent.mkdir(parents=True)
    shutil.copyfile(str(cached_asset("v1.0.7")), str(binary))
    os.chmod(str(binary), 0o755)
    assert asset() in HASHES["v1.0.7"]
    entry = {"command": str(binary), "args": ["-t", "stdio", "-e", "prod", "-u", user + "-host"]}
    if not IS_MAC and not Path("/etc/machine-id").is_file():
        key = data_dir(home) / "master.key"
        key.write_bytes(os.urandom(32))
        os.chmod(str(key), 0o600)
        entry["env"] = {"COINSDO_MASTER_KEY_FILE": str(key)}
    subprocess.run([HERMES, "config", "set", "mcp_servers.coinwallet", json.dumps(entry)], env=env,
                   capture_output=True, text=True, check=True)
    return binary


def check_update(home, hermes_home, env, binary, before_yes, replies):
    skill = hermes_home / "skills" / "coinwallet"
    backups = sorted((data_dir(home) / "backups").glob("*/coinwallet/service"))
    check = subprocess.run([sys.executable, str(skill / "scripts" / "mcp.py"), "check"], env=env,
                           capture_output=True, text=True, timeout=300)
    checks = {
        "nothing_changed_before_yes": before_yes == ("v1.0.7", "0.0.1"),
        "asked_first": "?" in (replies[0] if replies else ""),
        "skill_updated": (skill / "VERSION").read_text().strip() == (ROOT / "skills" / "coinwallet" / "VERSION").read_text().strip(),
        "mcp_upgraded": service_version(binary) == "v1.0.8",
        "backup_before_upgrade": any(service_version(path) == "v1.0.7" for path in backups),
        "mcp_check_ok": "result: ok" in check.stdout,
        "says_new_chat": "new chat" in (replies[-1] if replies else "").lower(),
    }
    if IS_MAC:
        checks["keychain_warning"] = "always allow" in (replies[0] if replies else "").lower()
    return all(checks.values()), checks


def session_cost(hermes_home, session):
    try:
        db = sqlite3.connect(str(hermes_home / "state.db"))
        row = db.execute("select estimated_cost_usd, tool_call_count, api_call_count from sessions where id = ?",
                         (session,)).fetchone()
        db.close()
        return row
    except sqlite3.Error:
        return None


def one_run(args, number, base):
    user = "cwr-" + time.strftime("%Y%m%d%H%M%S") + "-" + str(number)
    run_dir, home, hermes_home, bin_dir, work = make_run_dir(base, args.model, args.source, args.repo)
    env = run_env(home, hermes_home, bin_dir, user)
    # local: the README file stands in for the GitHub landing page (which shows the README).
    source = str(ROOT / "README.md") if args.source == "local" else "https://github.com/" + args.repo
    prompts = [p.format(source=source) for p in CASES[args.case]["prompts"]] + list(args.reply or [])
    binary = seed_update(run_dir, home, hermes_home, env, user, args.source, args.repo) if args.case == "update" else None
    session, events, secs, timed_out, replies, before_yes = None, [], 0.0, False, [], None
    for prompt in prompts:
        turn, turn_secs, turn_timeout = hermes_turn(prompt, env, work, args.model, session, args.timeout)
        events += turn
        secs += turn_secs
        timed_out = timed_out or turn_timeout
        for event in turn:
            if event.get("session_id"):
                session = event["session_id"]
        replies.append(next((e.get("text", "") for e in reversed(turn) if e.get("type") == "result"), ""))
        if binary and before_yes is None:
            before_yes = (service_version(binary), (hermes_home / "skills" / "coinwallet" / "VERSION").read_text().strip())
        if turn_timeout:
            break
    (run_dir / "events.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    tool_uses = [e for e in events if e.get("type") == "tool_use"]
    results = [e for e in events if e.get("type") == "result"]
    tokens = {k: sum((r.get("tokens") or {}).get(k, 0) for r in results) for k in ("input", "output", "total", "cache_read")}
    reply = results[-1].get("text", "") if results else ""
    files = []
    for event in tool_uses:
        for path in skill_files(event):
            if path not in files:
                files.append(path)
    if args.case == "setup":
        passed, checks = check_setup(hermes_home, home, env, reply)
    else:
        passed, checks = check_update(home, hermes_home, env, binary, before_yes, replies)
    cost_row = session_cost(hermes_home, session) if session else None
    budget = BUDGETS.get(args.case, {})
    record = {
        "case": args.case, "host": "hermes", "model": args.model, "source": args.source, "run": number,
        "ok": bool(passed) and not timed_out, "checks": checks, "timed_out": timed_out,
        "calls": len(tool_uses), "secs": round(secs, 1), "tokens": tokens["total"],
        "tokens_uncached": tokens["total"] - tokens["cache_read"],
        "cost_usd": round(cost_row[0], 5) if cost_row and cost_row[0] is not None else None,
        "api_calls": cost_row[2] if cost_row else None,
        "skill_files_read": files, "tools": [e.get("name") for e in tool_uses],
        "reply": reply[:600], "replies": [r[:600] for r in replies] if len(replies) > 1 else None, "budget": budget,
        "within_budget": bool(budget) and len(tool_uses) <= budget["calls"] and secs <= budget["secs"]
        and tokens["total"] <= budget["tokens"],
        "session": session, "transcript": str(run_dir / "events.jsonl"), "service_account": user,
        "date": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    return record, run_dir


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--case", choices=sorted(CASES), default="setup")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--model", default="deepseek/deepseek-v4-flash")
    parser.add_argument("--source", choices=("github", "local"), default="github")
    parser.add_argument("--repo", default="mackendell/agentic-wallet")
    parser.add_argument("--reply", action="append", help="fixed scripted reply for the next turn (repeatable)")
    parser.add_argument("--timeout", type=int, default=600, help="seconds per turn before the run is killed")
    parser.add_argument("--out", help="append JSON lines here (default: stdout only)")
    parser.add_argument("--workdir", help="where run folders go (default: a temp folder); kept for transcripts")
    args = parser.parse_args()
    base = Path(args.workdir or tempfile.mkdtemp(prefix="hermes-runner-"))
    base.mkdir(parents=True, exist_ok=True)
    for number in range(1, args.runs + 1):
        record, _ = one_run(args, number, str(base))
        line = json.dumps(record, ensure_ascii=False)
        print(line, flush=True)
        if args.out:
            with open(args.out, "a", encoding="utf-8") as stream:
                stream.write(line + "\n")


if __name__ == "__main__":
    main()
