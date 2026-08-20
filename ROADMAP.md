# RepIT production roadmap

RepIT is being rebuilt in reviewable stages. Exercise metadata comes from a pinned, public-domain Free Exercise DB snapshot through a provider adapter. Future stages must preserve that source boundary rather than coupling product logic to the vendored JSON schema.

## Completed

### Stage 0 — Restored baseline

- Recovered the Flask application and relational workout flows.
- Removed legacy secrets and inactive ExerciseDB assumptions.
- Established migrations, local setup, and baseline tests.

### Stage 1 — Production and catalogue foundation

- Added explicit development, testing, and production configuration.
- Added PostgreSQL support and production fail-closed validation.
- Normalized provider identity, catalogue metadata, attribution, and licensing fields.
- Added a provider synchronization contract and normalized catalogue model.
- Added exercise filtering, deployment health checks, and catalogue tests.

### Open catalogue integration

- Replaced the handcrafted scaffold with 873 Free Exercise DB records.
- Pinned the upstream commit, vendored its JSON and licence, and verified the snapshot checksum.
- Preserved existing routine/history relationships while retiring unused scaffold rows.
- Kept exercise media separate and commit-pinned so richer licensed media can be introduced independently.

### Stage 2 — Authentication and account security

- Stronger account-input and password validation.
- Explicit remember-me choice and bounded session lifetimes.
- Safe post-login redirects and generic authentication errors.
- Persistent database-backed login throttling.
- Password changes with global session invalidation.
- Password-confirmed account deletion.
- Browser security headers and expanded security regression tests.

## Planned

### Stage 3 — Workout experience and data integrity

- Redesign active-workout state, set editing, timers, notes, ordering, and recovery from interrupted sessions.
- Add transaction-safe service functions and database constraints for workout invariants.
- Treat external exercises as normalized provider records; preserve historical workout facts when provider content changes or disappears.

### Stage 4 — Progress and analytics

- Personal records, volume, frequency, exercise history, trends, and dashboard summaries.
- Unit preferences and accessible data visualizations.
- Provider-independent analytics keyed to RepIT exercise identities.

### Stage 5 — Product UI, accessibility, and responsive design

- Cohesive design system and rebuilt navigation, dashboard, exercise browser, workout logger, and account screens.
- Replace the legacy all-record exercise page with API-driven search, filtering, and pagination; keep media lazy-loaded and avoid generating multi-megabyte catalogue HTML.
- Mobile-first behavior, keyboard navigation, reduced-motion support, semantic markup, and accessibility checks.
- Improve the two-image exercise demonstrations and allow optional licensed looping media with fallbacks and attribution.

### Stage 6 — Deployment and operations

- Managed PostgreSQL, production web server, reverse-proxy configuration, structured logging, error monitoring, backups, CI, and deployment checks.
- Privacy policy, terms, fitness disclaimer, retention rules, and production runbooks.

## Deferred integrations and explicit prerequisites

These items are intentionally recorded rather than silently omitted:

- **Free Exercise DB updates:** updates are deliberate repository changes, not runtime network calls. Review the upstream licence/schema, pin a new commit, replace the snapshot, update the checksum, run the sync migration tests, and review additions/removals before publication.
- **Optional animation provider:** only integrate media with durable, no-cost usage rights. Keep animation independent from exercise identity and history; never expose provider credentials or make saved routines depend on a revocable media licence.
- **Email verification:** requires a transactional email provider, verified sending domain, expiring signed tokens, resend throttling, and delivery/error handling.
- **Password recovery:** requires the same email foundation, single-use expiring reset tokens, generic responses that prevent account enumeration, and session invalidation after reset.
- **Account email changes:** require current-password confirmation plus verification of the new address.
- **Multi-factor authentication and passkeys:** evaluate after the core deployment and recovery flows exist.
- **Advanced bot protection:** add only if real traffic justifies CAPTCHA or a managed edge challenge.
- **Proxy-aware client identity:** configure trusted proxy handling at deployment before relying on forwarded IP headers for throttling.
- **Centralized rate-limit storage:** the current database-backed throttle works across web workers. Re-evaluate Redis only if traffic or broader endpoint throttling makes it worthwhile.
- **Self-hosted exercise media:** evaluate before deployment to avoid depending on GitHub raw-file availability. The current public-domain images may be copied locally or to owned object storage after assessing repository size and image optimization.
- **Data export and delayed account deletion:** add before treating RepIT as a real multi-user service; the portfolio build currently supports immediate deletion.
- **Administrative tooling:** moderation, account support, catalogue synchronization controls, audit events, and operational dashboards require defined admin roles.
