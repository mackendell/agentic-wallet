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
        if tested or minimum:
            data = json.loads((self.skill / "mcp-tested.json").read_text())
            if tested:
                data["tested"] = {v: HASHES[v] for v in tested}
            if minimum:
                data["minimum"] = minimum
            (self.skill / "mcp-tested.json").write_text(json.dumps(data))

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

    def mcp(self, *args, local=True):
        argv = [sys.executable, str(self.skill / "scripts" / "mcp.py")] + list(args) + ["--user", USER]
        if local and args[0] == "install":
            argv += ["--local-dir", str(ASSETS)]
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
        fake = box.root / "assets" / "v1.0.8"
        fake.mkdir(parents=True)
        shutil.copyfile(str(cached_asset("v1.0.7")), str(fake / asset()))
        argv = [sys.executable, str(box.skill / "scripts" / "mcp.py"), "install", "--local-dir", str(box.root / "assets"),
                "--user", USER]
        run = subprocess.run(argv, capture_output=True, text=True, env=box.env(), timeout=120)
        self.assertEqual(run.returncode, 1, run.stdout)
        self.assertIn("checksum", run.stdout)
        self.assertFalse(box.binary().exists())

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
