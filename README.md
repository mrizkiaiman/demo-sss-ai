# SSS AI Workstation Setup

SSS is a Python CLI for installing shared Skills packages and configuring MCP servers in developer AI clients. It supports macOS, Linux, and Windows through WSL2. Native Windows Git is not supported.

The CLI applies local configuration directly with Python. It has no Ansible runtime dependency.

## What it manages

- Skill packages from `skills/` for Kiro, Claude Code, OpenCode, Antigravity IDE, and Codex.
- Local stdio and remote HTTP MCP entries from `catalogue/mcp.yml`.
- Optional shared Gitleaks rules and a global Git pre-commit hook.
- Existing client configuration is merged for selected MCP servers. Unrelated settings and servers are retained, changed files are backed up, and malformed configuration stops before any MCP files are written.

`code-review` and `security-review` are mandatory. The Skills component is automatically selected and cannot be deselected while required Skills are listed in the catalogue. Other Skills and all MCP servers are optional. The CLI does not install or update AI client applications or native MCP binaries. The MCP client starts local servers and handles remote OAuth after configuration. Gitleaks is a separate executable that must already be installed if the security component is selected.

SSS does not enforce AI permissions, file or network access, data privacy, or model routing. Ignore files and Gitleaks reduce accidental exposure but do not guarantee that sensitive data cannot reach an LLM.

## Install

Requirements:

- Python 3.9 or later.
- Git.
- Node.js and npm to use the one-command setup below.
- Node.js for the `npx` fallback if running the Python CLI directly and selecting `codebase-memory-mcp`.
- Gitleaks on PATH if enabling the security component.

## Run the CLI

Open Terminal in the project folder and run:

```bash
npm run setup
```

This creates the Python environment, installs the required packages, and opens the setup menu. The Skills component is automatically selected. Choose whether to configure MCP servers or the optional security setup too. In the Skills menu, `code-review` and `security-review` are marked **MANDATORY** and stay selected. Use the arrow keys to move, Space to toggle, Enter to continue, and `q` to cancel. The CLI previews changes and asks before applying them.

The npm script has no npm package dependencies. To set up and launch it directly with Python instead, run:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m cli
```

Preview only:

```bash
.venv/bin/python -m cli --check
```

Validate catalogues and every public Skill package without changing the workstation:

```bash
.venv/bin/python -m cli --validate
```

Use another absolute home directory for a preview or apply:

```bash
.venv/bin/python -m cli --target-home /absolute/home/path --check
```

`--verbose` lists changed file paths. It never prints MCP configuration values or hook contents.

## Configuration

- `catalogue/skills.yml` is the public Skills catalogue and menu grouping.
- `catalogue/mcp.yml` is the MCP server catalogue.
- `config/clients.yml` maps each client to its global Skills and MCP locations.
- `cli/mcp_config.py` translates shared MCP definitions into each client's format.
- `security/` contains the shared Gitleaks rules and hook.

Add a Skill by adding its package under `skills/<name>/` with a `SKILL.md`, then add its name to `catalogue/skills.yml`.

Add an MCP server by adding a command and arguments for a local server, or a URL for a remote server, to `catalogue/mcp.yml`. The CLI detects an installed native `codebase-memory-mcp` binary. Otherwise, it uses the catalogue's pinned `npx` command when Node.js is available.

The CLI writes only selected MCP entries. It validates all selected client configs before writing any of them. JSONC comments and formatting are normalized to JSON. TOML comments and formatting are preserved. It does not delete deselected Skills or stale files from existing packages.

## Security hook

Install Gitleaks first, then choose **Gitleaks and global Git hook** in the setup menu. SSS installs rules at `~/.config/company-ai/gitleaks.toml`. It uses an existing global `core.hooksPath` when one is configured and preserves an existing executable `pre-commit` hook as `pre-commit.company-original`. Otherwise, it installs the hook under `~/.config/company-ai/git-hooks/` and configures Git to use that path.

The hook scans staged changes. `git commit --no-verify` bypasses it. Gitleaks detects secrets and is not a general PII detector. See [SECURITY.md](SECURITY.md) for the enforcement boundary.

## Project checks

GitHub Actions and GitLab CI install the Python dependencies, check Python syntax, and verify that the CLI starts. They also scan Git history with Gitleaks.

## Layout

```text
catalogue/          Shared Skills and MCP catalogues
config/             Client configuration paths
security/           Gitleaks rules and Git hook
skills/             Public Skill packages
cli/                Python CLI and configuration writer
```
