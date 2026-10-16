#!/usr/bin/env python3
"""Seam 2: repo check, no model. Run in CI and before every release.

Usage:
  python3 dev/check_repo.py                 layout, size caps, versions, mcp-tested.json
  python3 dev/check_repo.py --tag v0.1.0    also require VERSION and both plugin.json versions to match the tag
  python3 dev/check_repo.py --runs FILE     also check Seam 1 run records (JSON lines): each task read SKILL.md + one card
                                            (a send: + one chain file; setup: setup.md + one setup-<host>.md + join.md)
Exit 1 on any problem. The tag defaults to $GITHUB_REF_NAME when $GITHUB_REF_TYPE is "tag".
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "coinwallet"
CARDS = SKILL / "references" / "cards"
CHAINS = SKILL / "references" / "chains"

SKILL_MAX, CARD_MAX, CHAIN_MAX = 4096, 3072, 1536
CARD_NAMES = {"setup", "setup-claude-code", "setup-codex", "setup-hermes", "setup-openclaw", "join", "wallet",
              "address", "send", "approve", "history", "update"}
CHAIN_NAMES = {"evm", "utxo", "tron", "xrp", "sol", "xlm"}
REQUIRED = [".claude-plugin/marketplace.json", ".claude-plugin/plugin.json", ".codex-plugin/plugin.json",
            "skills/coinwallet/SKILL.md", "skills/coinwallet/VERSION", "skills/coinwallet/mcp-tested.json",
            "skills/coinwallet/scripts/mcp.py", "skills/coinwallet/references/cards",
            "skills/coinwallet/references/chains", "README.md"]
FORBIDDEN = ["INSTALL.md", "MANIFEST.json", "VERSION", "skills/agent-wallet", "skills/agent-wallet-mcp",
             ".agents/plugins/marketplace.json", ".mcp.json", "skills/coinwallet/agents/openai.yaml"]
TOKEN_CASES = {"token"}  # Seam 1 cases where a send also reads the address card (#20 flow)
ASSETS = ["service-darwin-amd64", "service-darwin-arm64", "service-linux-amd64", "service-linux-arm64"]

problems = []


def problem(text):
    problems.append(text)


def size_cap(path, cap):
    size = path.stat().st_size
    if size > cap:
        problem(f"{path.relative_to(ROOT)} is {size} bytes, cap {cap}")


def load_json(rel):
    try:
        return json.loads((ROOT / rel).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        problem(f"{rel}: not valid JSON ({exc})")
        return {}


def vtuple(text):
    match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", text or "")
    return tuple(int(x) for x in match.groups()) if match else None


def check_layout():
    for rel in REQUIRED:
        if not (ROOT / rel).exists():
            problem(f"missing {rel}")
    for rel in FORBIDDEN:
        if (ROOT / rel).exists():
            problem(f"old or forbidden file present: {rel}")
    skills = sorted(p.name for p in (ROOT / "skills").iterdir() if p.is_dir())
    if skills != ["coinwallet"]:
        problem(f"skills/ must hold only coinwallet, found {skills}")
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    front = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not front or not re.search(r"^name: coinwallet$", front.group(1), re.M):
        problem("SKILL.md frontmatter must have name: coinwallet")
    if not front or not re.search(r"^description: .+", front.group(1), re.M):
        problem("SKILL.md frontmatter needs a description")
    if "scripts/mcp.py" not in text:
        problem("SKILL.md must name scripts/mcp.py literally (Hermes fallback copy)")
    size_cap(SKILL / "SKILL.md", SKILL_MAX)
    names = set()
    for card in sorted(CARDS.glob("*")):
        if card.suffix != ".md" or card.stem not in CARD_NAMES:
            problem(f"unknown card file {card.relative_to(ROOT)}")
            continue
        names.add(card.stem)
        size_cap(card, CARD_MAX)
    for missing in sorted(CARD_NAMES - names):
        problem(f"missing card references/cards/{missing}.md")
    chains = set()
    for chain in sorted(CHAINS.glob("*")):
        if chain.suffix != ".md" or chain.stem not in CHAIN_NAMES:
            problem(f"unknown chain file {chain.relative_to(ROOT)}")
            continue
        chains.add(chain.stem)
        size_cap(chain, CHAIN_MAX)
        body = chain.read_text(encoding="utf-8")
        for label in ("Gas coin:", "Explorer:", "Checked:"):
            if not re.search(r"^\W*" + re.escape(label), body, re.M):
                problem(f"{chain.relative_to(ROOT)} needs a '{label}' line")
    for missing in sorted(CHAIN_NAMES - chains):
        problem(f"missing chain file references/chains/{missing}.md")
    check_allow_list()


def check_allow_list():
    """The send card's allow-list line: `abbreviation` codes → chain file, e.g. "ETH, BSC → evm.md; TRX → tron.md"."""
    send = CARDS / "send.md"
    if not send.exists():
        return
    line = next((l for l in send.read_text(encoding="utf-8").splitlines() if "by `abbreviation`" in l), "")
    pairs = re.findall(r"((?:[A-Z][A-Z0-9_]*,\s*)*[A-Z][A-Z0-9_]*)\s*→\s*([a-z0-9-]+)\.md", line)
    if not pairs:
        problem("send card needs its allow-list line (\"by `abbreviation`: CODE, CODE → file.md; ...\")")
    codes = set()
    for group, name in pairs:
        if not (CHAINS / (name + ".md")).exists():
            problem(f"send card maps {group} to chains/{name}.md, which does not exist")
        for code in re.split(r",\s*", group):
            if code in codes:
                problem(f"send card lists {code} twice")
            codes.add(code)
            body = (CHAINS / (name + ".md")).read_text(encoding="utf-8") if (CHAINS / (name + ".md")).exists() else ""
            if not re.search(r"\b" + re.escape(code) + r"\b", body):
                problem(f"chains/{name}.md never names {code}")


def check_manifests(tag):
    market = load_json(".claude-plugin/marketplace.json")
    plugins = market.get("plugins") or [{}]
    if market.get("name") != "coinsdo" or plugins[0].get("name") != "coinwallet" or plugins[0].get("source") != "./":
        problem('marketplace.json must be marketplace "coinsdo", plugin "coinwallet", source "./"')
    claude, codex = load_json(".claude-plugin/plugin.json"), load_json(".codex-plugin/plugin.json")
    if claude.get("name") != "coinwallet" or codex.get("name") != "coinwallet":
        problem("both plugin.json files must be named coinwallet")
    if codex.get("skills") != "./skills/":
        problem('.codex-plugin/plugin.json must have "skills": "./skills/"')
    version = (SKILL / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        problem(f"skills/coinwallet/VERSION must be X.Y.Z, found {version!r}")
    for label, data in (("claude", claude), ("codex", codex)):
        if data.get("version") != version:
            problem(f"{label} plugin.json version {data.get('version')!r} != VERSION {version!r}")
    if tag and tag != "v" + version:
        problem(f"tag {tag} != v{version}")


def check_tested():
    data = load_json("skills/coinwallet/mcp-tested.json")
    minimum = vtuple(data.get("minimum"))
    tested = data.get("tested")
    if not minimum or not isinstance(tested, dict) or not tested:
        problem("mcp-tested.json needs minimum vX.Y.Z and a non-empty tested map")
        return
    versions = []
    for name, hashes in tested.items():
        if not vtuple(name):
            problem(f"mcp-tested.json: bad version {name!r}")
            continue
        versions.append(vtuple(name))
        for asset in ASSETS:
            if not re.fullmatch(r"[0-9a-f]{64}", str((hashes or {}).get(asset, ""))):
                problem(f"mcp-tested.json: {name} needs a sha256 for {asset}")
    if versions and minimum > max(versions):
        problem("mcp-tested.json: minimum is newer than the newest tested version")
    for name in data.get("no_fallback", []):
        if name not in tested:
            problem(f"mcp-tested.json: no_fallback names untested {name}")


def check_runs(path):
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        run = json.loads(line)
        files = [f for f in run.get("skill_files_read", []) if f != "SKILL.md"]
        cards = [f for f in files if f.startswith("references/cards/")]
        chains = [f for f in files if f.startswith("references/chains/")]
        if run.get("case") == "setup":
            cards = [c for c in cards if c not in ("references/cards/setup.md", "references/cards/join.md")]
            ok = len(cards) <= 1 and all(c.startswith("references/cards/setup-") for c in cards) and not chains
        else:
            send = "references/cards/send.md" in cards
            if send and run.get("case") in TOKEN_CASES:  # token not in the wallet: send card → address card
                cards = [c for c in cards if c != "references/cards/address.md"]
            ok = len(cards) <= 1 and len(chains) <= (1 if send else 0)
        if not ok:
            problem(f"{path}:{number} ({run.get('case')}) read too many skill files: {files}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default=os.environ.get("GITHUB_REF_NAME") if os.environ.get("GITHUB_REF_TYPE") == "tag" else None)
    parser.add_argument("--runs")
    args = parser.parse_args()
    check_layout()
    check_manifests(args.tag)
    check_tested()
    if args.runs:
        check_runs(args.runs)
    for text in problems:
        print("FAIL", text)
    print("repo check:", "FAIL" if problems else "ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
