# Go Security Patterns

## Input and query handling

- Trace values from HTTP requests, message payloads, files, and environment configuration to their sinks.
- Use SQL placeholders for values. Treat dynamic table names, column names, and sort expressions as safe only when selected from a strict allowlist.
- Check file paths derived from user input for traversal and symlink behavior. Confirm paths remain inside the authorized storage root.
- Check command execution for user-controlled arguments. Prefer APIs that pass an argument vector over shell command construction.

## HTTP and SSRF

- For outbound requests, trace control of the URL, scheme, host, redirects, and DNS resolution. Do not flag configured service URLs as attacker-controlled without evidence.
- Check redirects and IP resolution when user input can select destinations. Deny access to loopback, link-local, and internal ranges where the product's threat model requires it.
- Bound request bodies, response bodies, timeouts, and decompression when remote or user-controlled data is processed.
- Check handlers preserve request cancellation through `r.Context()` and outbound or database calls.

## Concurrency and resources

- Check goroutines have a bounded lifetime and a cancellation or completion path.
- Check shared mutable state is synchronized and that lock ownership and channel closure are consistent.
- Close response bodies and database rows. Check `Rows.Err()` after iteration and propagate database errors.
- Check multi-step writes use a transaction when partial completion would violate an invariant.

## Authentication and authorization

- Verify authorization is performed for the resource being accessed, not only for the route or authenticated identity.
- Check middleware and handler behavior on missing, malformed, expired, and incorrectly scoped credentials.
- Avoid logging credentials, tokens, raw authorization headers, or sensitive request bodies.

## References

- [Go database access](https://go.dev/doc/database/)
- [Canceling database operations](https://go.dev/doc/database/cancel-operations)
- [Querying databases](https://go.dev/doc/database/querying)
