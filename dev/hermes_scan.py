#!/usr/bin/env python3
"""Run Hermes' own skill security scanner (the one `hermes skills install` runs) on skills/coinwallet.

Usage: <hermes venv python> dev/hermes_scan.py [skill_dir]
Default Hermes checkout: ~/.hermes/hermes-agent (override with HERMES_AGENT_DIR).
Exit 1 if any finding is high or critical (that blocks a community install).
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
agent_dir = Path(os.environ.get("HERMES_AGENT_DIR", str(Path.home() / ".hermes" / "hermes-agent")))
sys.path.insert(0, str(agent_dir))

from tools.skills_guard import format_scan_report, scan_skill  # noqa: E402

skill = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "skills" / "coinwallet"
result = scan_skill(skill, source="mackendell/agentic-wallet")
print(format_scan_report(result))
bad = [f for f in result.findings if f.severity in ("high", "critical")]
print("verdict:", result.verdict, "| trust:", result.trust_level, "| high/critical:", len(bad))
sys.exit(1 if bad else 0)
