# Research: installable code-review and security plugins

**Checked:** 2026-10-07
**Question:** Which generic, installable AI coding-agent packages provide useful code-review and security-review workflows across Claude, Codex, Kiro, Antigravity (`agy`), OpenCode, OpenClaw, and Hermes?

## Recommendation

- There is no well-supported, single native plugin package I found that installs the same complete review experience on all seven clients. Plugin systems expose different features and install paths.
- For a quick external pilot, compare two packages:
  - [obra/superpowers](https://github.com/obra/superpowers) for broad code-review workflow. It has the strongest usage signal for a general code-review skill, and native installation routes for most of the requested tools. It is not a dedicated security-review package. Kiro is not listed as supported in its upstream README. OpenClaw support is documented in an upstream issue as a skills-directory adapter, not as a native plugin install route.
  - [wshobson/agents](https://github.com/wshobson/agents) for a more explicit plugin bundle pairing code-review capabilities with security-scanning. Its documented adapters cover Claude, Codex, OpenCode, and Antigravity. It does not document Kiro, OpenClaw, or Hermes support.
- For SSS's actual seven-client target, the best fit is a **company-owned plugin-style package** with an Agent Skills-compatible core and thin client-specific adapters. Keep review procedures in shared `SKILL.md` packages. Add native agents, commands, hooks, and manifests only where the client supports them. The Agent Plugins standard is a useful shared package format for Codex, Kiro, OpenClaw, and Hermes, but its current client list does not include Claude Code, Antigravity, or OpenCode.
- If Claude Code were the only target, Anthropic's official [Code Review](https://claude.com/marketplace/plugins/code-review) plus [Security Guidance](https://claude.com/plugins/security-guidance) is the strongest first-party plugin pair in this comparison. It is not a cross-agent choice.

## Keep the package types distinct

| Package type | What is portable | What does not automatically carry over |
|---|---|---|
| `SKILL.md` | Review procedures, checklists, references, and report templates in the open Agent Skills format. | Native slash commands, subagent definitions, hooks, permission controls, or marketplace install behavior. These are client-specific. |
| Agent Plugin package | A root `plugin.json`, shared skills, and optional MCP configuration under the Agent Plugins specification. | Client-specific plugin extensions and behaviors. The core standard does not standardize subagents, commands, or hooks. Each client chooses supported components. |
| Native client plugin | The complete experience for its target harness, including that client's agents, tools, hooks, and commands. | Cross-client use unless a vendor or maintainer ships adapters or equivalent packages. |

The [Agent Plugins specification](https://agent-plugins.org/specification) defines the portable core as a manifest, skills, and optional MCP servers. It leaves client-specific behavior in extensions. Its [current compatible-client list](https://agent-plugins.org/compatible-clients) includes Codex, Kiro, Hermes, and OpenClaw, but not Claude Code, Antigravity CLI, or OpenCode. Those tools can still load Agent Skills, but the portable plugin manifest alone is not a universal native installer.

## Compatibility against the requested tools

Legend: **Native** means the upstream documents an install route or adapter. **Skills** means the shared `SKILL.md` content can be installed or loaded, but plugin features may be absent. **No documented route** means I found no upstream-supported route for that client.

| Package | Claude | Codex | Kiro | `agy` | OpenCode | OpenClaw | Hermes |
|---|---|---|---|---|---|---|---|
| Agent Skills core | Skills | Skills | Skills | Skills | Skills | Skills | Skills |
| Agent Plugins 1.0 core | No listed client support | Native | Native | No listed client support | No listed client support | Native | Native |
| obra/superpowers | Native plugin | Native plugin | No documented route | Native plugin | Native plugin | Skills-directory adapter documented in issue, not upstream README | Native plugin |
| wshobson/agents | Native marketplace | Native marketplace plus generated route | No documented route | Generated adapter | Generated adapter | No documented route | No documented route |
| Anthropic Code Review + Security Guidance | Native plugins | No documented route | No documented route | No documented route | No documented route | No documented route | No documented route |

“Skills” support is not equivalent to installing an entire plugin. Kiro's official docs support importing Agent Skills from GitHub. OpenClaw loads skills from configured directories, and Hermes has its own plugin/skills mechanisms. Review each client's current loader and permissions before choosing the distribution adapter.

## Shortlist

| Candidate | Adoption signal observed | Plugin contents and install shape | Fit and gaps |
|---|---|---|---|
| [obra/superpowers](https://github.com/obra/superpowers) | About **296K GitHub stars** for the repository. Its `requesting-code-review` skill showed about **245K installs** in skills.sh. | Includes `requesting-code-review` and a separate reviewer prompt template. The workflow sends a Git range and requirements to a fresh reviewer, then acts on severity-ranked feedback. Claude and Codex have plugin-marketplace routes. Antigravity uses `agy plugin install`. OpenCode has a dedicated install document. Hermes uses `hermes plugins install obra/superpowers --enable`. | Best adoption-backed general review workflow. It assumes a second reviewer/subagent and is not a security-review specialist. Its README does not document Kiro. OpenClaw integration instructions appear in a GitHub issue and use OpenClaw workspace skills plus configuration, rather than a plugin package command. |
| [wshobson/agents](https://github.com/wshobson/agents) | About **40K GitHub stars** for the repository. | `developer-essentials` lists code review among its development skills. `security-scanning` is a separate plugin for security checks. Claude plugins have manifests. Codex has marketplace manifests and generated artifacts. OpenCode and Antigravity use generated adapters. The documented build/install path requires cloning, `uv`, Python 3.12+, and running the harness generator/installer for OpenCode or Antigravity. | Closest ready-made plugin bundle for the two requested concerns across multiple clients. Its own compatibility table does not cover Kiro, OpenClaw, or Hermes. Source is Claude-format Markdown with per-harness generated adaptations, so review adapter output and behavior rather than assuming identical feature parity. |
| [Anthropic Code Review](https://claude.com/marketplace/plugins/code-review) + [Security Guidance](https://claude.com/plugins/security-guidance) | Marketplace showed about **438K Code Review installs** and **242K Security Guidance installs**. | Code Review uses five independent review angles, confidence scoring, and a `/code-review` command for GitHub PRs. Security Guidance adds pattern warnings on edits, an LLM diff review, and an agentic commit review. Its documented requirements include Claude Code CLI, Python 3.8+, and a working model API path. | Strongest first-party, ready-to-run combination and unusually strong install signal. Claude-only. Security Guidance runs as a hook and makes model calls, so it is not equivalent to a portable checklist skill or a deterministic CI scanner. |
| [OWASP Secure Agent Playbook](https://github.com/OWASP/secure-agent-playbook) | About **186 GitHub stars** for the repository; the `code-review-security` skill showed about **322 skills.sh installs**. | Claude Code marketplace plugins include a `code-review-security` skill and a detailed OWASP-mapped play. The play covers trust boundary, data sensitivity, OWASP Top 10/ASVS classes, changed-code context, attack scenario, evidence, remediation, and confidence. | Strong generic security-review content, weak cross-agent plugin packaging and lower observed adoption. Best as a reviewed source to adapt into the SSS security skill, not as the shared seven-client plugin by itself. |

### Install commands and notable components

- **Superpowers:** `agy plugin install https://github.com/obra/superpowers`; `hermes plugins install obra/superpowers --enable`; OpenCode follows `.opencode/INSTALL.md`; Codex uses its plugin marketplace; Claude Code uses its plugin marketplace. Its `requesting-code-review` skill expects a fresh subagent and passes a bounded diff plus requirements. OpenClaw's documented workaround loads skills from an extra directory and adds a bootstrap plugin hook/config entry.
- **wshobson/agents:** Claude uses `/plugin marketplace add wshobson/agents`. Codex uses `codex plugin marketplace add wshobson/agents`. OpenCode and Antigravity require a clone and generated install route such as `make install-opencode` or `make install-antigravity`. It separates development review and security scanning into different plugins, rather than one monolithic review plugin.
- **Anthropic:** Claude Code installs with `/plugin install code-review@claude-plugins-official` and `/plugin install security-guidance@claude-plugins-official`. The Code Review plugin analyzes pull requests and posts findings. Security Guidance runs automatically around edits/turn completion/commits according to configuration. Its README calls the review best-effort and not a replacement for human review, SAST/DAST, dependency scanning, or penetration testing.
- **OWASP:** The play is distributed inside Claude Code plugins. Its portable value is the explicit review procedure, not a cross-client command or reviewer agent. The standalone `SKILL.md` points to a more detailed play file, so installing only that skill would omit the full review procedure.

## What SSS should adopt

1. **Code review skill:** Define a bounded, read-only diff review. Read repository instructions and enough surrounding code to prove findings. Report concrete, introduced, actionable issues only. Order by severity, include file and line evidence, and say when there are no findings. Keep security in scope without turning every review into a full audit.
2. **Security review skill:** Scope the threat boundary, entry points, sensitive data, actors, and changed security controls. Use OWASP ASVS/Top 10 as reference maps, not as proof that every listed category applies. Require an attack scenario and code evidence for each finding. Label unresolved candidates as unconfirmed.
3. **Package layer:** Keep `code-review/SKILL.md`, `security-review/SKILL.md`, their references, and report templates as the shared core. Add a root Agent Plugins manifest for compatible clients. Generate or maintain client-native manifests and adapters for Claude Code, Antigravity, and OpenCode. For OpenClaw, Hermes, and Kiro, confirm the native Agent Plugins/skill loading behavior and use the lowest-common-denominator skill package where native plugin features are unavailable.
4. **Governance:** Pin reviewed package revisions. Inspect every script and referenced document before distribution. Use SAST/SCA, CI requirements, branch protection, and permissions for enforcement. Instructions in a plugin are not a security boundary.

## Popularity is not an effectiveness benchmark

- GitHub stars are for the whole repository, not a particular plugin, and can reflect awareness rather than repeated use.
- skills.sh install counts measure its own CLI telemetry, not unique developers, skill invocation, or finding quality. Manual and Ansible distribution are not represented.
- Anthropic Marketplace install counts are product-specific and do not establish successful findings or cross-agent adoption.
- None of these counts demonstrates vulnerability recall, false-positive rate, reviewer agreement, or reduced production incidents. They are discovery/adoption proxies only.
- The recommendation for a company-owned common core follows from the documented gaps in plugin format compatibility, not a claim that a custom package is already proven more effective.

## Sources

- [Agent Plugins specification](https://agent-plugins.org/specification) and [compatible clients](https://agent-plugins.org/compatible-clients)
- [Agent Skills specification](https://agentskills.io/specification)
- [Kiro Agent Skills docs](https://kiro.dev/docs/skills/) and [Kiro Agent Plugin support announcement](https://kiro.dev/changelog/ide/1-0-288/)
- [OpenClaw Skills docs](https://docs.openclaw.ai/skills) and [Superpowers OpenClaw integration details](https://github.com/obra/superpowers/issues/1641)
- [obra/superpowers README](https://github.com/obra/superpowers), [review skill](https://github.com/obra/superpowers/blob/main/skills/requesting-code-review/SKILL.md), and [harness porting guide](https://github.com/obra/superpowers/blob/main/docs/porting-to-a-new-harness.md)
- [wshobson/agents README and compatibility matrix](https://github.com/wshobson/agents), [security-scanning manifest](https://github.com/wshobson/agents/blob/main/plugins/security-scanning/.claude-plugin/plugin.json), [developer-essentials manifest](https://github.com/wshobson/agents/blob/main/plugins/developer-essentials/.claude-plugin/plugin.json), and [harness details](https://github.com/wshobson/agents/blob/main/docs/harnesses.md)
- [Anthropic Code Review marketplace listing](https://claude.com/marketplace/plugins/code-review), [Security Guidance marketplace listing](https://claude.com/plugins/security-guidance), and [Security Guidance implementation README](https://github.com/anthropics/claude-code/blob/main/plugins/security-guidance/README.md)
- [OWASP Secure Agent Playbook](https://github.com/OWASP/secure-agent-playbook), [`code-review-security` skill](https://github.com/OWASP/secure-agent-playbook/blob/main/plugins/code-security-skills/skills/code-review-security/SKILL.md), [detailed play](https://github.com/OWASP/secure-agent-playbook/blob/main/plugins/code-security-skills/plays/code-review-security.md), and [skills.sh listing](https://www.skills.sh/owasp/secure-agent-playbook)
- [skills.sh telemetry and ranking documentation](https://www.skills.sh/docs)
