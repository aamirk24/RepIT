# Security and data handling

## Reporting a vulnerability

Do not open a public issue containing exploit details, secrets, or user data. Contact the repository owner privately through the contact method on their GitHub profile and include the affected route, reproducible steps, impact, and any suggested mitigation. The owner will acknowledge and triage reports as availability permits; this personal project does not promise a formal response SLA.

## Production controls

RepIT validates production secrets and PostgreSQL configuration at startup, terminates HTTPS at the hosting proxy, trusts a bounded proxy hop count, uses secure and HTTP-only cookies, applies CSRF protection, hashes passwords, throttles login attempts, and emits restrictive browser headers. Dynamic responses are not cached. Application logs contain route templates and request IDs, not request bodies, query strings, cookies, passwords, or IP addresses.

Dependency vulnerabilities are checked in CI with `pip-audit`. Keep GitHub dependency alerts enabled and review automated updates before merging. An audit result is a signal for review, not permission to apply an incompatible upgrade without tests.

## Data retention

- Profile, routines, workout history, sets, and measurements are retained while the account exists.
- Successful or failed login-throttle records older than 30 days are pruned during authentication activity.
- Immediate account deletion removes user-owned application data through relational cascades.
- Hosting logs, monitoring events, and database recovery history follow the configured provider retention periods and may persist briefly after account deletion.
- Free Exercise DB catalogue data is public-domain reference data and is not user data.

Before accepting meaningful public usage, add self-service data export, a documented deletion queue for backup expiry, verified email/recovery, and a named security contact.
