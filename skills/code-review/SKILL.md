---
name: code-review
description: Review code changes in Go, TypeScript, React, React Native, and PHP Laravel projects. Use for pull requests, branches, commits, or diffs. Report concrete, introduced defects with evidence and severity.
license: Apache-2.0
---

# Code Review

Adapted by SSS from the review checklist in [getsentry/skills/code-review](https://github.com/getsentry/skills/tree/main/skills/code-review). Modified to target Go, TypeScript, React, React Native, and PHP Laravel projects.

Review a user-specified change for correctness, security, performance, reliability, compatibility, and maintainability. Prioritize defects over style preferences.

## Review contract

- Review only the requested diff or commit range. Read surrounding code and relevant callers, tests, types, framework configuration, and project instructions to confirm a finding.
- If the user did not identify the change range, use the current uncommitted diff when that is clearly the request. Otherwise ask for the base ref before reviewing.
- Report only concrete, introduced, actionable defects. Do not report pre-existing problems, speculative risks, or stylistic preferences as findings.
- Do not modify files during a review.
- Do not claim tests were run unless you ran them. Mention relevant validation gaps only when they affect confidence.
- Do not send source code, secrets, customer records, or production data to external services to perform the review.

## Identify the stack

Use changed file extensions, imports, manifests, and nearby source files. A repository may use more than one target stack. Apply only the relevant checks below, plus the repository's own documented conventions.

| Stack | Indicators |
|---|---|
| Go | `.go`, `go.mod`, `go.work` |
| TypeScript | `.ts`, `.tsx`, `tsconfig.json` |
| React | JSX/TSX components, React imports, React DOM dependencies |
| React Native | `react-native`, Expo, native platform directories, navigation libraries |
| PHP Laravel | `composer.json` with Laravel, `artisan`, routes, controllers, Form Requests, Eloquent models |

TypeScript, React, and React Native overlap. Review both language-level and framework-specific behavior where applicable.

## General checks

- Trace changed inputs to their validation, authorization, and eventual use. Check boundary cases, null or missing values, error paths, and concurrency.
- Check whether callers and consumers remain compatible. Pay attention to API contracts, persisted data, migrations, serialization, and platform-specific behavior.
- Check resource behavior: unbounded work, repeated queries or requests, leaks, retries, timeouts, cancellation, and cleanup.
- Check test changes against the behavior and regression risk. Do not require tests for trivial changes without meaningful behavior.
- Treat framework protections as real. Do not flag a pattern as unsafe without tracing the input and checking the protections in use.

## Go

- Check every returned error on changed paths. Confirm errors retain useful context and callers do not silently discard failures.
- Follow `context.Context` through request-scoped I/O and database calls. Check cancellation, deadlines, and cleanup of goroutines, timers, response bodies, and `sql.Rows`.
- Check shared mutable state for races and lock/channel correctness. Look for goroutines that can outlive their request or block forever.
- Check HTTP handlers for method, status, body, and header behavior, plus authentication and authorization at the correct resource boundary.
- Check SQL uses parameters for values. Dynamic identifiers require a strict allowlist. Review transaction boundaries and ensure operations intended to be atomic use the transaction handle throughout.
- Check resource limits for request bodies, uploads, decompression, and expensive parsing when input is untrusted.

## TypeScript

- Check external data at runtime boundaries. Static types do not validate JSON, network responses, database rows, URL parameters, or user input.
- Check async failures, rejected promises, cancellation, stale responses, and cleanup of subscriptions or timers.
- Check public type and API changes for compatibility, including optional/null values, discriminated unions, and serialized shapes.
- Check unsafe casts, `any`, non-null assertions, and ignored compiler or lint errors where they conceal an actual behavior defect.
- Check that validation and authorization happen at the trusted server boundary. Client-side checks alone do not protect an API.

## React

- Check render purity, state ownership, keys, controlled inputs, and whether derived state or synchronization can become stale.
- For Effects, verify they synchronize with an external system, declare reactive dependencies correctly, and clean up subscriptions, timers, and requests when needed. Do not flag an Effect solely because it exists.
- Check event handlers and async UI work for duplicate submission, stale state, race conditions, and updates after the relevant view is no longer active.
- Check unsafe HTML rendering and URL sinks. JSX escaping protects ordinary text interpolation, but does not make `dangerouslySetInnerHTML` or unsafe URL schemes safe.
- Check keyboard and screen-reader behavior when a changed interaction could become inaccessible.

## React Native

- Check app lifecycle and navigation transitions for stale requests, subscriptions, listeners, timers, and sensitive state retained across logout or account changes.
- Check deep links and notification payloads as untrusted input. Validate destinations and resource authorization, and never put credentials or sensitive data in URLs.
- Check tokens and sensitive local data are not stored in unencrypted general-purpose storage or emitted to logs, analytics, or crash reports.
- Check WebView content, injected JavaScript, URL allowlists, native bridges, and external intents for trust-boundary mistakes.
- Check platform differences across iOS and Android for permissions, secure storage, networking, and native modules. Do not infer one platform's behavior from the other.
- Check UI states and controls remain usable with platform accessibility APIs when affected by the change.

## PHP Laravel

- Check each route/action for authentication and resource-level authorization. Verify policies, gates, middleware, and tenant scoping protect the specific object being accessed.
- Check request data is validated before use. Review Form Requests and conditional validation for authorization or validation gaps.
- Check mass assignment boundaries on Eloquent models. Do not treat `$fillable` or `$guarded` by itself as proof of safety; trace which request fields reach model writes.
- Check query-builder and Eloquent calls for parameterized values. Review `DB::raw`, raw expressions, dynamic table or column names, and string-built SQL carefully.
- Check Blade output uses escaped rendering for untrusted values. Review raw `{!! !!}` output, redirects, and URLs for their context.
- Check transactions cover all writes that must succeed or fail together. Check queued jobs for authorization assumptions, retry safety, idempotency, and sensitive payloads.
- Check uploads, storage paths, temporary files, and downloads for validation, authorization, path traversal, and public exposure.

## Findings

Order findings by severity. Each finding must include:

- Severity: Critical, High, Medium, or Low, based on demonstrated impact and exploitability.
- A precise file and line location in the changed code.
- The concrete failure and its impact.
- The input, state, or execution path that makes it happen.
- A narrow remediation.

Do not inflate severity. If no actionable issue is found, state that no findings were found. Keep general observations and validation gaps separate from findings.
