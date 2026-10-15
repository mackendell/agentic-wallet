#!/usr/bin/env python3
"""`hermes skills install` from a local checkout instead of GitHub (dev only, for runs before a push).

Usage: <hermes venv python> dev/hermes_local_install.py <local repo> skills install <owner>/agentic-wallet/skills/coinwallet [--yes]

It runs the real Hermes install code (quarantine, the same security scan, lock file, install path).
Only the GitHub fetch is replaced: the bundle is read from <local repo>/skills/coinwallet with the same
file rules as Hermes' GitHub source (dotfiles, __pycache__ and *.pyc are skipped).
"""
import os
import sys
from pathlib import Path

repo = Path(sys.argv[1]).resolve()
sys.argv = ["hermes"] + sys.argv[2:]
agent_dir = Path(os.environ.get("HERMES_AGENT_DIR", str(Path.home() / ".hermes" / "hermes-agent")))
sys.path.insert(0, str(agent_dir))

from tools import skills_hub_github as gh  # noqa: E402
from tools.skills_hub_models import SkillBundle, SkillMeta, _parse_frontmatter  # noqa: E402

SUFFIX = "/agentic-wallet/skills/coinwallet"
_fetch, _inspect = gh.GitHubSource.fetch, gh.GitHubSource.inspect


def _local_dir(identifier):
    return repo / "skills" / "coinwallet" if identifier.rstrip("/").endswith(SUFFIX) else None


def fetch(self, identifier):
    skill = _local_dir(identifier)
    if skill is None:
        return _fetch(self, identifier)
    files = {}
    for path in sorted(skill.rglob("*")):
        rel = path.relative_to(skill).as_posix()
        if path.is_file() and not gh._skip_bundle_file(rel):
            data = path.read_bytes()
            try:
                files[rel] = data.decode("utf-8")
            except UnicodeDecodeError:
                files[rel] = data
    return SkillBundle(name="coinwallet", files=files, source="github", identifier=identifier,
                       trust_level=self.trust_level_for(identifier),
                       metadata={"source_url": "file://" + str(skill), "source_revision": ""})


def inspect(self, identifier):
    skill = _local_dir(identifier)
    if skill is None:
        return _inspect(self, identifier)
    fm = _parse_frontmatter((skill / "SKILL.md").read_text(encoding="utf-8"))
    repo_id = identifier.rstrip("/")[: -len("/skills/coinwallet")]
    return SkillMeta(name=fm.get("name", "coinwallet"), description=str(fm.get("description", "")),
                     source="github", identifier=identifier, trust_level=self.trust_level_for(identifier),
                     repo=repo_id, path="skills/coinwallet", tags=[], extra={})


gh.GitHubSource.fetch, gh.GitHubSource.inspect = fetch, inspect

from hermes_cli.main import main  # noqa: E402

main()
