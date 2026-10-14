# Security policy

Customer data, including NIK, payment-card data, and database exports, must not be sent to an LLM.

## Local safeguards

- `.gitignore` excludes common credentials, private keys, and database exports from Git. Codex file discovery and Antigravity strict-mode workspace access honor these patterns.
- `.geminiignore`, `.cursorignore`, `.aiderignore`, and `.kiroignore` provide client-specific exclusions.
- `.claude/settings.json` denies Claude Code's `Read` tool access to those sensitive paths. `opencode.json` denies OpenCode's `read` tool access to them.
- These controls reduce accidental exposure. They do not enforce company-wide traffic policy. Client read controls may not block shell commands, MCP servers, other AI clients, or direct network requests.

## Enforcement boundary

Company-wide zero-PII enforcement requires an approved AI gateway or managed endpoint and network policy that blocks unapproved LLM destinations. That control is not configured by this repository. Do not describe local ignore files or client read controls as a guarantee that PII cannot reach an LLM.
