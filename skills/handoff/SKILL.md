---
name: handoff
description: Summarize the current conversation in chat so another agent can continue the work.
argument-hint: "What will the next session be used for?"
disable-model-invocation: true
---

Write a concise handoff summary directly in your response so the user can pass it to a fresh agent. Do not create or save a file unless the user explicitly asks for one.

Include the current goal, key decisions, completed work, open questions or next steps, and relevant file paths or URLs.

Include a "suggested skills" section naming any skills the next agent should call.

Do not duplicate content already captured in other artifacts (specs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

Redact any sensitive information, such as API keys, passwords, or personally identifiable information.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.
