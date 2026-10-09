# PHP and Laravel Security Patterns

## Authorization and tenant boundaries

- Check route middleware, gates, and policies against each resource action. Authentication alone does not establish permission to access a model.
- Trace tenant or owner scoping through route binding, queries, jobs, and service methods. A request-controlled identifier must not bypass the intended scope.
- Verify authorization still applies to queued or deferred work and background entry points.

## Validation and mass assignment

- Check request values are validated before they reach business logic or persistence. Inspect Form Requests, controller validation, and custom validation rules.
- Trace request fields into `create`, `fill`, `update`, or `updateOrCreate`. `$fillable` and `$guarded` are context, not proof that a particular request is safe.
- Ensure fields such as owner IDs, roles, account status, and prices cannot be changed by unauthorized callers.

## Database and output handling

- Eloquent and query-builder bindings parameterize values. Do not report ordinary bound queries as SQL injection.
- Investigate raw expressions, interpolated SQL, and user-controlled identifiers. Allowlist identifiers that cannot be bound.
- Blade escapes `{{ }}` output. Review `{!! !!}` and other raw HTML paths when content is attacker-controlled.

## Files, sessions, and jobs

- Check uploads for authorization, content constraints, safe storage location, and safe download behavior.
- Check redirects and URL construction for untrusted destinations.
- Review jobs and retries for idempotency, transaction boundaries, authorization assumptions, and sensitive payloads.
- Check logs and exception reporting do not include credentials, tokens, or unnecessary personal data.

## References

- [Laravel authorization](https://laravel.com/docs/12.x/authorization)
- [Laravel validation](https://laravel.com/docs/12.x/validation)
- [Laravel Eloquent mass assignment](https://laravel.com/docs/12.x/eloquent#mass-assignment)
