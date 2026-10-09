# Security policy

Customer data, including NIK, payment-card data, and database exports, must not be sent to an LLM.

## Local safeguards

- `.gitignore` excludes common credentials, private keys, and database exports from Git. Codex file discovery and Antigravity strict-mode workspace access honor these patterns.
- `.geminiignore`, `.cursorignore`, `.aiderignore`, and `.kiroignore` provide client-specific exclusions.
- `.claude/settings.json` denies Claude Code's `Read` tool access to those sensitive paths. `opencode.json` denies OpenCode's `read` tool access to them.
- The optional Python CLI security component installs shared Gitleaks rules and a global Git pre-commit hook. It reuses an existing global hooks directory and chains its executable `pre-commit` script when present.
- Gitleaks must be installed separately. The hook scans staged changes and blocks commits with findings. `git commit --no-verify` bypasses this local hook.
- These controls reduce accidental exposure. They do not enforce company-wide traffic policy. Client read controls may not block shell commands, MCP servers, other AI clients, or direct network requests.
- Gitleaks detects secrets. It is not a general PII detector.

## Enforcement boundary

Company-wide zero-PII enforcement requires an approved AI gateway or managed endpoint and network policy that blocks unapproved LLM destinations. That control is not configured by this repository. Do not describe local ignore files or the Gitleaks hook as a guarantee that PII cannot reach an LLM.

## Hook setup

Install Gitleaks first, then select **Gitleaks and global Git hook** in `.venv/bin/python -m cli`. An existing global `core.hooksPath` is reused. Its current executable pre-commit script is saved as `pre-commit.company-original` and chained before the company scan.
