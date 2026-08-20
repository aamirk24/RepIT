# Backup and recovery runbook

## Policy

Neon's point-in-time recovery window is the primary protection against operator mistakes. The available window varies by plan, so confirm the current project setting before every risky migration. For a real multi-user launch, add scheduled logical exports to encrypted storage controlled by the project owner and define a tested retention period.

Backups contain personal training and profile data. Restrict access, encrypt copies, never commit exports, and delete expired copies according to the privacy policy.

## Before a risky migration

1. Confirm the latest restorable point in Neon.
2. Create a separate branch or logical export if the change could remove or rewrite data.
3. Restore into an isolated database and run the new migration there.
4. Run the application smoke test against the restored copy.
5. Record the recovery point and responsible release before production deployment.

## Recovery procedure

1. Stop writes by suspending the web service or enabling an equivalent maintenance boundary.
2. Preserve logs and identify the last known-good time and commit.
3. Restore Neon to a new branch/database rather than overwriting the only remaining copy.
4. point a temporary RepIT instance at the restored database and run `/health/ready` plus the smoke test.
5. Update production `DATABASE_URL` to the verified restored database and redeploy.
6. Confirm user counts, recent workouts, routines, measurements, and catalogue count before reopening writes.
7. Document the incident, affected interval, recovery point, and preventative action.

Never claim backups are working merely because a provider advertises them. A restore test is the evidence that recovery works.
