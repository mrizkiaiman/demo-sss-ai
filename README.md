# SSS

SSS is a Python CLI for installing shared Skills and configuring MCP servers on developer workstations. It supports macOS, Linux, and Windows through WSL2. Native Windows Git is not supported. The CLI writes configuration with Python and does not require Ansible.

## What it does

- Installs Skills packages for:
  - Kiro
  - Claude Code
  - OpenCode
  - Antigravity IDE
  - Codex
- Configures selected local stdio and remote HTTP MCP servers from `catalogue/mcp.yml`.
- Optionally installs shared Gitleaks rules and a global Git pre-commit hook.
- Shows planned file changes and asks before applying them.
- Merges selected MCP entries into existing client configuration. It keeps unrelated settings, backs up files it changes, and stops before writing MCP files if a selected configuration is malformed.

`code-review` and `security-review` are required and stay selected. Other Skills and MCP servers are optional. The CLI does not install or update AI client applications or native MCP binaries. Clients start local MCP servers and handle remote OAuth after setup. If `codebase-memory-mcp` is not installed, the CLI uses the pinned `npx` command from the catalogue.

SSS does not enforce AI permissions, file or network access, data privacy, or model routing. Ignore files and Gitleaks can reduce accidental exposure, but they do not stop sensitive data from reaching an LLM. See [SECURITY.md](SECURITY.md) for the enforcement boundary.

## Install

Requirements:

- Python 3.9 or later.
- Git.
- Node.js and npm for the setup command.
- Node.js if the CLI needs the `npx` fallback for `codebase-memory-mcp`.
- Gitleaks on `PATH` if you select the security component.

Clone the repository and start the setup menu:

~~~bash
git clone https://github.com/mrizkiaiman/demo-sss-ai.git sss-ai-cli
cd sss-ai-cli
npm run setup
~~~

The setup command creates `.venv`, installs the Python dependencies, and opens the menu. Skills are selected automatically. Choose whether to configure MCP servers or the optional security setup too.

- Use arrow keys to move, Space to toggle, and Enter to continue.
- In the Skills menu, `code-review` and `security-review` stay selected.
- Press `q` to cancel.
- Review the preview, then confirm to apply.

The npm script has no npm package dependencies. To set up and start the Python CLI directly:

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m cli
~~~

## Make changes

- **Add a Skill.** Create `skills/<skill-name>/` with a `SKILL.md`, then add the Skill to `catalogue/skills.yml`. Run `.venv/bin/python -m cli --validate` to check the catalogue and public Skill packages.
- **Add an MCP server.** Add its local command and arguments, or remote URL, to `catalogue/mcp.yml`. The CLI uses a native `codebase-memory-mcp` binary when available, then falls back to the pinned `npx` command.
- **Change client paths.** Edit `config/clients.yml`.
- **Change the Gitleaks setup.** Edit the files under `security/`.

The CLI writes only selected MCP entries and validates all selected client configurations before writing any of them. JSONC comments and formatting are normalized to JSON. TOML comments and formatting are preserved. Deselecting a Skill does not remove files already installed on a workstation.

## Commands

~~~bash
# Open the setup menu
npm run setup

# Preview without applying changes
.venv/bin/python -m cli --check

# Validate catalogues and public Skill packages
.venv/bin/python -m cli --validate

# Preview against another absolute home directory
.venv/bin/python -m cli --target-home /absolute/home/path --check
~~~

Add `--verbose` to list planned file paths. The CLI does not print MCP configuration values or hook contents.

Use `--target-home /absolute/home/path` to preview or apply against another home directory. Add `--check` to preview without applying.

## Security hook

Install Gitleaks first, then select **Gitleaks and global Git hook** in the setup menu. SSS installs rules at `~/.config/company-ai/gitleaks.toml`. It uses an existing global `core.hooksPath` when configured and preserves and chains an existing executable hook as `pre-commit.company-original`. Otherwise, it installs the hook under `~/.config/company-ai/git-hooks/` and configures Git to use that path.

The hook scans staged changes. `git commit --no-verify` bypasses it. Gitleaks detects secrets, not general PII.

## Project checks

GitHub Actions and GitLab CI install the Python dependencies, check Python syntax, and verify that the CLI starts. They also scan Git history with Gitleaks.

## Repository layout

~~~text
catalogue/          Shared Skills and MCP catalogues
config/             Client configuration paths
security/           Gitleaks rules and Git hook
skills/             Public Skill packages
cli/                Python CLI and configuration writer
package.json        Setup shortcut
~~~
