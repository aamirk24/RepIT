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

### Stage 3 — Workout experience and data integrity

- Added recoverable active workouts with database-backed timers and one active session per user.
- Added editable and removable sets, rest times, workout names and notes, and persistent exercise ordering.
- Moved workout mutations into transaction-safe service functions with ownership and active-state enforcement.
- Added database uniqueness, range, lifecycle, and ordering constraints.
- Snapshotted exercise identity fields into workout history so provider catalogue changes cannot rewrite past sessions.
- Made completed sessions immutable and prevented empty workouts from being completed.

### Stage 4 — Progress and analytics

- Added 30, 90, and 365-day summaries for workouts, sets, repetitions, weighted volume, and training time.
- Added previous-period comparisons, 12-week workout frequency, weekly volume, and consecutive-week streaks.
- Added per-exercise heaviest-load, estimated 1RM, repetition records, performance trends, and session history.
- Added metric and imperial preferences while retaining kilograms and centimetres as canonical storage units.
- Added accessible chart alternatives and semantic analytics tables.
- Kept analytics user-scoped and provider-independent through RepIT exercise IDs and historical snapshots.
- Added analytics indexes and regression coverage for calculations, isolation, conversion, and filtering.

### Stage 5 — Product UI, accessibility, and responsive design

- Added the Quiet Sage design system and rebuilt navigation, landing, dashboard, exercise browser, routines, workout logger, progress, history, and account screens.
- Replaced the legacy all-record exercise page with paginated search and filtering while keeping media lazy-loaded.
- Added responsive behavior, keyboard navigation, reduced-motion support, semantic markup, and accessible chart alternatives.
- Added reliable two-frame exercise demonstrations throughout catalogue, routine, and workout experiences.

### Stage 6 — Deployment and operations

- Prepared Render and Neon deployment configuration, Gunicorn, bounded reverse-proxy trust, structured request logging, optional Sentry monitoring, and liveness/readiness checks.
- Added concurrency-safe migrations and pinned catalogue preparation to the production startup path.
- Added GitHub Actions tests, migration verification, compilation, and dependency vulnerability auditing before automatic deployment.
- Added a privacy policy, terms, fitness disclaimer, explicit retention rules, and deployment, incident, backup, recovery, and security runbooks.

## Planned

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
