#!/usr/bin/env python3
"""Seam 3: mcp.py CLI tests against real CoinsDo MCP release binaries. No model.

Run on macOS:   python3 tests/test_mcp_cli.py
Run on Linux:   dev/linux_mcp_tests.sh   (Docker: one run with /etc/machine-id, one without)

Safety:
- Each test gets a throwaway HOME. The MCP service picks its data folder from HOME, so real data is never touched.
- macOS: the throwaway HOME gets a symlink to the real ~/Library/Keychains (a HOME without it makes macOS offer
  to reset the login keychain). Every run uses one fresh service account (-u cwt-<time>), so the real keychain
  items (accounts coinsdo, agenttest) are never read or changed. Each run leaves one test item
  (service com.coinsdo.wallet.secure, account cwt-<time>); it holds an empty test wallet only.
- Never runs -clean-data.

Env:
  COINWALLET_TEST_ASSETS  folder for downloaded release assets (cache, layout <version>/<asset>), default ~/.cache/coinwallet-test-assets
  COINWALLET_TEST_CONTAINER=1  allow tests that edit /etc/machine-id (only inside a throwaway container)
"""

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "coinwallet"
IS_MAC = sys.platform == "darwin"
IN_CONTAINER = os.environ.get("COINWALLET_TEST_CONTAINER") == "1"
ASSETS = Path(os.environ.get("COINWALLET_TEST_ASSETS") or str(Path.home() / ".cache" / "coinwallet-test-assets"))
USER = "cwt-" + time.strftime("%Y%m%d%H%M%S")
REAL_HOME = Path.home()

HASHES = {
    "v1.0.7": {
        "service-darwin-amd64": "cddcd041e4cfbf3443a87879d6f05d576855b1b20cd29818be360e721fda9b04",
        "service-darwin-arm64": "4ccf631450e69ba5ae62584cc632cd290be4344072861e58c2f622f97cf0ae07",
        "service-linux-amd64": "a3f805edd8008e5d5a3b8b83516a25d6598f98ae3c85b8dc3353dd22d855f0a2",
        "service-linux-arm64": "178d4b2a022cc297c11286b4e2749892e162a6302ca2ea06a2fd12b5416c1a33",
    },
}
HASHES["v1.0.8"] = json.loads((SKILL / "mcp-tested.json").read_text())["tested"]["v1.0.8"]


def asset():
    machine = platform.machine().lower()
    if IS_MAC and subprocess.run(["sysctl", "-n", "hw.optional.arm64"], capture_output=True, text=True).stdout.strip() == "1":
        machine = "arm64"
    arch = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}[machine]
    return "service-" + ("darwin" if IS_MAC else "linux") + "-" + arch


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cached_asset(version):
    path = ASSETS / version / asset()
    if not path.is_file() or sha(path) != HASHES[version][asset()]:
        path.parent.mkdir(parents=True, exist_ok=True)
        url = "https://github.com/CoinsDo/coinsdo-wallet-mcp/releases/download/" + version + "/" + asset()
        with urllib.request.urlopen(url, timeout=120) as response, open(path, "wb") as stream:
            shutil.copyfileobj(response, stream)
        if sha(path) != HASHES[version][asset()]:
            raise RuntimeError("bad test asset " + str(path))
    return path


class Sandbox:
    """Throwaway HOME + a copy of the skill whose mcp-tested.json the test may rewrite."""

    def __init__(self, tested=None, minimum=None):
        self.root = Path(tempfile.mkdtemp(prefix="cwtest-"))
        self.home = self.root / "home"
        self.home.mkdir()
        if IS_MAC:
            (self.home / "Library").mkdir()
            os.symlink(str(REAL_HOME / "Library" / "Keychains"), str(self.home / "Library" / "Keychains"))
        self.skill = self.root / "coinwallet"
        shutil.copytree(str(SKILL), str(self.skill))
        self.assets = self.root / "assets"  # local release assets: real cached ones plus fake builds
        for version in HASHES:
            (self.assets / version).mkdir(parents=True)
            os.symlink(str(cached_asset(version)), str(self.assets / version / asset()))
        if tested or minimum:
            self.set_tested(tested, minimum)

    def set_tested(self, tested=None, minimum=None, no_fallback=None, extra=None):
        """Rewrite this copy's mcp-tested.json. extra: {version: sha256} for fake builds."""
        data = json.loads((self.skill / "mcp-tested.json").read_text())
        if tested:
            data["tested"] = {v: HASHES[v] for v in tested}
        for version, digest in (extra or {}).items():
            data["tested"][version] = {asset(): digest}
        if minimum:
            data["minimum"] = minimum
        if no_fallback is not None:
            data["no_fallback"] = no_fallback
        (self.skill / "mcp-tested.json").write_text(json.dumps(data))

    def fake_build(self, version, stderr="boom: the service cannot start"):
        """A build that reports `version` and exits 1 on start (stands in for a broken MCP release)."""
        path = self.assets / version / asset()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/bin/sh\nif [ \"$1\" = -v ]; then echo 'service version " + version + "'; exit 0; fi\n"
                        "echo '" + stderr + "' >&2\nexit 1\n")
        os.chmod(str(path), 0o755)
        return sha(path)

    def backups(self):
        folder = self.data_dir() / "backups"
        return sorted(folder.iterdir()) if folder.is_dir() else []

    def data_dir(self):
        if IS_MAC:
            return self.home / "Library" / "Application Support" / "coinsdo-wallet-mcp"
        return self.home / ".config" / "coinsdo-wallet-mcp"

    def binary(self):
        return self.data_dir() / "coinwallet" / "service"

    def env(self):
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(self.home),
               "LANG": os.environ.get("LANG", "C.UTF-8")}
        assert not IS_MAC or (self.home / "Library" / "Keychains").exists()
        return env

    def mcp(self, *args, local=True, user=USER):
        argv = [sys.executable, str(self.skill / "scripts" / "mcp.py")] + list(args) + ["--user", user]
        if local and args[0] in ("install", "upgrade", "fallback"):
            argv += ["--local-dir", str(self.assets)]
        run = subprocess.run(argv, capture_output=True, text=True, env=self.env(), timeout=400)
        lines = {}
        for line in run.stdout.splitlines():
            key, _, value = line.partition(": ")
            lines[key] = value
        return run.returncode, lines, run.stdout + run.stderr

    def place(self, version):
        self.binary().parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(cached_asset(version)), str(self.binary()))
        os.chmod(str(self.binary()), 0o755)

    def version(self):
        run = subprocess.run([str(self.binary()), "-v"], capture_output=True, text=True, env=self.env())
        return (run.stdout + run.stderr).strip().split()[-1]

    def cleanup(self):
        shutil.rmtree(str(self.root), ignore_errors=True)


class McpCli(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cached_asset("v1.0.7")
        cached_asset("v1.0.8")

    def setUp(self):
        self.boxes = []

    def tearDown(self):
        for box in self.boxes:
            box.cleanup()

    def box(self, **kw):
        box = Sandbox(**kw)
        self.boxes.append(box)
        return box

    # install

    def test_install_downloads_newest_tested_and_prints_register(self):
        box = self.box(tested=["v1.0.7", "v1.0.8"], minimum="v1.0.7")
        code, lines, text = box.mcp("install", "--host", "hermes", local=False)  # real GitHub download
        self.assertEqual(code, 0, text)
        self.assertEqual(lines["result"], "ok", text)
        self.assertEqual(box.version(), "v1.0.8")
        self.assertEqual(sha(box.binary()), HASHES["v1.0.8"][asset()])
        self.assertEqual(lines["environment"], "prod")
        self.assertEqual(lines["wallets"], "0")
        self.assertEqual(os.path.realpath(lines["data_folder"]), os.path.realpath(str(box.data_dir())))  # service agrees on the folder
        self.assertIn("hermes config set mcp_servers.coinwallet", lines["register"])
        self.assertIn(str(box.binary()), lines["register"])
        self.assertIn('"-e", "prod"', lines["register"])
        if IS_MAC:
            xattr = subprocess.run(["xattr", "-p", "com.apple.quarantine", str(box.binary())], capture_output=True)
            self.assertNotEqual(xattr.returncode, 0, "binary has a quarantine flag")

    def test_install_leaves_newer_mcp_alone(self):
        box = self.box(tested=["v1.0.7"], minimum="v1.0.7")
        box.place("v1.0.8")
        before = sha(box.binary())
        code, lines, text = box.mcp("install")
        self.assertEqual(code, 0, text)
        self.assertIn("already installed v1.0.8", lines["mcp"])
        self.assertEqual(sha(box.binary()), before)

    def test_install_below_minimum_asks_user(self):
        box = self.box()
        box.place("v1.0.7")
        code, lines, text = box.mcp("install")
        self.assertEqual(code, 2, text)
        self.assertEqual(lines["result"], "needs_user")
        self.assertEqual(box.version(), "v1.0.7")  # not upgraded without a yes

    def test_install_rejects_wrong_checksum(self):
        box = self.box()
        fake = box.root / "bad-assets" / "v1.0.8"
        fake.mkdir(parents=True)
        shutil.copyfile(str(cached_asset("v1.0.7")), str(fake / asset()))
        argv = [sys.executable, str(box.skill / "scripts" / "mcp.py"), "install", "--local-dir", str(box.root / "bad-assets"),
                "--user", USER]
        run = subprocess.run(argv, capture_output=True, text=True, env=box.env(), timeout=120)
        self.assertEqual(run.returncode, 1, run.stdout)
        self.assertIn("checksum", run.stdout)
        self.assertFalse(box.binary().exists())

    @unittest.skipIf(os.getuid() == 0, "root ignores folder permissions")
    def test_install_in_a_read_only_sandbox_says_so(self):
        box = self.box()
        parent = box.data_dir().parent
        parent.mkdir(parents=True, exist_ok=True)
        os.chmod(str(parent), 0o500)  # like a Host sandbox that blocks writes outside the work folder
        try:
            code, lines, text = box.mcp("install")
        finally:
            os.chmod(str(parent), 0o700)
        self.assertEqual(code, 1, text)
        self.assertIn("Permission denied", lines["say"])
        self.assertNotIn("Traceback", text)

    @unittest.skipUnless(IS_MAC, "macOS keychain guard")
    def test_moved_home_without_test_account_is_refused(self):
        box = self.box()
        argv = [sys.executable, str(box.skill / "scripts" / "mcp.py"), "install", "--local-dir", str(ASSETS)]
        run = subprocess.run(argv, capture_output=True, text=True, env=box.env(), timeout=60)
        self.assertEqual(run.returncode, 1, run.stdout)
        self.assertIn("Never set HOME", run.stdout)
        self.assertFalse(box.binary().exists())

    # check

    def test_check_fails_below_minimum(self):
        box = self.box()
        box.place("v1.0.7")
        code, lines, text = box.mcp("check")
        self.assertEqual(code, 2, text)
        self.assertEqual(lines["result"], "needs_user")
        self.assertIn("older than the minimum v1.0.8", lines["say"])

    def test_check_passes_at_minimum(self):
        box = self.box()
        code, _, text = box.mcp("install")
        self.assertEqual(code, 0, text)
        code, lines, text = box.mcp("check")
        self.assertEqual(code, 0, text)
        self.assertEqual(lines["version"], "v1.0.8")
        self.assertEqual(lines["wallets"], "0")

    def test_check_not_installed(self):
        box = self.box()
        code, lines, text = box.mcp("check")
        self.assertEqual(code, 1, text)
        self.assertIn("not installed", lines["say"])

    # start

    def test_start_waits_until_ready_then_sees_host_copy(self):
        box = self.box()
        code, _, text = box.mcp("install")
        self.assertEqual(code, 0, text)
        code, lines, text = box.mcp("start")
        self.assertEqual(code, 0, text)
        self.assertEqual(lines["service"], "v1.0.8")
        # A Host-owned copy holds the data folder lock: start and check must say "running", not fail.
        argv = [str(box.binary()), "-t", "stdio", "-e", "prod", "-u", USER]
        env = box.env()
        key = box.data_dir() / "master.key"
        if key.exists():
            env["COINSDO_MASTER_KEY_FILE"] = str(key)
        host = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
        try:
            time.sleep(3)
            code, lines, text = box.mcp("start")
            self.assertEqual(code, 0, text)
            self.assertIn("already running", lines["service"])
            code, lines, text = box.mcp("check")
            self.assertEqual(code, 0, text)
            self.assertIn("running in your Host", lines["service"])
        finally:
            host.stdin.close()
            host.terminate()
            host.wait(timeout=10)

    # register with each Host

    def test_register_command_per_host(self):
        box = self.box()
        code, _, text = box.mcp("install")
        self.assertEqual(code, 0, text)
        binary = str(box.binary())
        for host, start in (("hermes", "hermes config set mcp_servers.coinwallet "),
                            ("openclaw", "openclaw mcp set coinwallet "),
                            ("claude-code", "claude mcp remove --scope user coinwallet >/dev/null 2>&1; "
                                            "claude mcp add-json --scope user coinwallet "),
                            ("codex", "codex mcp add coinwallet ")):
            code, lines, text = box.mcp("install", "--host", host)  # second install: left as is, register printed
            self.assertEqual(code, 0, text)
            register = lines["register"]
            self.assertTrue(register.startswith(start), register)
            self.assertIn(binary, register)
            self.assertIn("prod", register)
            self.assertIn(USER, register)

    def test_register_command_runs_in_a_throwaway_host_config(self):
        """Run each printed line for real, with HOME = the throwaway home (never the user's Host config)."""
        box = self.box()
        code, _, text = box.mcp("install")
        self.assertEqual(code, 0, text)
        key = box.data_dir() / "master.key"
        ran = 0
        for host, tool in (("openclaw", "openclaw"), ("claude-code", "claude"), ("codex", "codex")):
            if not shutil.which(tool):
                continue
            _, lines, _ = box.mcp("install", "--host", host)
            run = subprocess.run(["/bin/sh", "-c", lines["register"]], capture_output=True, text=True,
                                 env=box.env(), cwd=str(box.root), stdin=subprocess.DEVNULL, timeout=120)
            self.assertEqual(run.returncode, 0, host + ": " + run.stdout + run.stderr)
            if host == "openclaw":
                entry = json.loads((box.home / ".openclaw" / "openclaw.json").read_text())["mcp"]["servers"]["coinwallet"]
            elif host == "claude-code":
                subprocess.run(["/bin/sh", "-c", lines["register"]], capture_output=True, env=box.env(),
                               cwd=str(box.root), stdin=subprocess.DEVNULL, timeout=120)  # twice: no "already exists"
                entry = json.loads((box.home / ".claude.json").read_text())["mcpServers"]["coinwallet"]
            else:
                toml = (box.home / ".codex" / "config.toml").read_text()
                self.assertIn("[mcp_servers.coinwallet]", toml)
                self.assertIn(str(box.binary()), toml)
                if key.exists():
                    self.assertIn(str(key), toml)
                ran += 1
                continue
            self.assertEqual(entry["command"], str(box.binary()))
            self.assertEqual(entry["args"][:4], ["-t", "stdio", "-e", "prod"])
            if key.exists():
                self.assertEqual(entry["env"]["COINSDO_MASTER_KEY_FILE"], str(key))
            ran += 1
        if not ran:
            self.skipTest("no openclaw, claude or codex on this machine")

    # upgrade

    def test_upgrade_backs_up_then_restarts_newest_tested(self):
        box = self.box(tested=["v1.0.7"], minimum="v1.0.7")
        if IS_MAC:
            # A v1.0.7 start would make the keychain item, and v1.0.8 would then show the popup (needs a person).
            # So v1.0.7 is only placed here; the Linux run below starts it on real data.
            box.place("v1.0.7")
            marker = box.data_dir() / ".data" / "marker"
            marker.parent.mkdir(parents=True)
            marker.write_text("wallet data")
        else:
            code, _, text = box.mcp("install")
            self.assertEqual(code, 0, text)
            marker = next(box.data_dir().glob(".data/**/*.db"))
        key = box.data_dir() / "master.key"
        key_before = sha(key) if key.exists() else None
        box.set_tested(["v1.0.7", "v1.0.8"])
        code, lines, text = box.mcp("upgrade")
        self.assertEqual(code, 0, text)
        self.assertEqual(lines["result"], "ok", text)
        self.assertEqual(lines["mcp"], "upgraded v1.0.7 -> v1.0.8")
        self.assertEqual(lines["wallets"], "0")  # restarted right away and get_wallets answered
        self.assertEqual(box.version(), "v1.0.8")
        backup = Path(lines["backup"])
        self.assertEqual(box.backups(), [backup])
        self.assertEqual(sha(backup / "coinwallet" / "service"), HASHES["v1.0.7"][asset()])
        self.assertTrue((backup / marker.relative_to(box.data_dir())).is_file())
        self.assertFalse((backup / "backups").exists())
        if key_before:
            self.assertEqual(sha(key), key_before)  # same master key on Linux
        code, lines, text = box.mcp("check")
        self.assertEqual(code, 0, text)
        self.assertEqual(lines["version"], "v1.0.8")

    def test_upgrade_stops_the_host_copy_first(self):
        box = self.box(tested=["v1.0.7"], minimum="v1.0.7")
        if IS_MAC:
            box.place("v1.0.7")
        else:
            code, _, text = box.mcp("install")  # Linux: makes the master key file when there is no machine-id
            self.assertEqual(code, 0, text)
        box.set_tested(["v1.0.7", "v1.0.8"])
        env = box.env()
        key = box.data_dir() / "master.key"
        if key.exists():
            env["COINSDO_MASTER_KEY_FILE"] = str(key)
        # The Host's copy holds the data folder lock. It runs under another throwaway account so that on macOS
        # the v1.0.8 start under USER makes a fresh keychain item (silent) instead of showing a popup.
        host = subprocess.Popen([str(box.binary()), "-t", "stdio", "-e", "prod", "-u", USER + "-host"],
                                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
        try:
            time.sleep(3)
            self.assertIsNone(host.poll(), "the Host copy did not start")
            code, lines, text = box.mcp("upgrade")
            self.assertEqual(code, 0, text)
            self.assertEqual(lines["result"], "ok", text)
            self.assertEqual(lines["wallets"], "0")
            self.assertIsNotNone(host.poll(), "the Host copy is still running")
        finally:
            host.stdin.close()
            if host.poll() is None:
                host.terminate()
            host.wait(timeout=10)

    def test_upgrade_leaves_newest_alone(self):
        box = self.box()
        code, _, text = box.mcp("install")
        self.assertEqual(code, 0, text)
        before = sha(box.binary())
        code, lines, text = box.mcp("upgrade")
        self.assertEqual(code, 0, text)
        self.assertIn("already v1.0.8", lines["mcp"])
        self.assertEqual(sha(box.binary()), before)
        self.assertEqual(box.backups(), [])

    def test_upgrade_not_installed(self):
        box = self.box()
        code, lines, text = box.mcp("upgrade")
        self.assertEqual(code, 1, text)
        self.assertIn("not installed", lines["say"])

    # fallback

    def test_failed_upgrade_falls_back_to_previous_tested_on_same_data(self):
        box = self.box()
        code, _, text = box.mcp("install")  # v1.0.8 on real data
        self.assertEqual(code, 0, text)
        key = box.data_dir() / "master.key"
        key_before = sha(key) if key.exists() else None
        box.set_tested(extra={"v1.0.9": box.fake_build("v1.0.9")})
        code, lines, text = box.mcp("upgrade")
        self.assertEqual(code, 0, text)
        self.assertEqual(lines["result"], "fallback", text)
        self.assertIn("went back to v1.0.8", lines["mcp"])
        self.assertIn("boom", lines["mcp"])
        self.assertEqual(lines["wallets"], "0")  # the wallet data is still readable
        self.assertEqual(sha(box.binary()), HASHES["v1.0.8"][asset()])
        self.assertEqual(len(box.backups()), 2)  # before the upgrade, and before going back
        self.assertEqual(sha(box.backups()[0] / "coinwallet" / "service"), HASHES["v1.0.8"][asset()])
        if key_before:
            self.assertEqual(sha(key), key_before)
        code, lines, text = box.mcp("check")
        self.assertEqual(code, 0, text)
        self.assertEqual(lines["version"], "v1.0.8")

    def test_failed_upgrade_without_fallback_stops(self):
        box = self.box()
        code, _, text = box.mcp("install")
        self.assertEqual(code, 0, text)
        box.set_tested(extra={"v1.0.9": box.fake_build("v1.0.9")}, no_fallback=["v1.0.9"])
        code, lines, text = box.mcp("upgrade")
        self.assertEqual(code, 1, text)
        self.assertEqual(lines["result"], "failed")
        self.assertIn("no tested version to go back to", lines["say"])
        self.assertIn(str(box.backups()[0]), lines["say"])
        self.assertEqual(box.version(), "v1.0.9")  # left as is; the user and maintainer decide

    @unittest.skipIf(IS_MAC, "v1.0.7 opening a keychain item v1.0.8 made shows a popup (needs a person)")
    def test_fallback_command_reinstalls_previous_tested(self):
        box = self.box(tested=["v1.0.7", "v1.0.8"], minimum="v1.0.7")
        code, _, text = box.mcp("install")  # v1.0.8
        self.assertEqual(code, 0, text)
        code, lines, text = box.mcp("fallback")
        self.assertEqual(code, 0, text)
        self.assertEqual(lines["result"], "fallback", text)
        self.assertEqual(box.version(), "v1.0.7")
        self.assertEqual(lines["wallets"], "0")
        self.assertEqual(len(box.backups()), 1)

    # Linux master key

    @unittest.skipIf(IS_MAC or not IN_CONTAINER, "needs a throwaway Linux container")
    def test_linux_master_key(self):
        machine_id = Path("/etc/machine-id")
        box = self.box()
        key = box.data_dir() / "master.key"
        if machine_id.exists() and machine_id.read_text().strip():
            code, lines, text = box.mcp("install", "--host", "hermes")
            self.assertEqual(code, 0, text)
            self.assertFalse(key.exists())
            self.assertNotIn("COINSDO_MASTER_KEY_FILE", lines["register"])
            return
        code, lines, text = box.mcp("install", "--host", "hermes")
        self.assertEqual(code, 0, text)
        self.assertTrue(key.is_file())
        self.assertEqual(oct(key.stat().st_mode & 0o777), "0o600")
        self.assertEqual(len(key.read_bytes()), 32)
        self.assertIn('"COINSDO_MASTER_KEY_FILE": "' + str(key) + '"', lines["register"])
        first = sha(key)
        code, _, text = box.mcp("install")  # second install: same key file, service still opens its data
        self.assertEqual(code, 0, text)
        self.assertEqual(sha(key), first)
        code, lines, text = box.mcp("start")
        self.assertEqual(code, 0, text)
        code, lines, text = box.mcp("check")
        self.assertEqual(code, 0, text)
        self.assertEqual(sha(key), first)


if __name__ == "__main__":
    print("service account for this run:", USER, file=sys.stderr)
    unittest.main(verbosity=2)
