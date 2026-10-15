# SSS

SSS is a thin launcher/installer for developers. It selects and installs **Skills** and **MCP** configuration using each AI client's native syntax. SSS is not a runtime orchestrator, policy proxy, or replacement for an AI client.

The primary use case is developers. QA is supported as an additional use case through selected Skills.

## MVP contract

- Users select clients, Skills, and MCP servers through the existing menu.
- Installation scope is `global` or `project`.
- Project-level installation writes below the selected project root, not `$HOME`.
- If scope is omitted during an interactive session, SSS asks the user. Non-interactive sessions must use `--scope global` or `--scope project`.
- SSS does not create `.sss`, `sss.yml`, or `sss.lock`.
- Existing configuration is not overwritten by default. Conflicts are skipped and shown in the preview.
- `--update` and `--force` allow replacement of selected items, while still using preview, confirmation, backups, and atomic writes.
- The five existing clients remain available and are shown with the capability matrix.
- OS is shown as a compatibility label. OS is not used as a large installation-folder category.

## Native destinations

All paths below are relative to the selected scope root.

| Client | Skills | MCP | MCP format |
| --- | --- | --- | --- |
| Kiro | `.kiro/skills` | `.kiro/settings/mcp.json` | JSON |
| Claude Code | `.claude/skills` | `.claude.json` | JSON |
| OpenCode | `.config/opencode/skills` | `.config/opencode/opencode.json` | JSON/JSONC |
| Antigravity IDE | `.gemini/config/skills` | `.gemini/config/mcp_config.json` | JSON |
| Codex | `.agents/skills` | `.codex/config.toml` | TOML |

The capability matrix, OS compatibility, and installation complexity come from `config/clients.yml`. At startup, SSS detects the current runtime OS and architecture and displays them as context. Skill and MCP catalogue metadata lives in `catalogue/skills.yml` and `catalogue/mcp.yml`. These labels help users choose a target; they are not a dependency resolver or a runtime guarantee.

## Install and usage

Requirements: Python 3.9+, Git, and Node.js/npm when using the `codebase-memory-mcp` fallback through `npx`.

The legacy bootstrap remains global:

```bash
npm run setup
```

This script creates `.venv`, installs `requirements.txt`, and runs the Python CLI with `--scope global`. The global behavior of `npm run setup` is unchanged.

For project-level installation:

```bash
.venv/bin/python -m cli --scope project --project-root /absolute/path/to/project --check
.venv/bin/python -m cli --scope project --project-root /absolute/path/to/project
```

Without `--project-root`, project scope uses the current working directory. SSS does not detect or switch to the Git root automatically. For a custom global home, use the legacy behavior:

```bash
.venv/bin/python -m cli --scope global --target-home /absolute/home/path --check
```

The public npm package provides the `npx` entrypoint and bundles its Python dependencies. No project `.venv`, cached venv, or `pip install` step is required.

From any project root:

```bash
npx sss-ai-cli --scope project --project-root /absolute/path/to/project --check
npx sss-ai-cli --scope project --project-root /absolute/path/to/project
```

`npx sss-ai-cli setup` remains a compatibility alias for launching the interactive menu. The wrapper keeps the caller's working directory as the project context and requires only a system Python 3 executable. `SSS_PYTHON` can override the Python executable when needed.

## Setup flow

1. Select one or more components: `Skills`, `MCP servers`, and optionally `AI guardrails` in project scope.
2. If Skills or MCP servers are selected, choose one or more of the five clients.
3. Select the required catalogue items. `code-review` and `security-review` remain mandatory.
4. Review the scope, target root, native paths, compatibility labels, complexity, and conflict warnings.
5. Run `--check` for a preview without writing, or confirm the apply operation.

## AI guardrails

The optional `AI guardrails` component creates `AGENTS.md` in the selected project root. Guardrails are available only with `--scope project`; SSS does not create a global `AGENTS.md` automatically because its instructions could affect every project.

The component follows the same file rules as other managed outputs:

- An existing `AGENTS.md` is skipped by default and shown as a conflict.
- `--update` or `--force` replaces the file only after preview and confirmation, with a timestamped backup.
- The template contains `MUST` rules, sensitive-file reminders, examples of destructive commands that require confirmation, and a change protocol.
- The template intentionally does not add a separate MCP policy section.

`AGENTS.md` is an instruction contract for compatible AI clients, not runtime security enforcement. It does not replace a sandbox, permissions, approval hooks, network policy, or human review.

The canonical template is `templates/AGENTS.md`.

## Conflict behavior

- A Skill directory with the same name is skipped entirely by default, so existing files are not touched.
- An MCP server with the same name in the native section is skipped, while new servers can still be added.
- `--update` or `--force` replaces only selected Skill/MCP items and creates a timestamped backup for existing files.
- Other entries and files remain unchanged.
- A malformed config stops the merge before the target file is replaced.

File-level MVP hardening includes relative-path validation, confinement to the target root, symlink-escape protection, preview, confirmation, conflict handling, backups, permissions, temporary-file `fsync`, and atomic `os.replace`.

## Commands

```bash
# Global setup with the menu
npm run setup

# Project-level preview
.venv/bin/python -m cli --scope project --project-root /absolute/path/to/project --check

# Allow replacement after preview and confirmation
.venv/bin/python -m cli --scope project --project-root /absolute/path/to/project --update

# --force is an alias for --update
.venv/bin/python -m cli --scope global --force --verbose

# Validate catalogues and public Skill packages
.venv/bin/python -m cli --validate

# Show all options
.venv/bin/python -m cli --help
```

## Security boundary

SSS does not redact email addresses or tokens before requests reach an AI client, install a local security bridge, analyze repository contents for automatic recommendations, or provide runtime interception, a policy proxy, or a daemon. Client ignore files and permissions can reduce accidental exposure, but they do not guarantee that an AI client cannot access sensitive data through a shell, MCP server, another client, or a direct network request.

## Repository structure

```text
catalogue/          Skills and MCP catalogues
config/             Native paths, capability matrix, and client metadata
skills/             Public Skill packages
cli/                Python engine, selector, merge, and deployment plan
bin/sss.js          npm/npx entrypoint
package.json        npm wrapper and package allowlist
SECURITY.md         Hardening boundaries and enforcement limits
templates/          Generated project instruction templates
```
