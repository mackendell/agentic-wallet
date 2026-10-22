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

Cases after setup (dev/test_cases.py) start as after a finished setup: the skill installed (--source) and the
`coinwallet` MCP server registered as dev/mcp_proxy.py, which logs every tool call and enforces the fixture's policy:
  fresh      a throwaway HTTP service, new -u account per invocation, 0 wallets, read tools only
  agenttest  the running `-e prod -u agenttest` HTTP service (--agenttest-url), read tools only
  own        a throwaway HTTP service kept in --own-home/--own-user for Rooms made in the App; join + add_address
Human steps (make a Room, finish it in the App) wait for Enter, or for --wait-file to appear (its text = the value).
  python3 dev/hermes_runner.py --case join --runs 1 --source local --set code=9F3A0C --wait-file /tmp/w
  python3 dev/hermes_runner.py --case add-address --source local --set wallet=<name of an ONLINE own wallet>

Note: `--oneshot` makes Hermes use its weaker one-shot skill guidance ("load a skill only when it carries domain
knowledge you lack"), so skill loading is harder here than in a real chat, and Hermes shows only the first 57
characters of the skill description.

Record: case, host, model, source, run, ok, checks, calls (Host tool calls), mcp_calls, secs, tokens
(+ non-cached), cost, skill files read, tools used, prompts, replies, budget and within_budget.
"""
import argparse
import json
import os
import re
import selectors
import shlex
import shutil
import socket
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

sys.path.insert(0, str(ROOT / "dev"))
from mcp_proxy import HttpMcp  # noqa: E402
from test_cases import CASES, HOOKS  # noqa: E402

PROXY = ROOT / "dev" / "mcp_proxy.py"
AGENTTEST_URL = "http://127.0.0.1:18534/mcp"  # the read-only fixture service (-u cwr-fix34, HTTP), read tools only


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
    except (BrokenPipeError, OSError):  # the registered service exited at once
        return False, "registered service exited: " + proc.stderr.read().decode("utf-8", "replace")[-300:]
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


SEED_OLD = "v1.0.8"  # the previous tested MCP: what a user who installed before this release runs


def seed_update(run_dir, home, hermes_home, env, user, source, repo):
    """An older install: the skill with VERSION 0.0.1 and only MCP SEED_OLD tested, MCP SEED_OLD placed and registered.
    Default: the registered copy runs as account <user>-host and mcp.py upgrade as <user>, so on macOS every keychain
    item is first-made (silent). SEED_SAME_ACCOUNT=1: one account, and SEED_OLD starts once before the agent, so the
    upgraded service opens an item the old one made: the real user's path, with the one-time "Always Allow" popup."""
    sys.path.insert(0, str(ROOT / "tests"))
    from test_mcp_cli import HASHES, asset, cached_asset
    old = run_dir / "old-repo"
    shutil.copytree(str(ROOT / "skills" / "coinwallet"), str(old / "skills" / "coinwallet"))
    (old / "skills" / "coinwallet" / "VERSION").write_text("0.0.1\n")
    (old / "skills" / "coinwallet" / "mcp-tested.json").write_text(json.dumps(
        {"minimum": SEED_OLD, "tested": {SEED_OLD: HASHES[SEED_OLD]}, "no_fallback": []}))
    identifier = ("CoinsDo" if source == "local" else repo.split("/")[0]) + "/agentic-wallet/skills/coinwallet"
    install = subprocess.run([str(HERMES_PY), str(ROOT / "dev" / "hermes_local_install.py"), str(old), "skills",
                              "install", identifier, "--yes"], env=env, capture_output=True, text=True)
    if install.returncode or not (hermes_home / "skills" / "coinwallet" / "VERSION").is_file():
        raise SystemExit("seeding the old skill failed: " + install.stdout[-500:] + install.stderr[-500:])
    binary = data_dir(home) / "coinwallet" / "service"
    binary.parent.mkdir(parents=True)
    shutil.copyfile(str(cached_asset(SEED_OLD)), str(binary))
    os.chmod(str(binary), 0o755)
    assert asset() in HASHES[SEED_OLD]
    same = os.environ.get("SEED_SAME_ACCOUNT") == "1"
    entry = {"command": str(binary), "args": ["-t", "stdio", "-e", "prod", "-u", user if same else user + "-host"]}
    if same:  # the old service runs once under the user's account, as on the user's machine before the update
        subprocess.run([sys.executable, str(old / "skills" / "coinwallet" / "scripts" / "mcp.py"), "check"], env=env,
                       capture_output=True, text=True, timeout=300)
    if not IS_MAC and not Path("/etc/machine-id").is_file():
        key = data_dir(home) / "master.key"
        key.write_bytes(os.urandom(32))
        os.chmod(str(key), 0o600)
        entry["env"] = {"COINSDO_MASTER_KEY_FILE": str(key)}
    subprocess.run([HERMES, "config", "set", "mcp_servers.coinwallet", json.dumps(entry)], env=env,
                   capture_output=True, text=True, check=True)
    return binary


def update_state(home, hermes_home, env, binary, before_yes, skill=None):
    """What the update case's check needs (test_cases.check_update): versions before the "yes" and now."""
    skill = skill or hermes_home / "skills" / "coinwallet"
    backups = sorted((data_dir(home) / "backups").glob("*/coinwallet/service"))
    check = subprocess.run([sys.executable, str(skill / "scripts" / "mcp.py"), "check"], env=env,
                           capture_output=True, text=True, timeout=300)
    return {
        "before_yes": before_yes, "is_mac": IS_MAC,
        "skill_version": (skill / "VERSION").read_text().strip(),
        "repo_skill_version": (ROOT / "skills" / "coinwallet" / "VERSION").read_text().strip(),
        "service_version": service_version(binary),
        "backup_versions": [service_version(path) for path in backups],
        "mcp_check": check.stdout, "seed_old": SEED_OLD,
        "newest": max(json.loads((ROOT / "skills" / "coinwallet" / "mcp-tested.json").read_text())["tested"],
                      key=lambda v: tuple(int(x) for x in v.lstrip("v").split("."))),
    }


def db_tool_calls(hermes_home):
    """Every tool call the model made, from Hermes' state.db: [(name, arguments json), ...]. stream-json leaves out
    calls Hermes refused before running them (e.g. a tool_call that failed argument validation)."""
    try:
        db = sqlite3.connect(str(hermes_home / "state.db"))
        rows = db.execute("select tool_calls from messages where role = 'assistant' and tool_calls is not null "
                          "order by id").fetchall()
        db.close()
    except sqlite3.Error:
        return []
    out = []
    for (raw,) in rows:
        try:
            for call in json.loads(raw) or []:
                function = call.get("function") or {}
                out.append((function.get("name"), function.get("arguments")))
        except ValueError:
            pass
    return out


def session_cost(hermes_home, session):
    try:
        db = sqlite3.connect(str(hermes_home / "state.db"))
        row = db.execute("select estimated_cost_usd, tool_call_count, api_call_count from sessions where id = ?",
                         (session,)).fetchone()
        db.close()
        return row
    except sqlite3.Error:
        return None


# ---------- fixtures for cases after setup ----------

def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class ThrowawayService:
    """The real MCP binary as an HTTP service under a throwaway account (-u) and a throwaway HOME.
    macOS: that HOME links the real ~/Library/Keychains, so the account's item lands there (one per account)."""

    def __init__(self, svc_home, user):
        self.home, self.user = Path(svc_home), user
        self.home.mkdir(parents=True, exist_ok=True)
        if IS_MAC and not (self.home / "Library" / "Keychains").exists():
            (self.home / "Library").mkdir(exist_ok=True)
            os.symlink(str(REAL_HOME / "Library" / "Keychains"), str(self.home / "Library" / "Keychains"))
        base = self.home / "Library" / "Application Support" if IS_MAC else self.home / ".config"
        self.binary = base / "coinsdo-wallet-mcp" / "coinwallet" / "service"
        self.env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(self.home),
                    "USER": os.environ.get("USER", ""), "LANG": "en_US.UTF-8", "COINWALLET_TEST_USER": user}
        self.proc, self.url = None, None

    def start(self):
        if not self.binary.is_file():
            run = subprocess.run([sys.executable, str(ROOT / "skills" / "coinwallet" / "scripts" / "mcp.py"), "install"],
                                 env=self.env, capture_output=True, text=True, timeout=600)
            if "result: ok" not in run.stdout:
                raise SystemExit("throwaway service install failed:\n" + run.stdout + run.stderr)
        port = free_port()
        self.url = "http://127.0.0.1:" + str(port) + "/mcp"
        self.log = open(str(self.home / ("service-" + self.user + ".log")), "ab")
        self.proc = subprocess.Popen([str(self.binary), "-t", "http", "-p", str(port), "-e", "prod", "-u", self.user],
                                     env=self.env, cwd=str(self.binary.parent), stdout=self.log, stderr=self.log)
        deadline = time.monotonic() + 150
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                raise SystemExit("throwaway service exited, see " + self.log.name)
            try:
                HttpMcp(self.url).connect().call("get_wallets")
                return self.url
            except Exception:  # noqa: BLE001 - not listening yet or still uninitialized
                time.sleep(1)
        raise SystemExit("throwaway service did not answer, see " + self.log.name)

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self.proc:
            self.log.close()


def transactions(client, wallet_id):
    """Newest transfers of one wallet: [transaction dict, ...] (get_transactions, no status filter)."""
    reply = client.call("get_transactions", {"walletId": wallet_id, "pageIndex": 1, "pageSize": 50})
    items = (reply.get("items") if isinstance(reply, dict) else reply) or []
    return [item.get("transaction", item) for item in items]


def newbie_service(base, number, services):
    """M9 (whole Newbie journey): a new throwaway account (0 wallets) for each run; it joins and sends."""
    service = ThrowawayService(Path(base) / ("newbie-" + str(number)), "cwr-nb-" + time.strftime("%Y%m%d%H%M%S"))
    service.start()
    services["newbie"] = service


class RunningService:
    """A throwaway service someone else keeps running (--own-url)."""

    def __init__(self, url, user):
        self.url, self.user = url, user

    def start(self):
        HttpMcp(self.url).connect().call("get_wallets")

    def stop(self):
        pass


def read_truth(url, balances_for=()):
    """Service state, read tools only: wallets, every ONLINE wallet's addresses and transfers, balances of the
    named wallets."""
    client = HttpMcp(url).connect()
    wallets = (client.call("get_wallets") or {}).get("items") or []
    truth = {"wallets": wallets, "addresses": {}, "balances": {}, "txs": {}}
    for wallet in wallets:
        if wallet.get("status") != "ONLINE":
            continue
        truth["txs"][wallet["walletId"]] = transactions(client, wallet["walletId"])
        reply = client.call("get_addresses", {"walletId": wallet["walletId"], "pageIndex": 1, "pageSize": 100})
        items = (reply.get("items") if isinstance(reply, dict) else None) or []
        truth["addresses"][wallet["walletId"]] = items
        if balances_for == "all" or wallet["walletId"] in balances_for:
            for item in items:
                truth["balances"][item["addressId"]] = None  # stays None if the backend keeps failing
                for _ in range(6):  # the balance backend sometimes answers ErrCodeNet1004 for a while
                    try:
                        truth["balances"][item["addressId"]] = client.call(
                            "get_address_balance", {"addressId": item["addressId"]}).get("balance")
                        break
                    except RuntimeError:
                        time.sleep(3)
    return truth


def service_stub(home):
    """The Host runs the service (here: the proxy) after setup, so `scripts/mcp.py check` must find it: a stub at the
    service path answers `-v` like v1.0.8 and anything else with "already running", as the real binary does while the
    Host holds it. Without it, check says "not installed. Open the setup card" and agents reinstall (persona sweep)."""
    base = Path(home) / "Library" / "Application Support" if IS_MAC else Path(home) / ".config"
    stub = base / "coinsdo-wallet-mcp" / "coinwallet" / "service"
    stub.parent.mkdir(parents=True, exist_ok=True)
    newest = max(json.loads((ROOT / "skills" / "coinwallet" / "mcp-tested.json").read_text())["tested"],
                 key=lambda v: tuple(int(x) for x in v.lstrip("v").split(".")))
    stub.write_text('#!/bin/bash\nif [ "$1" = -v ]; then echo "coinsdo-wallet-mcp" >&2; echo " ' + newest + '" >&2; exit 0; fi\n'
                    'echo "the service is already running" >&2; exit 1\n', encoding="utf-8")
    os.chmod(str(stub), 0o755)


def preinstall(args, env, hermes_home, url, policy, hide, mcp_log, fail=()):
    """Skill installed and the coinwallet MCP server registered (through the proxy), as after a finished setup."""
    if args.source == "local":
        argv = [str(HERMES_PY), str(ROOT / "dev" / "hermes_local_install.py"), str(ROOT),
                "skills", "install", "CoinsDo/agentic-wallet/skills/coinwallet", "--yes"]
    else:
        argv = [HERMES, "skills", "install", args.repo + "/skills/coinwallet", "--yes"]
    run = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=300)
    if not (hermes_home / "skills" / "coinwallet" / "SKILL.md").is_file():
        raise SystemExit("skill install failed:\n" + run.stdout[-2000:] + run.stderr[-2000:])
    proxy_args = [str(PROXY), "--url", url, "--policy", policy, "--log", str(mcp_log)]
    for wallet_id in hide:
        proxy_args += ["--hide-wallet", str(wallet_id)]
    for tool in fail:
        proxy_args += ["--fail-tool", tool]
    service_stub(env["HOME"])
    entry = json.dumps({"command": sys.executable, "args": proxy_args})
    run = subprocess.run([HERMES, "config", "set", "mcp_servers.coinwallet", entry], env=env,
                         capture_output=True, text=True, timeout=60)
    if run.returncode:
        raise SystemExit("hermes config set failed: " + run.stdout + run.stderr)


def read_log(path):
    if not Path(path).is_file():
        return []
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def sent_bundles(mcp):
    """bundleIds the agent's send_transaction calls got back (from the proxy log's short reply)."""
    return [m.group(1) for e in mcp if e["tool"] == "send_transaction" and not e.get("isError")
            for m in [re.search(r'"bundleId"\s*:\s*"(\d+)"', e.get("reply", ""))] if m]


def wait_settled(url, mcp, text, limit=17 * 60):
    """A human step in the App (approve or reject the agent's transfer): wait until every bundle this run sent has
    left PENDING_APPROVAL (or the 15-minute window plus slack is over). Returns [(bundleId, status), ...]."""
    bundles = sent_bundles(mcp)
    sys.stderr.write("\n[human] " + text + " bundles=" + ",".join(bundles) + "\n")
    sys.stderr.flush()
    deadline, statuses = time.monotonic() + limit, {}
    while bundles and time.monotonic() < deadline:
        client = HttpMcp(url).connect()
        for bundle in bundles:
            try:
                statuses[bundle] = (client.call("get_transaction", {"bundleId": bundle}).get("transaction") or {}).get("status")
            except RuntimeError:
                pass
        if all(statuses.get(b) and statuses[b] != "PENDING_APPROVAL" for b in bundles):
            break
        time.sleep(5)
    sys.stderr.write("[human] settled: " + json.dumps(statuses) + "\n")
    return sorted(statuses.items())


class NeedsHuman(Exception):
    pass


WAIT_FILE = None  # --wait-file: a helper (or a phone-driving agent) creates this file instead of pressing Enter


def human_value(text):
    if WAIT_FILE:
        sys.stderr.write("\n[human] " + text + " (waiting for " + WAIT_FILE + ")\n")
        sys.stderr.flush()
        while not Path(WAIT_FILE).exists():
            time.sleep(2)
        value = Path(WAIT_FILE).read_text(encoding="utf-8").strip()
        Path(WAIT_FILE).unlink()
        return value
    if not sys.stdin.isatty():
        raise NeedsHuman(text)
    sys.stderr.write("\n[human] " + text)
    sys.stderr.flush()
    return input().strip()


def one_run(args, number, base, services):
    case = CASES[args.case]
    fixture = case["fixture"]
    user = "cwr-" + time.strftime("%Y%m%d%H%M%S") + "-" + str(number)
    run_dir, home, hermes_home, bin_dir, work = make_run_dir(base, args.model, args.source, args.repo)
    env = run_env(home, hermes_home, bin_dir, user)
    # local: the README file stands in for the GitHub landing page (which shows the README).
    source = str(ROOT / "README.md") if args.source == "local" else "https://github.com/" + args.repo
    values = dict(case.get("values", {}))
    values.update(dict(item.split("=", 1) for item in (args.set or [])))
    values["source"] = source
    mcp_log = run_dir / "mcp.jsonl"
    url, binary, before_yes = None, None, None
    if fixture == "seeded":
        binary = seed_update(run_dir, home, hermes_home, env, user, args.source, args.repo)
    elif fixture != "install":
        if fixture == "newbie":
            newbie_service(base, number, services)
        url = args.agenttest_url if fixture == "agenttest" else services[fixture].url
        policy = case.get("policy") or ("own" if fixture == "own" else "read")
        preinstall(args, env, hermes_home, url, policy, case.get("hide", []), mcp_log, case.get("fail", []))
    truth = read_truth(url, "all" if case.get("balances") else ()) if url else {}
    if case.get("hide"):
        truth["wallets"] = [w for w in truth["wallets"] if w["walletId"] not in case["hide"]]
    turns = list(case["turns"]) + list(args.reply or [])
    session, events, secs, timed_out, replies, marks, sent, settled = None, [], 0.0, False, [], [], [], []
    for turn in turns:
        if isinstance(turn, dict):
            if "hook" in turn:  # a dev step before a turn, e.g. mint a fresh token (test_cases.HOOKS)
                values.update(HOOKS[turn["hook"]](values, url))
                continue
            if "settle" in turn:
                settled[:] = wait_settled(url, read_log(mcp_log), turn["settle"])
                continue
            if "ask" in turn:
                values[turn["key"]] = values.get(turn["key"]) or human_value(turn["ask"])
            else:
                human_value(turn["wait"])
            continue
        prompt = turn.format(**values)
        sent.append(prompt if "{code}" not in turn else turn)
        events_turn, turn_secs, turn_timeout = hermes_turn(prompt, env, work, args.model, session, args.timeout)
        events += events_turn
        secs += turn_secs
        timed_out = timed_out or turn_timeout
        for event in events_turn:
            if event.get("session_id"):
                session = event["session_id"]
        results_turn = [e for e in events_turn if e.get("type") == "result"]
        replies.append(results_turn[-1].get("text", "") if results_turn else "")
        marks.append(len(read_log(mcp_log)))
        if binary and before_yes is None:
            before_yes = (service_version(binary), (hermes_home / "skills" / "coinwallet" / "VERSION").read_text().strip())
        if turn_timeout:
            break
    (run_dir / "events.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    tool_uses = [e for e in events if e.get("type") == "tool_use"]
    results = [e for e in events if e.get("type") == "result"]
    tokens = {k: sum((r.get("tokens") or {}).get(k, 0) for r in results) for k in ("input", "output", "total", "cache_read")}
    reply = replies[-1] if replies else ""
    files = []
    for event in tool_uses:
        for path in skill_files(event):
            if path not in files:
                files.append(path)
    mcp = read_log(mcp_log)
    if args.case == "setup":
        passed, checks = check_setup(hermes_home, home, env, reply)
    else:
        ctx = {"card": case.get("card"), "lang": case.get("lang"), "mcp": mcp, "mcp_by_turn": [mcp[(marks[i - 1] if i else 0):m] for i, m in enumerate(marks)],
               "replies": replies, "truth": truth, "values": values, "files": files, "prompts": sent,
               "tool_inputs": [(e.get("name"), e.get("input")) for e in tool_uses],
               "db_tool_calls": db_tool_calls(hermes_home),
               "truth_after": read_truth(url) if fixture in ("own", "newbie") else {}, "settled": settled,
               "sent_bundles": sent_bundles(mcp),
               "state": update_state(home, hermes_home, env, binary, before_yes) if fixture == "seeded" else {}}
        try:
            checks = case["check"](ctx)
        except Exception as exc:  # noqa: BLE001 - a broken fixture or reply shape is a failed run, not a crash
            checks = {"check_crashed: " + repr(exc)[:200]: False}
        passed = all(checks.values())
    cost_row = session_cost(hermes_home, session) if session else None
    budget = case.get("budget", {})
    if fixture in ("install", "seeded"):
        account = user
    elif fixture == "agenttest":
        account = "agenttest (read tools only)"
    else:
        account = services[fixture].user
    record = {
        "case": args.case, "host": "hermes", "model": args.model, "source": args.source, "run": number,
        "ok": bool(passed) and not timed_out, "checks": checks, "timed_out": timed_out,
        "calls": len(tool_uses), "db_calls": len(db_tool_calls(hermes_home)), "mcp_calls": [e["tool"] for e in mcp], "secs": round(secs, 1),
        "tokens": tokens["total"], "tokens_uncached": tokens["total"] - tokens["cache_read"],
        "cost_usd": round(cost_row[0], 5) if cost_row and cost_row[0] is not None else None,
        "api_calls": cost_row[2] if cost_row else None,
        "skill_files_read": files, "tools": [e.get("name") for e in tool_uses],
        "prompts": sent, "replies": [r[:600] for r in replies], "reply": reply[:600], "budget": budget,
        "within_budget": bool(budget) and len(tool_uses) <= budget["calls"] and secs <= budget["secs"]
        and tokens["total"] <= budget["tokens"],
        "session": session, "transcript": str(run_dir / "events.jsonl"), "mcp_log": str(mcp_log),
        "service_account": account, "date": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    if fixture == "newbie":
        services["newbie"].stop()
    return record, run_dir


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--case", choices=sorted(CASES), default="setup")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--model", default="deepseek/deepseek-v4-flash")
    parser.add_argument("--source", choices=("github", "local"), default="github")
    parser.add_argument("--repo", default="mackendell/agentic-wallet")
    parser.add_argument("--reply", action="append", help="extra scripted reply after the case's turns (repeatable)")
    parser.add_argument("--set", action="append", help="KEY=VALUE for the case's turns, e.g. wallet=my-test")
    parser.add_argument("--agenttest-url", default=AGENTTEST_URL)
    parser.add_argument("--own-home", default=str(REAL_HOME / ".cache" / "coinwallet-dev" / "own"),
                        help="throwaway HOME of the 'own' service account, kept between runs")
    parser.add_argument("--own-user", default="cwr-own", help="throwaway service account (-u) for the 'own' fixture")
    parser.add_argument("--own-url", help="use this already running throwaway service (--own-user's) for 'own' "
                                          "instead of starting one, so several runners can share it")
    parser.add_argument("--wait-file", help="wait for this file instead of Enter at human steps (its text = the value)")
    parser.add_argument("--timeout", type=int, default=600, help="seconds per turn before the run is killed")
    parser.add_argument("--out", help="append JSON lines here (default: stdout only)")
    parser.add_argument("--workdir", help="where run folders go (default: a temp folder); kept for transcripts")
    args = parser.parse_args()
    global WAIT_FILE
    WAIT_FILE = args.wait_file
    if not args.own_user.startswith("cwr-"):
        raise SystemExit("--own-user must be a throwaway account starting with cwr-")
    base = Path(args.workdir or tempfile.mkdtemp(prefix="hermes-runner-"))
    base.mkdir(parents=True, exist_ok=True)
    fixture = CASES[args.case]["fixture"]
    services = {}
    if fixture == "fresh":
        # One throwaway account per invocation (one test keychain item on macOS); these runs never join.
        services["fresh"] = ThrowawayService(base / "fresh-service", "cwr-fresh-" + time.strftime("%Y%m%d%H%M%S"))
    elif fixture == "own" and args.own_url:
        services["own"] = RunningService(args.own_url, args.own_user)
    elif fixture == "own":
        services["own"] = ThrowawayService(args.own_home, args.own_user)
    try:
        for service in services.values():
            service.start()
        for number in range(1, args.runs + 1):
            try:
                record, _ = one_run(args, number, str(base), services)
            except NeedsHuman as need:
                record = {"case": args.case, "run": number, "ok": None, "needs_human": str(need)}
            line = json.dumps(record, ensure_ascii=False)
            print(line, flush=True)
            if args.out:
                with open(args.out, "a", encoding="utf-8") as stream:
                    stream.write(line + "\n")
            if record.get("needs_human"):
                break
    finally:
        for service in services.values():
            service.stop()


if __name__ == "__main__":
    main()
