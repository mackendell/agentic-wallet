#!/usr/bin/env python3
"""Install, start and check the CoinsDo wallet MCP service for the coinwallet skill.

Usage:
  python3 mcp.py install --host hermes   download the newest tested MCP, start it once, print the register command
  python3 mcp.py start                   start the installed MCP once and wait until it answers
  python3 mcp.py check                   service starts, version >= minimum, get_wallets answers

macOS and Linux only. Python 3.9+, standard library only.
Output is plain "key: value" lines. Exit code 0 = ok, 1 = failed, 2 = the user must act.
"""

import argparse
import hashlib
import json
import os
import platform
import re
import secrets
import selectors
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
TESTED_FILE = SKILL_DIR / "mcp-tested.json"
DOWNLOAD = "https://github.com/CoinsDo/coinsdo-wallet-mcp/releases/download/{version}/{asset}"
SERVER_NAME = "coinwallet"
READY_SECONDS = 150  # a macOS keychain popup can wait for the user's password
HOST_ENV_KEYS = ("PATH", "HOME", "USER", "LANG", "LC_ALL", "TMPDIR", "XDG_CONFIG_HOME")


class Stop(Exception):
    """A result to print and exit with: code 1 = failed, 2 = the user must act."""

    def __init__(self, result, say, code=1, **extra):
        super().__init__(say)
        self.result, self.say, self.code, self.extra = result, say, code, extra


def out(**lines):
    for key, value in lines.items():
        if value is not None:
            print(key + ": " + str(value))


# ---------- versions ----------

def vtuple(text):
    match = re.search(r"v?(\d+)\.(\d+)\.(\d+)", text or "")
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def vname(parts):
    return "v" + ".".join(str(part) for part in parts)


def load_tested():
    try:
        data = json.loads(TESTED_FILE.read_text(encoding="utf-8"))
        minimum = vtuple(data["minimum"])
        tested = {vtuple(name): hashes for name, hashes in data["tested"].items()}
        if not minimum or not tested or None in tested:
            raise ValueError("bad versions")
        return minimum, tested
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        raise Stop("failed", "The skill file mcp-tested.json is missing or broken. Reinstall the skill.") from None


# ---------- paths and platform ----------

def is_mac():
    return sys.platform == "darwin"


def asset_name():
    system = platform.system()
    if system not in ("Darwin", "Linux"):
        raise Stop("failed", "This system is not supported. CoinWallet setup runs on macOS and Linux only.")
    machine = platform.machine().lower()
    if system == "Darwin":
        probe = subprocess.run(["sysctl", "-n", "hw.optional.arm64"], capture_output=True, text=True, timeout=10)
        if probe.stdout.strip() == "1":
            machine = "arm64"  # Python under Rosetta reports x86_64
    arch = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}.get(machine)
    if not arch:
        raise Stop("failed", "This CPU (" + machine + ") has no CoinsDo MCP build.")
    return "service-" + system.lower() + "-" + arch


def data_dir():
    """The MCP data folder (the service picks it from HOME; never move or delete it)."""
    if is_mac():
        return Path.home() / "Library" / "Application Support" / "coinsdo-wallet-mcp"
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "coinsdo-wallet-mcp"


def guard_home(user):
    """The service keeps its secret per account (-u) in the real keychain; a moved HOME would make it
    open the real account with an empty data folder. Only dev tests (throwaway account) may move HOME."""
    if not is_mac() or user:
        return
    import pwd
    real = Path(pwd.getpwuid(os.getuid()).pw_dir).resolve()
    if Path.home().resolve() != real:
        raise Stop("failed", "HOME is not your real home folder. Never set HOME for the wallet service. "
                   "Run this again without changing HOME.")


def binary_path():
    return data_dir() / "coinwallet" / "service"


def installed_version(binary):
    if not binary.is_file():
        return None
    try:
        run = subprocess.run([str(binary), "-v"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return vtuple(run.stdout + run.stderr)


# ---------- Linux master key ----------

def master_key_env(create=False):
    """Env the service needs for its master key. macOS uses the keychain: none.
    Linux order: COINSDO_MASTER_KEY_FILE, our own key file, /etc/machine-id, else create a key file once."""
    if is_mac():
        return {}
    key_file = os.environ.get("COINSDO_MASTER_KEY_FILE")
    if key_file:
        return {"COINSDO_MASTER_KEY_FILE": key_file}
    own_key = data_dir() / "master.key"
    if own_key.is_file():
        return {"COINSDO_MASTER_KEY_FILE": str(own_key)}
    if os.environ.get("COINSDO_MASTER_KEY"):
        raise Stop("needs_user", "COINSDO_MASTER_KEY is set in this shell. Add it to the Host's MCP config by hand. "
                   "Never change it: a new master key loses the agent's key shard.", 2)
    machine_id = Path("/etc/machine-id")
    try:
        if machine_id.read_text().strip():
            return {}
    except OSError:
        pass
    if not create:
        raise Stop("failed", "This machine has no /etc/machine-id and no master key file. Run install once.")
    own_key.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    handle = os.open(str(own_key), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(handle, "wb") as stream:
        stream.write(secrets.token_bytes(32))
    return {"COINSDO_MASTER_KEY_FILE": str(own_key)}


def service_env(create_key=False):
    """Same small env a Host passes to an MCP server, plus the master key."""
    env = {}
    for key in HOST_ENV_KEYS:
        value = os.environ.get(key)
        if value:
            env[key] = value
    env.update(master_key_env(create_key))
    return env


# ---------- download ----------

def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(url, target):
    """urllib first, curl if Python has no CA certificates. Neither sets the macOS quarantine flag."""
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "coinwallet-skill"})
        with urllib.request.urlopen(request, timeout=60) as response, open(target, "wb") as stream:
            shutil.copyfileobj(response, stream, 1024 * 1024)
        return
    except Exception:  # noqa: BLE001 - any urllib failure falls back to curl
        pass
    curl = shutil.which("curl")
    if not curl:
        raise Stop("failed", "Download failed and curl is missing. Check the internet connection, then run install again.")
    run = subprocess.run([curl, "-fsSL", "--retry", "2", "-o", str(target), url], capture_output=True, text=True, timeout=600)
    if run.returncode:
        raise Stop("failed", "Download failed. Check the internet connection, then run install again.")


def download(version, expected_sha, binary, local_dir=None):
    asset = asset_name()
    binary.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    handle, partial = tempfile.mkstemp(prefix=".service-", dir=str(binary.parent))
    os.close(handle)
    try:
        if local_dir:
            shutil.copyfile(str(Path(local_dir) / vname(version) / asset), partial)
        else:
            fetch(DOWNLOAD.format(version=vname(version), asset=asset), partial)
        if sha256(partial) != expected_sha:
            raise Stop("failed", "The downloaded file does not match the tested checksum. Nothing was installed.")
        os.chmod(partial, 0o755)
        os.replace(partial, str(binary))
    finally:
        if os.path.exists(partial):
            os.unlink(partial)


# ---------- talking to the service ----------

def explain_exit(stderr_text):
    text = stderr_text or ""
    if "already running" in text:
        return Stop("running", "The service is already running (your Host started it).", 0)
    if "(-128)" in text:
        return Stop("needs_user", "The Mac keychain popup was denied. Run start again, then type your Mac login "
                    "password and click Always Allow. Never click Deny.", 2)
    if "(-60006)" in text:
        return Stop("needs_user", "The Mac keychain popup was not answered in time. Run start again, then type your "
                    "Mac login password and click Always Allow.", 2)
    if "(-60008)" in text:
        return Stop("needs_user", "The Mac keychain popup cannot show here (no desktop session). Start the service "
                    "from the Host in your logged-in Mac desktop session.", 2)
    if "authentication failed" in text or "decrypt secure storage" in text:
        return Stop("failed", "The service cannot open the agent's key shard: the master key changed. Stop here and "
                    "tell the user. Never run -clean-data and never reinstall with -r: that wipes the shard.")
    if "machine-id" in text or "MASTER_KEY" in text:
        return Stop("failed", "The service has no master key. Run install again on this machine.")
    last = [line for line in text.strip().splitlines() if line.strip()]
    reason = last[-1][-200:] if last else "no message"
    return Stop("failed", "The service stopped: " + reason + ". Stop and tell the user; never run -clean-data.")


class Service:
    """One short-lived stdio session with the MCP service."""

    def __init__(self, binary, user=None):
        argv = [str(binary), "-t", "stdio", "-e", "prod"]
        if user:
            argv += ["-u", user]
        self.errors = tempfile.TemporaryFile()
        self.proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.errors,
                                     env=service_env(), cwd=str(binary.parent))
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.proc.stdout, selectors.EVENT_READ)
        self.buffer = b""
        self.next_id = 0

    def stderr_text(self):
        self.errors.seek(0)
        return self.errors.read().decode("utf-8", "replace")

    def died(self):
        self.proc.wait(timeout=10)
        return explain_exit(self.stderr_text())

    def send(self, message):
        try:
            self.proc.stdin.write((json.dumps(message) + "\n").encode())
            self.proc.stdin.flush()
        except OSError:
            raise self.died() from None

    def request(self, method, params, wait):
        self.next_id += 1
        self.send({"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params})
        deadline = time.monotonic() + wait
        while True:
            while b"\n" in self.buffer:
                line, self.buffer = self.buffer.split(b"\n", 1)
                try:
                    message = json.loads(line)
                except ValueError:
                    continue
                if isinstance(message, dict) and message.get("id") == self.next_id:
                    return message
            left = deadline - time.monotonic()
            if left <= 0 or not self.selector.select(left):
                raise Stop("failed", "The service did not answer in time. Stop and tell the user.")
            chunk = os.read(self.proc.stdout.fileno(), 65536)
            if not chunk:
                raise self.died()
            self.buffer += chunk

    def call(self, tool, wait):
        message = self.request("tools/call", {"name": tool, "arguments": {}}, wait)
        result = message.get("result") if isinstance(message.get("result"), dict) else {}
        texts = [c.get("text", "") for c in result.get("content", []) if isinstance(c, dict)]
        text = " ".join(texts)
        if "error" in message or result.get("isError"):
            return None, text or json.dumps(message.get("error"))
        data = result.get("structuredContent")
        if data is None:
            try:
                data = json.loads(text)
            except ValueError:
                data = text
        return data, None

    def wait_ready(self):
        """initialize, then get_wallets until it stops saying uninitialized."""
        self.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                    "clientInfo": {"name": "coinwallet-mcp-py", "version": "1"}}, READY_SECONDS)
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        deadline = time.monotonic() + READY_SECONDS
        while True:
            wallets, error = self.call("get_wallets", READY_SECONDS)
            if error is None:
                break
            if "uninitialized" not in error.lower() or time.monotonic() > deadline:
                raise Stop("failed", "get_wallets failed: " + error[:200] + ". Stop and tell the user.")
            time.sleep(1)
        status, _ = self.call("status", 30)
        status = status if isinstance(status, dict) else {}
        items = wallets.get("items") if isinstance(wallets, dict) else wallets
        count = len(items) if isinstance(items, list) else 0
        return status, count

    def close(self):
        try:
            self.proc.stdin.close()
        except OSError:
            pass
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        self.selector.close()
        self.errors.close()


def start_once(binary, user):
    if not binary.is_file():
        raise Stop("failed", "The MCP service is not installed. Run: python3 " + str(Path(__file__).resolve()) + " install")
    service = Service(binary, user)
    try:
        return service.wait_ready()
    finally:
        service.close()


# ---------- Host registration ----------

def register_command(host, binary, user):
    args = ["-t", "stdio", "-e", "prod"] + (["-u", user] if user else [])
    env = master_key_env()
    if host == "hermes":
        entry = {"command": str(binary), "args": args}
        if env:
            entry["env"] = env
        return "hermes config set mcp_servers." + SERVER_NAME + " " + shlex.quote(json.dumps(entry))
    return None


# ---------- subcommands ----------

def do_install(args):
    minimum, tested = load_tested()
    newest = max(tested)
    asset = asset_name()
    binary = binary_path()
    have = installed_version(binary)
    if have is None:
        expected = tested[newest].get(asset)
        if not expected:
            raise Stop("failed", "No tested MCP build for " + asset + ".")
        download(newest, expected, binary, args.local_dir)
        have = newest
        note = "installed " + vname(newest)
    elif have < minimum:
        raise Stop("needs_user", "The installed MCP " + vname(have) + " is older than the minimum " + vname(minimum)
                   + ". Ask the user before upgrading (it restarts the service).", 2, version=vname(have))
    else:
        note = "already installed " + vname(have) + " (left as is)"
    master_key_env(create=True)
    status, count = start_once(binary, args.user)
    out(result="ok", mcp=note, service=binary, environment=status.get("environmentName"), wallets=count,
        data_folder=status.get("dataDir") or data_dir())
    key = master_key_env().get("COINSDO_MASTER_KEY_FILE")
    if key:
        out(master_key=key, say="Tell the user once: Never delete or replace the master key file or the MCP data "
            "folder. Moving to a new server means a new wallet Room.")
    command = register_command(args.host, binary, args.user) if args.host else None
    if command:
        out(next="run the register command below once, exactly as printed", register=command)
    return 0


def do_start(args):
    try:
        status, count = start_once(binary_path(), args.user)
    except Stop as stop:
        if stop.result == "running":
            out(result="ok", service="already running in your Host")
            return 0
        raise
    out(result="ok", service=status.get("ServerVersion"), environment=status.get("environmentName"), wallets=count)
    return 0


def do_check(args):
    minimum, _tested = load_tested()
    binary = binary_path()
    have = installed_version(binary)
    if have is None:
        raise Stop("failed", "The MCP service is not installed. Open the setup card.")
    if have < minimum:
        raise Stop("needs_user", "MCP " + vname(have) + " is older than the minimum " + vname(minimum)
                   + ". Tell the user and ask before upgrading. If the user says no, stop.", 2, version=vname(have))
    try:
        status, count = start_once(binary, args.user)
    except Stop as stop:
        if stop.result != "running":
            raise
        out(result="ok", version=vname(have), service="running in your Host",
            say="The wallet service is running. Report the failed tool's error to the user in one line and stop.")
        return 0
    out(result="ok", version=vname(have), environment=status.get("environmentName"), wallets=count)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="mcp.py", description="CoinWallet MCP service setup.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("install", "start", "check"):
        command = sub.add_parser(name)
        command.add_argument("--user", help=argparse.SUPPRESS)  # dev tests only: throwaway service account (-u)
        if name == "install":
            command.add_argument("--host", choices=("hermes",), help="print the register command for this Host")
            command.add_argument("--local-dir", help=argparse.SUPPRESS)  # dev tests only: pre-downloaded assets
    args = parser.parse_args(argv)
    # Dev test runs only: a throwaway service account so the real keychain item is never used.
    args.user = args.user or os.environ.get("COINWALLET_TEST_USER") or None
    try:
        guard_home(args.user)
        return {"install": do_install, "start": do_start, "check": do_check}[args.command](args)
    except Stop as stop:
        out(result=stop.result, **stop.extra)
        out(say=stop.say)
        return stop.code
    except KeyboardInterrupt:
        out(result="failed", say="Interrupted.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
