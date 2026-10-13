#!/usr/bin/env python3
"""Prepare a local CoinsDo MCP; never call wallet business tools.

Management stdout is one JSON document. `run` stdout belongs solely to the MCP.
Python >= 3.9, standard library only. Host CLI configuration is intentionally
separate from evidence that the current agent has loaded its tools.
"""

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import selectors
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.error
import urllib.request

REPO = "CoinsDo/coinsdo-wallet-mcp"
RELEASES = "https://api.github.com/repos/" + REPO + "/releases/tags/"
SERVER = "coinsdo-wallet"
TIMEOUT = 20
MAX_BYTES = 256 * 1024 * 1024


def localize(text):
    """Translation failure changes wording only, never the decision or error code."""
    if not isinstance(text, str):
        return text
    try:
        path = Path(__file__).resolve().parents[1] / "locales/messages.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        translated = data["messages"].get(text, text)
        return translated if isinstance(translated, str) and translated else text
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return text


class Problem(Exception):
    def __init__(self, code, message, next_step="核实原因后继续；不要重复钱包写操作。", exit_code=1):
        super().__init__(localize(message))
        self.code, self.next_step, self.exit_code = code, localize(next_step), exit_code


def need(code, message, next_step):
    raise Problem(code, message, next_step, 2)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path):
    try:
        with open(path, encoding="utf-8") as stream:
            return json.load(stream)
    except (ValueError, OSError):
        raise Problem("INVALID_RECORD", "安装记录无法读取；未将它当作未安装。") from None


def atomic_json(path, value):
    fd, tmp = tempfile.mkstemp(prefix=".record-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


@contextlib.contextmanager
def lock(path, wait=0):
    import fcntl  # Imported after platform checks; Windows is unsupported.
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    end = time.monotonic() + wait
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= end:
                    need("BUSY", "另一个安装或服务进程正在使用此实例。", "复用已有实例；稍后重新检查，不另起服务。")
                time.sleep(0.05)
        yield fd
    finally:
        os.close(fd)  # Kernel releases locks even after an interrupted process.


def system_asset():
    system, machine = platform.system(), platform.machine().lower()
    if system not in ("Darwin", "Linux"):
        raise Problem("UNSUPPORTED_PLATFORM", "首版自动管理仅支持 macOS/Linux。")
    if system == "Darwin":
        hw = subprocess.run(["sysctl", "-n", "hw.optional.arm64"], capture_output=True, timeout=5)
        if hw.returncode == 0 and hw.stdout.strip() == b"1":
            machine = "arm64"
    arch = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}.get(machine)
    if not arch:
        raise Problem("UNSUPPORTED_PLATFORM", "没有当前 CPU 的已支持发布文件。")
    return "service-" + ("darwin" if system == "Darwin" else "linux") + "-" + arch


def default_root():
    if platform.system() == "Darwin":
        return Path.home() / "Library/Application Support/agent-wallet-mcp"
    return Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "agent-wallet-mcp"


def command(argv, input_text=None):
    try:
        p = subprocess.run(argv, input=input_text or "", text=True, capture_output=True, timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        raise Problem("HOST_COMMAND_FAILED", "宿主命令无法执行或超时，需回读配置确认结果。") from None
    if p.returncode:
        # CLI output may contain tokens or the complete config; never echo it.
        raise Problem("HOST_COMMAND_FAILED", "宿主命令失败，需回读配置确认是否已生效。")
    return p.stdout


class Host:
    def __init__(self, name, profile=None):
        self.name = name
        exe = shutil.which(name)
        if not exe:
            raise Problem("UNSUPPORTED_HOST", "未找到当前宿主 CLI；不会自动安装或升级宿主。")
        self.cli = [exe]
        home = Path.home()
        if name == "openclaw":
            profile = profile or os.environ.get("OPENCLAW_PROFILE")
            if profile and not re.fullmatch(r"[A-Za-z0-9_-]+", profile):
                raise Problem("INVALID_PROFILE", "无法识别当前 OpenClaw profile。")
            if profile:
                self.cli += ["--profile", profile]
            state = Path(os.environ.get("OPENCLAW_STATE_DIR", str(home / (".openclaw-" + profile if profile and profile != "default" else ".openclaw"))))
            self.config = Path(os.environ.get("OPENCLAW_CONFIG_PATH", str(state / "openclaw.json")))
        elif name == "hermes":
            self.config = Path(os.environ.get("HERMES_HOME", str(home / ".hermes"))) / "config.yaml"
        else:
            self.config = Path(os.environ.get("CODEX_HOME", str(home / ".codex"))) / "config.toml"
        if not self.config.is_absolute():
            raise Problem("INVALID_CONFIG_PATH", "宿主配置路径必须是绝对路径。")

    def check_capabilities(self):
        if self.name == "codex":
            specs = [(["mcp", "list", "--help"], ["--json"]), (["mcp", "add", "--help"], ["--url", "COMMAND"])]
        elif self.name == "hermes":
            specs = [(["config", "get", "--help"], ["--json"]), (["config", "set", "--help"], ["key", "value"])]
        else:
            specs = [(["mcp", "show", "--help"], ["--json"]), (["mcp", "add", "--help"], ["--command", "--arg", "--no-probe"])]
        for args, tokens in specs:
            help_text = command(self.cli + args)
            if any(token not in help_text for token in tokens):
                raise Problem("UNSUPPORTED_HOST", "当前 CLI 缺少所需能力，不改配置或自动升级宿主。")

    def servers(self):
        if self.name == "codex":
            args = ["mcp", "list", "--json"]
        elif self.name == "hermes":
            # Full resolved config avoids interpreting a missing key as a CLI error.
            args = ["config", "get", "--json"]
        else:
            args = ["mcp", "show", "--json"]
        try:
            value = json.loads(command(self.cli + args))
            if self.name == "codex":
                if not isinstance(value, list):
                    raise ValueError()
                result = {}
                for row in value:
                    key = row["name"]
                    if key in result:
                        raise ValueError()
                    result[key] = row
            elif self.name == "hermes":
                if not isinstance(value, dict):
                    raise ValueError()
                result = value["mcp_servers"] if "mcp_servers" in value else {}
            else:
                result = value
            if not isinstance(result, dict) or any(not isinstance(v, dict) for v in result.values()):
                raise ValueError()
            return result
        except (ValueError, TypeError, KeyError, AttributeError):
            raise Problem("HOST_CONFIG_UNKNOWN", "无法识别宿主配置，未将它当作没有连接。") from None

    def version(self):
        value = command(self.cli + ["--version"]).strip()
        if not value or len(value) > 256 or len(value.splitlines()) != 1:
            raise Problem("HOST_VERSION_UNKNOWN", "宿主版本无法确定，暂不安装。")
        return value

    def add(self, name, argv):
        if self.name == "codex":
            args = ["mcp", "add", name, "--"] + argv
        elif self.name == "hermes":
            # Native config CLI avoids mcp add's interactive tool picker and probe.
            args = ["config", "set", "mcp_servers." + name, json.dumps({"command": argv[0], "args": argv[1:], "enabled": True})]
        else:
            args = ["mcp", "add", name, "--command", argv[0], "--no-probe"]
            for arg in argv[1:]:
                args += ["--arg=" + arg]
        command(self.cli + args)


def transport(entry):
    t = entry.get("transport", entry)
    return t if isinstance(t, dict) else entry


def matches(entry, argv):
    t = transport(entry)
    return (entry.get("enabled", True) is True and not t.get("url")
            and t.get("command") == argv[0] and t.get("args", []) == argv[1:]
            and not t.get("env") and not t.get("cwd")
            and not entry.get("tools") and not entry.get("toolFilter"))


def wallet_candidates(servers, root):
    names = []
    for name, entry in servers.items():
        t = transport(entry)
        # Only a candidate hint; an explicit --server remains authoritative.
        description = " ".join([name, str(t.get("command", "")), str(t.get("args", []))]).lower()
        if any(word in description for word in ("agent-wallet", "agent_wallet", "coinsdo", str(root).lower())):
            names.append(name)
    return sorted(names)


def existing_data():
    home = Path.home()
    paths = [home / "Library/Application Support/coinsdo-wallet-mcp", home / ".config/coinsdo-wallet-mcp",
             home / "Library/Application Support/coinsdo/wallet-mcp", home / ".local/share/coinsdo/wallet-mcp"]
    return [p for p in paths if p.exists()]


def unmanaged_processes():
    try:
        p = subprocess.run(["ps", "-axo", "pid=,comm="], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        raise Problem("PROCESS_CHECK_FAILED", "无法核实已有本机服务，暂不新装。") from None
    if p.returncode:
        raise Problem("PROCESS_CHECK_FAILED", "无法核实已有本机服务，暂不新装。")
    for line in p.stdout.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) != 2:
            continue
        name = Path(parts[1]).name.lower()
        if name == "service" or "service-darwin-" in name or "service-linux-" in name or "coinsdo-wallet" in name:
            return True
    return False


class OfficialRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlsplit(newurl)
        if parsed.scheme != "https" or parsed.hostname not in ("github.com", "api.github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"):
            raise Problem("UNTRUSTED_REDIRECT", "下载重定向不属于已支持的官方发布主机。")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def official_open(url):
    req = urllib.request.Request(url, headers={"User-Agent": "agent-wallet-mcp", "Accept": "application/json" if url.startswith(RELEASES) else "application/octet-stream"})
    return urllib.request.build_opener(OfficialRedirect()).open(req, timeout=TIMEOUT)


def release(asset):
    version = load_compatibility()["contract_baseline"]["mcp_version"]
    try:
        with official_open(RELEASES + version) as stream:
            info = json.loads(stream.read(2 * 1024 * 1024))
        tag = info["tag_name"]
        if tag != version or info.get("draft") or info.get("prerelease"):
            raise ValueError()
        candidates = [a for a in info["assets"] if a["name"] == asset]
        if len(candidates) != 1:
            raise ValueError()
        item = candidates[0]
        digest = item["digest"]
        if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
            raise ValueError()
        url = item["browser_download_url"]
        expected = "https://github.com/" + REPO + "/releases/download/" + tag + "/" + asset
        if url != expected:
            raise ValueError()
        return {"version": tag, "sha256": digest[7:].lower(), "url": url, "asset": asset}
    except Problem:
        raise
    except urllib.error.HTTPError as exc:
        exc.close()
        raise Problem("RELEASE_UNAVAILABLE", "官方发布信息暂时无法读取。") from None
    except Exception:
        raise Problem("RELEASE_UNAVAILABLE", "未取得完整且可信的稳定版发布信息；未开始替换。") from None


def load_compatibility():
    path = Path(__file__).resolve().parents[1] / "compatibility/manifest.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if (not isinstance(value, dict) or value.get("format") != 1
                or not isinstance(value.get("verified_installations"), list)
                or not isinstance(value.get("contract_baseline"), dict)
                or not isinstance(value["contract_baseline"].get("mcp_version"), str)
                or not re.fullmatch(r"v\d+\.\d+\.\d+", value["contract_baseline"]["mcp_version"])):
            raise ValueError()
        return value
    except (OSError, ValueError):
        raise Problem("COMPATIBILITY_UNKNOWN", "兼容清单缺失或格式错误，未下载程序。") from None


def require_supported_release(info):
    """Keep interrupted installs on the packaged contract; evidence is not an allowlist."""
    if info["version"] != load_compatibility()["contract_baseline"]["mcp_version"]:
        need("UNSUPPORTED_RELEASE", "安装版本与随包契约基线不一致，未下载或注册程序。",
             "核实原安装记录与当前 skill 版本；不要覆盖记录或静默切换版本。")


class Manager:
    def __init__(self, root, host=None, server=None, env=None, required=None):
        self.root = root.absolute()
        self.host, self.server, self.env = host, server, env
        self.required = set(required or ["status"])
        self.result = {"state": "unknown", "stage": "inspect", "completed": [],
                       "installation": "unknown", "connection": "unknown", "protocol": "not_checked",
                       "host_tools": "not_checked", "error": None, "next_step": None}

    def finish(self, state, next_step=None, code=0):
        self.result.update(state=state, next_step=localize(next_step))
        return self.result, code

    def record(self, pending=False):
        path = self.root / ("pending.json" if pending else "installation.json")
        if not path.exists():
            return None
        record = read_json(path)
        try:
            valid = (record["format"] == 1
                     and record["env"] in ("prod", "test")
                     and re.fullmatch(r"[vV]?\d+\.\d+\.\d+", record["version"])
                     and re.fullmatch(r"[0-9a-f]{64}", record["sha256"])
                     and record["binary"] == str(self.root / "service")
                     and record["command"] == [record["binary"], "-t", "stdio", "-e", record["env"]]
                     and record["asset"] == system_asset()
                     and record["url"] == "https://github.com/" + REPO + "/releases/download/" + record["version"] + "/" + record["asset"])
            if not valid:
                raise ValueError()
        except (ValueError, KeyError, TypeError):
            raise Problem("INVALID_RECORD", "安装记录字段不一致；不执行其中的命令。") from None
        if self.env and self.env != record["env"]:
            need("ENV_CONFLICT", "已有安装使用不同环境；没有切换。", "沿用已有环境，或另行明确要求切换环境。")
        if not pending:
            binary = Path(record["binary"])
            if not binary.is_file() or binary.is_symlink() or sha(binary) != record["sha256"]:
                raise Problem("INSTALLATION_CHANGED", "程序缺失或散列与安装记录不符；不自动覆盖或执行。")
            self.result.update(installation="installed", version=record["version"], environment=record["env"])
        return record

    def launch(self):
        return [sys.executable, str(Path(__file__).resolve()), "run", "--root", str(self.root)]

    def inspect(self):
        system_asset()
        self.host.check_capabilities()
        servers = self.host.servers()
        if self.server:
            selected = self.server if self.server in servers else None
            if not selected:
                need("CONNECTION_NOT_FOUND", "指定连接不存在；未改为默认新装。", "确认原连接名称或恢复原配置。")
        else:
            candidates = wallet_candidates(servers, self.root)
            if len(candidates) > 1:
                self.result["candidates"] = candidates
                need("MULTIPLE_CONNECTIONS", "存在多个钱包连接。", "由 agent 根据任务定位连接，仍有歧义时请用户选择。")
            selected = candidates[0] if candidates else None
        if selected:
            self.result.update(connection="configured", server=selected)
            if not matches(servers[selected], self.launch()):
                self.result["installation"] = "external"
                return self.finish("existing_connection", "通过宿主复用并核实原连接，不另行安装或启动。")
        record = self.record()
        if record:
            return self.finish("pending_host_load" if selected else "installed", "由宿主加载已有服务并验证 status。", 2 if selected else 0)
        if selected:
            raise Problem("MANAGED_RECORD_MISSING", "已有受管连接但缺少有效安装记录，暂不新装。")
        pending = self.record(pending=True)
        if pending:
            return self.finish("interrupted_install", "按锁定的原发布信息继续 ensure。")
        if self.root.exists() and any(p.name not in ("install.lock", "run.lock") for p in self.root.iterdir()):
            need("UNMANAGED_INSTALLATION", "安装目录有未识别内容，暂不覆盖。", "先定位原安装，不删除现有文件。")
        if existing_data() or unmanaged_processes():
            need("EXISTING_SERVICE_OR_DATA", "发现已有服务或钱包数据，暂不按首次安装处理。", "由 agent 定位并连接原实例；无法唯一确定时只澄清目标。")
        self.result["installation"] = "not_installed"
        return self.finish("not_installed", "首次用途不明时问实际使用还是测试体验，再执行 ensure。")

    def install(self):
        pending = self.record(pending=True)
        if not pending:
            if not self.env:
                need("NEED_ENVIRONMENT", "首次安装用途尚未明确。", "询问：实际使用还是测试体验？")
            candidate = release(system_asset())
            require_supported_release(candidate)
            pending = dict(candidate, format=1, env=self.env, binary=str(self.root / "service"))
            pending["command"] = [pending["binary"], "-t", "stdio", "-e", self.env]
            atomic_json(self.root / "pending.json", pending)
        else:
            require_supported_release(pending)
        binary, partial = self.root / "service", self.root / "service.download"
        if binary.exists():
            if binary.is_symlink() or sha(binary) != pending["sha256"]:
                raise Problem("INSTALLATION_CHANGED", "中断安装留下的程序不匹配，未覆盖。")
        else:
            self.result["stage"] = "download"
            try:
                with official_open(pending["url"]) as response, open(partial, "wb") as stream:
                    total = 0
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > MAX_BYTES:
                            raise Problem("DOWNLOAD_TOO_LARGE", "发布文件超过支持的大小。")
                        stream.write(chunk)
                    stream.flush()
                    os.fsync(stream.fileno())
            except Problem:
                raise
            except urllib.error.HTTPError as exc:
                exc.close()
                raise Problem("DOWNLOAD_FAILED", "下载未完成；保留锁定发布信息以便恢复。") from None
            except Exception:
                raise Problem("DOWNLOAD_FAILED", "下载未完成；保留锁定发布信息以便恢复。") from None
            if sha(partial) != pending["sha256"]:
                partial.unlink()
                raise Problem("DIGEST_MISMATCH", "下载文件校验不一致，已删除暂存文件，未执行。")
            partial.chmod(0o700)
            os.replace(partial, binary)
        atomic_json(self.root / "installation.json", pending)
        (self.root / "pending.json").unlink(missing_ok=True)
        self.result["completed"].append("installed")
        return self.record()

    def ensure(self):
        self.inspect()
        if self.result["state"] == "existing_connection":
            return self.finish("existing_connection", "使用宿主核实原连接；不替换、不重启、不切换环境。")
        if not self.record() and not self.record(pending=True) and not self.env:
            need("NEED_ENVIRONMENT", "首次安装用途尚未明确。", "询问：实际使用还是测试体验？")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with lock(self.root / "install.lock", wait=5):
            # Repeat discovery under the lock to close concurrent install races.
            self.inspect()
            if self.result["state"] == "existing_connection":
                return self.finish("existing_connection", "使用宿主核实原连接。")
            if not self.record():
                self.install()
            servers = self.host.servers()
            equivalents = [name for name, entry in servers.items() if matches(entry, self.launch())]
            if equivalents:
                name = equivalents[0]
            else:
                name = self.server or SERVER
                if name in servers:
                    need("CONFIG_CONFLICT", "同名宿主配置指向其他目标，未覆盖。", "复用原连接或明确选择另一个名称。")
                self.result["stage"] = "configure"
                config = self.host.config
                before_hash = sha(config) if config.exists() else None
                if config.exists():
                    backup_dir = self.root / "backups"
                    backup_dir.mkdir(mode=0o700, exist_ok=True)
                    backup = backup_dir / (self.host.name + "-" + str(time.time_ns()) + ".config")
                    shutil.copyfile(config, backup)
                    backup.chmod(0o600)
                    self.result["backup"] = str(backup)
                if (sha(config) if config.exists() else None) != before_hash:
                    raise Problem("CONFIG_CHANGED", "宿主配置在准备过程中变化，未执行写入。")
                # CLI may have mutated state even when it fails. Never retry here.
                try:
                    self.host.add(name, self.launch())
                except Problem:
                    self.result["connection"] = "unknown_after_write"
                    raise
                self.result["completed"].append("configuration_written")
                after = self.host.servers()
                if not matches(after.get(name, {}), self.launch()) or {k: v for k, v in after.items() if k != name} != servers:
                    self.result["connection"] = "unknown_after_write"
                    raise Problem("CONFIG_VERIFY_FAILED", "配置回读不符合预期；保留备份，未自动覆盖回滚。")
            self.result.update(connection="configured", server=name, stage="host_load")
            return self.finish("pending_host_load", "让当前宿主刷新工具；不能热加载时重新连接/打开会话，然后核对 status 和所需工具。", 2)

    def verify(self):
        self.result["stage"] = "verify"
        record = self.record()
        if not record:
            need("NOT_INSTALLED", "没有受管安装可探测。", "已有外部连接请用宿主验证；否则先执行 ensure。")
        # The probe owns only its subprocess. A live run refuses a second process.
        status = probe(self.launch(), self.required)
        if status.get("ServerVersion", "").lstrip("vV") != record["version"].lstrip("vV") or status.get("environmentName") != record["env"] or status.get("transportType") != "stdio":
            raise Problem("STATUS_MISMATCH", "运行版本、环境或传输方式与安装记录不一致。")
        self.result.update(protocol="verified", stage="host_load")
        self.result["completed"].append("isolated_protocol_probe")
        return self.finish("protocol_verified", "独立探测通过；仍须当前宿主加载工具并验证 status，才可继续钱包业务。")

    def run(self):
        system_asset()
        record = self.record()
        if not record:
            raise Problem("NOT_INSTALLED", "受管程序尚未安装。")
        os.chdir(self.root)
        with lock(self.root / "run.lock") as fd:
            os.set_inheritable(fd, True)  # Keep exclusivity for the service lifetime.
            os.execv(record["binary"], record["command"])


def probe(argv, required):
    try:
        p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except OSError:
        raise Problem("START_FAILED", "无法启动受管服务。") from None
    selector = selectors.DefaultSelector()
    selector.register(p.stdout, selectors.EVENT_READ)
    buffer = b""
    total = 0
    sequence = 0

    def send(obj):
        try:
            p.stdin.write((json.dumps(obj) + "\n").encode())
            p.stdin.flush()
        except (OSError, BrokenPipeError):
            raise Problem("START_FAILED", "服务已退出，无法完成协议验证。") from None

    def request(method, params):
        nonlocal buffer, total, sequence
        sequence += 1
        send({"jsonrpc": "2.0", "id": sequence, "method": method, "params": params})
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if b"\n" not in buffer:
                if not selector.select(max(0, deadline - time.monotonic())):
                    break
                chunk = os.read(p.stdout.fileno(), 65536)
                if not chunk:
                    raise Problem("START_FAILED", "服务在协议验证完成前退出。")
                buffer += chunk
                total += len(chunk)
                if total > 4 * 1024 * 1024:
                    raise Problem("PROTOCOL_LIMIT", "协议返回超出验证上限。")
                continue
            line, buffer = buffer.split(b"\n", 1)
            try:
                value = json.loads(line)
            except ValueError:
                raise Problem("PROTOCOL_INVALID", "服务 stdout 含非 MCP JSON 数据。") from None
            if not isinstance(value, dict) or value.get("jsonrpc") != "2.0":
                raise Problem("PROTOCOL_INVALID", "服务返回无效协议消息。")
            if "id" not in value:
                continue
            if value.get("id") != sequence or "error" in value or not isinstance(value.get("result"), dict):
                raise Problem("PROTOCOL_ERROR", "服务返回错误或不匹配的响应。")
            return value["result"]
        raise Problem("PROTOCOL_TIMEOUT", "服务协议验证超时。")

    try:
        init = request("initialize", {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "agent-wallet-mcp-probe", "version": "1"}})
        capabilities = init.get("capabilities")
        if init.get("protocolVersion") not in ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05") or not isinstance(capabilities, dict) or not isinstance(capabilities.get("tools"), dict):
            raise Problem("INITIALIZE_INVALID", "服务未协商受支持协议或工具能力。")
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        names, cursors, cursor = set(), set(), None
        for _ in range(100):
            result = request("tools/list", {"cursor": cursor} if cursor else {})
            rows = result.get("tools")
            if not isinstance(rows, list) or any(not isinstance(t, dict) or not isinstance(t.get("name"), str) for t in rows):
                raise Problem("TOOLS_INVALID", "无法识别服务工具列表。")
            names.update(t["name"] for t in rows)
            cursor = result.get("nextCursor")
            if cursor is None:
                break
            if not isinstance(cursor, str) or not cursor or cursor in cursors:
                raise Problem("TOOLS_INVALID", "工具列表分页重复或无效。")
            cursors.add(cursor)
        else:
            raise Problem("PROTOCOL_LIMIT", "工具列表超过验证上限。")
        if not (required | {"status"}).issubset(names):
            raise Problem("TOOLS_MISSING", "服务缺少本次任务所需工具；没有自动升级。")
        result = request("tools/call", {"name": "status", "arguments": {}})
        if result.get("isError"):
            raise Problem("STATUS_FAILED", "服务 status 返回工具错误。")
        status = result.get("structuredContent")
        content = result.get("content", [])
        if not isinstance(content, list):
            raise Problem("STATUS_INVALID", "status 内容格式无效。")
        texts = [t.get("text") for t in content if isinstance(t, dict) and t.get("type") == "text"]
        parsed = []
        for value in texts:
            try:
                parsed.append(json.loads(value))
            except (ValueError, TypeError):
                raise Problem("STATUS_INVALID", "status 文本无法解析。") from None
        if status is None and len(parsed) == 1:
            status = parsed[0]
        if not isinstance(status, dict) or any(value != status for value in parsed):
            raise Problem("STATUS_INVALID", "status 结构缺失或不同表示相互冲突。")
        if any(not isinstance(status.get(k), str) or not status[k] for k in ("ServerVersion", "environmentName", "transportType")):
            raise Problem("STATUS_INVALID", "status 缺少验证所需字段。")
        return status
    finally:
        selector.close()
        with contextlib.suppress(OSError):
            p.stdin.close()
        p.stdout.close()
        if p.poll() is None:
            p.terminate()
        try:
            p.wait(timeout=3)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait(timeout=3)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Problem("INVALID_ARGUMENTS", "命令参数无效；使用 --help 查看接口。")


def main(argv=None):
    manager = None
    running = (argv or sys.argv[1:])[:1] == ["run"]
    try:
        parser = Parser(description=__doc__)
        parser.add_argument("action", choices=("inspect", "ensure", "run", "verify"))
        parser.add_argument("--host", choices=("codex", "hermes", "openclaw"))
        parser.add_argument("--profile", help="OpenClaw current profile only")
        parser.add_argument("--server", help="Existing wallet connection name")
        parser.add_argument("--env", choices=("prod", "test"))
        parser.add_argument("--root", type=Path, default=default_root())
        parser.add_argument("--require-tool", action="append", default=[])
        args = parser.parse_args(argv)
        system_asset()
        if args.profile and args.host != "openclaw":
            raise Problem("INVALID_PROFILE", "--profile 仅用于 OpenClaw；其他宿主沿用当前环境。")
        if args.server and not re.fullmatch(r"[A-Za-z0-9_-]+", args.server):
            raise Problem("INVALID_SERVER", "连接名称只能包含字母、数字、下划线和连字符。")
        if args.action in ("inspect", "ensure") and not args.host:
            need("NEED_HOST", "需要 agent 指定当前宿主。", "agent 传 --host codex|hermes|openclaw，不让用户猜测。")
        host = Host(args.host, args.profile) if args.action in ("inspect", "ensure") else None
        manager = Manager(args.root, host, args.server, args.env, args.require_tool)
        result = getattr(manager, args.action)()
        if args.action != "run":
            value, code = result
            print(json.dumps(value, ensure_ascii=False))
            return code
    except (Problem, OSError, ValueError, KeyboardInterrupt) as exc:
        if not isinstance(exc, Problem):
            exc = Problem("INTERRUPTED" if isinstance(exc, KeyboardInterrupt) else "LOCAL_FAILURE", "操作中断或本地读写失败；需核实当前状态后继续。")
        value = manager.result if manager else {"completed": [], "stage": "arguments"}
        value.update(state="needs_action" if exc.exit_code == 2 else "failed", error={"code": exc.code, "message": str(exc)}, next_step=exc.next_step)
        print(json.dumps(value, ensure_ascii=False), file=sys.stderr if running else sys.stdout)
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(main())
