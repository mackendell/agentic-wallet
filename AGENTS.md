## Agent skills

### Issue tracker

Issues live in GitHub Issues for `mackendell/agentic-wallet`, managed with the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Dev tools (not shipped in the skill)

- `python3 dev/check_repo.py`: layout, size caps, versions (also runs in CI).
- `python3 tests/test_mcp_cli.py` (macOS) and `dev/linux_mcp_tests.sh` (Docker): `scripts/mcp.py` against real MCP releases, in throwaway homes with a throwaway `-u` account.
- `~/.hermes/hermes-agent/venv/bin/python dev/hermes_scan.py`: Hermes' install security scan; any high/critical finding blocks a release.
- `python3 dev/hermes_runner.py --case setup --runs 3`: Hermes headless runs, one JSON line per run. `--source local` installs this checkout instead of GitHub `main`. Cases and checks: `dev/test_cases.py`; the agent reaches the MCP service only through `dev/mcp_proxy.py` (logs calls, read tools only on real wallets).
