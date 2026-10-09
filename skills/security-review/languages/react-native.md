# React Native Security Patterns

## Sensitive data

- Never treat values bundled in the mobile application as server-side secrets. App bundles can be inspected.
- Check whether tokens or sensitive personal data are persisted in unencrypted general-purpose storage, Redux persistence, logs, analytics, or crash reports.
- Confirm logout and account switching clear sensitive state and invalidate credentials where required.
- Prefer platform-backed secure storage for secrets when persistent storage is necessary. Check the actual library and platform configuration before reporting a finding.

## Deep links and authentication

- Treat deep links, universal links, notification payloads, and OAuth redirects as untrusted input.
- Do not place credentials or sensitive values in URLs. Validate the requested route and authorize access to the target resource after navigation.
- Check OAuth flows use the provider-supported protections, including PKCE where applicable, and validate redirect handling.

## WebViews and native bridges

- Review allowed URL schemes and hosts, JavaScript injection, navigation policy, and any bridge exposed to web content.
- Confirm untrusted pages cannot invoke privileged native methods or read sensitive data.
- Check values passed between JavaScript and native code are validated at the boundary.

## Network and platform configuration

- Check production endpoints use TLS and that cleartext exceptions are narrow and justified.
- Check iOS and Android configurations independently. Do not assume platform security behavior is identical.
- Treat certificate pinning as an operational choice with rotation and expiry risks. Its absence alone is not a vulnerability.

## References

- [React Native security](https://reactnative.dev/docs/security)
- [React Native networking](https://reactnative.dev/docs/network)
