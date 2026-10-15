# Security boundary

SSS is a thin launcher/installer. It manages local configuration files, not the contents of requests sent to an AI client and not a runtime security bridge.

## MVP hardening

- Destinations must be relative paths below the selected target root.
- Absolute paths, `..`, parent symlink escapes, and non-file destinations are rejected before writing.
- Scope and target root are shown in the preview.
- Existing Skill packages and MCP entries are not overwritten by default.
- `--update` and `--force` are explicit permissions for selected replacements; they do not bypass preview or confirmation.
- Existing files that are replaced receive a timestamped backup.
- Writes use a temporary file, `fsync`, restricted permissions, and atomic `os.replace`.
- A malformed config stops the merge before the target file is replaced.
- Preview output does not print config contents or MCP secrets.

Backups and atomic replacement reduce the risk of a partial installation, but they do not replace organizational backups or policy.

## Enforcement boundary

SSS **does not** provide any of the following:

- A local security bridge or runtime policy proxy.
- Email or token redaction before a request reaches an AI client.
- Automatic recommendations based on repository contents.
- Role/project metadata persistence or per-target Skill mapping.
- Installation or updates for AI client applications or MCP binaries.
- Enforcement for shell, MCP, file access, network access, model routing, or LLM destinations.
- Runtime enforcement from generated `AGENTS.md`; it is only a project instruction contract for compatible AI clients.

Client ignore files such as `.gitignore`, `.geminiignore`, `.cursorignore`, `.aiderignore`, and `.kiroignore` can reduce accidental exposure. Config permissions can also limit ordinary writes. These controls do not guarantee that sensitive data cannot be accessed through a shell, MCP server, another client, or a direct network request.

Zero-PII enforcement requires an approved AI gateway and network policy that blocks disallowed LLM destinations. This repository does not configure those controls.
