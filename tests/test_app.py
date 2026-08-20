import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app import create_app, db
from app.analytics import progress_report
from app.models import Exercise, ExerciseSet, Height, SessionExercise, User, Weight, Workout, WorkoutSession
from app.seed import CATALOG_SOURCE, CATALOG_VERSION, FreeExerciseDbProvider, seed_exercises
from app.config import normalize_database_url


class RepITTestCase(unittest.TestCase):
    password = "correct-horse-battery"
    catalogue_size = 873

    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "WTF_CSRF_ENABLED": False,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "SECRET_KEY": "test-secret",
                "LOG_LEVEL": "WARNING",
            }
        )
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            seed_exercises()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def signup(self, email="user@example.com", username="user123"):
        return self.client.post(
            "/signup",
            data={
                "email": email,
                "first_name": "Test",
                "username": username,
                "password": self.password,
                "confirm": self.password,
            },
            follow_redirects=True,
        )

    def test_app_starts_without_network_or_api_key(self):
        response = self.client.get("/landing")
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            self.assertEqual(db.session.scalar(db.select(db.func.count(Exercise.id))), self.catalogue_size)

    def test_catalogue_seed_is_idempotent_and_versioned(self):
        with self.app.app_context():
            result = seed_exercises()
            self.assertEqual(result.created, 0)
            self.assertEqual(result.updated, 0)
            exercise = db.session.scalar(
                db.select(Exercise).where(Exercise.source_identifier == "Alternate_Incline_Dumbbell_Curl")
            )
            self.assertEqual(exercise.source, CATALOG_SOURCE)
            self.assertEqual(exercise.catalog_version, CATALOG_VERSION)
            self.assertTrue(exercise.description)
            self.assertTrue(exercise.is_active)
            self.assertEqual(exercise.license_name, "The Unlicense")
            self.assertEqual(len(exercise.image_urls), 2)
            self.assertIn(CATALOG_VERSION, exercise.image_url)

    def test_catalogue_sync_accepts_an_external_provider(self):
        record = dict(next(iter(FreeExerciseDbProvider().records())))
        record.update(
            source="test-provider",
            source_identifier="provider-001",
            slug="provider-squat",
            name="Provider Squat",
        )

        class TestProvider:
            source = "test-provider"

            def records(self):
                return [record]

        with self.app.app_context():
            result = seed_exercises(TestProvider())
            self.assertEqual(result.created, 1)
            synced = db.session.scalar(
                db.select(Exercise).where(
                    Exercise.source == "test-provider",
                    Exercise.source_identifier == "provider-001",
                )
            )
            self.assertEqual(synced.name, "Provider Squat")

    def test_catalogue_rejects_a_modified_snapshot(self):
        with tempfile.NamedTemporaryFile() as modified:
            modified.write(b"[]")
            modified.flush()
            with self.assertRaisesRegex(RuntimeError, "checksum"):
                list(FreeExerciseDbProvider(modified.name).records())

    def test_catalogue_replacement_preserves_referenced_scaffold_rows(self):
        self.signup()
        with self.app.app_context():
            user = db.session.scalar(db.select(User).where(User.email == "user@example.com"))
            existing = db.session.scalar(db.select(Exercise).where(Exercise.name == "Barbell Curl"))
            db.session.delete(existing)
            db.session.flush()

            def legacy(name, slug):
                return Exercise(
                    name=name,
                    slug=slug,
                    description="Legacy scaffold",
                    body_part="upper body",
                    target="biceps",
                    equipment="barbell",
                    difficulty="beginner",
                    category="strength",
                    secondary_muscles=[],
                    instructions=["Legacy instruction"],
                    image_urls=[],
                    source="RepIT",
                    source_identifier=slug,
                    catalog_version="legacy",
                    is_active=True,
                )

            exact_match = legacy("Barbell Curl", "legacy-barbell-curl")
            unmatched = legacy("Legacy Custom Movement", "legacy-custom-movement")
            unused = legacy("Unused Scaffold Movement", "unused-scaffold-movement")
            routine = Workout(name="Legacy Routine", creator=user, exercises=[exact_match, unmatched])
            db.session.add_all([routine, unused])
            db.session.commit()
            exact_id = exact_match.id
            unmatched_id = unmatched.id

            seed_exercises()

            rehomed = db.session.get(Exercise, exact_id)
            retained = db.session.get(Exercise, unmatched_id)
            self.assertEqual(rehomed.source, CATALOG_SOURCE)
            self.assertTrue(rehomed.is_active)
            self.assertEqual(retained.source, "RepIT")
            self.assertFalse(retained.is_active)
            self.assertIsNone(
                db.session.scalar(db.select(Exercise).where(Exercise.name == "Unused Scaffold Movement"))
            )
            self.assertEqual({item.id for item in routine.exercises}, {exact_id, unmatched_id})

    def test_exercise_api_supports_catalogue_filters(self):
        self.signup()
        response = self.client.get("/exercises?equipment=barbell&difficulty=intermediate&per_page=100")
        self.assertEqual(response.status_code, 200)
        exercises = response.get_json()["exercises"]
        self.assertGreater(len(exercises), 0)
        self.assertTrue(all(item["equipment"] == "barbell" for item in exercises))
        self.assertTrue(all(item["difficulty"] == "intermediate" for item in exercises))

    def test_exercise_library_renders_both_demonstration_frames(self):
        self.signup()
        response = self.client.get("/exercise")
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            exercise = db.session.scalar(db.select(Exercise).order_by(Exercise.id))
            for image_url in exercise.image_urls:
                self.assertIn(image_url.encode(), response.data)
        self.assertIn(b"exercise-demo-image", response.data)
        self.assertIn(b"data-frame-one=", response.data)
        self.assertIn(b"data-frame-two=", response.data)
        self.assertIn(b"/static/js/exercise_frames.js", response.data)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_readiness_request_ids_and_cache_policy(self):
        response = self.client.get("/health/ready", headers={"X-Request-ID": "render-check-123"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ready")
        self.assertEqual(response.headers["X-Request-ID"], "render-check-123")
        self.assertEqual(response.headers["Cache-Control"], "no-store")

        response = self.client.get("/landing", headers={"X-Request-ID": "invalid request id"})
        self.assertRegex(response.headers["X-Request-ID"], r"^[a-f0-9]{32}$")
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_public_legal_and_error_pages(self):
        for path, text in (
            ("/privacy", b"Privacy policy"),
            ("/terms", b"Terms of use"),
            ("/fitness-disclaimer", b"Fitness disclaimer"),
        ):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertIn(text, response.data)
        response = self.client.get("/this-page-does-not-exist")
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"Page not found", response.data)

    def test_prepare_deploy_command_runs_migrations_and_catalogue_sync(self):
        with patch("app.deploy.upgrade") as upgrade:
            result = self.app.test_cli_runner().invoke(args=["prepare-deploy"])
        self.assertEqual(result.exit_code, 0, result.output)
        upgrade.assert_called_once_with()
        self.assertIn("Deployment prepared", result.output)

    def test_production_configuration_fails_closed(self):
        with patch.dict(
            os.environ,
            {"SECRET_KEY": "short", "DATABASE_URL": "sqlite:///unsafe.db"},
            clear=False,
        ):
            with self.assertRaisesRegex(RuntimeError, "SECRET_KEY"):
                create_app(environment="production")

        with patch.dict(
            os.environ,
            {
                "SECRET_KEY": "a" * 32,
                "DATABASE_URL": "sqlite:///unsafe.db",
            },
            clear=False,
        ):
            with self.assertRaisesRegex(RuntimeError, "PostgreSQL"):
                create_app(environment="production")

    def test_postgres_urls_use_psycopg3(self):
        self.assertEqual(
            normalize_database_url("postgres://localhost/repit"),
            "postgresql+psycopg://localhost/repit",
        )

    def test_production_configuration_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "SECRET_KEY"):
                create_app(environment="production")

    def test_signup_login_logout_and_protected_route(self):
        self.assertEqual(self.client.get("/").status_code, 302)
        response = self.signup()
        self.assertIn(b"Welcome Back", response.data)

    def test_authenticated_pages_render(self):
        self.signup()
        for path in ("/", "/exercise", "/create_workout", "/tracking", "/progress", "/profile-info", "/measurements", "/account", "/faq"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
        self.client.post("/logout")
        response = self.client.post(
            "/login", data={"email": "user@example.com", "password": self.password}, follow_redirects=True
        )
        self.assertIn(b"Welcome Back", response.data)

    def test_short_and_predictable_passwords_are_rejected(self):
        for password in ("too-short", "password1234"):
            with self.subTest(password=password):
                response = self.client.post(
                    "/signup",
                    data={
                        "email": f"{password}@example.com",
                        "first_name": "Test",
                        "username": f"user{len(password)}",
                        "password": password,
                        "confirm": password,
                    },
                )
                self.assertEqual(response.status_code, 200)
                with self.app.app_context():
                    self.assertIsNone(db.session.scalar(db.select(User).where(User.email == f"{password}@example.com")))

    def test_login_is_throttled_after_repeated_failures(self):
        self.signup()
        self.client.post("/logout")
        for _ in range(5):
            response = self.client.post("/login", data={"email": "user@example.com", "password": "wrong-password"})
            self.assertEqual(response.status_code, 200)
        response = self.client.post("/login", data={"email": "user@example.com", "password": self.password})
        self.assertEqual(response.status_code, 429)
        self.assertIn(b"Too many login attempts", response.data)

    def test_login_rejects_external_next_redirects(self):
        self.signup()
        self.client.post("/logout")
        response = self.client.post(
            "/login?next=https://attacker.example/steal",
            data={"email": "user@example.com", "password": self.password},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")

    def test_remember_me_is_explicit(self):
        self.signup()
        self.client.post("/logout")
        response = self.client.post("/login", data={"email": "user@example.com", "password": self.password})
        self.assertNotIn("remember_token=", " ".join(response.headers.getlist("Set-Cookie")))
        self.client.post("/logout")
        response = self.client.post(
            "/login", data={"email": "user@example.com", "password": self.password, "remember": "y"}
        )
        self.assertIn("remember_token=", " ".join(response.headers.getlist("Set-Cookie")))

    def test_password_change_invalidates_existing_session(self):
        self.signup()
        response = self.client.post(
            "/change-password",
            data={
                "current_password": self.password,
                "new_password": "a-new-secure-passphrase",
                "confirm_password": "a-new-secure-passphrase",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Password changed", response.data)
        self.assertEqual(self.client.get("/").status_code, 302)
        old_login = self.client.post("/login", data={"email": "user@example.com", "password": self.password})
        self.assertIn(b"Invalid email or password", old_login.data)
        new_login = self.client.post(
            "/login", data={"email": "user@example.com", "password": "a-new-secure-passphrase"}
        )
        self.assertEqual(new_login.status_code, 302)

    def test_account_deletion_requires_password_and_confirmation(self):
        self.signup()
        response = self.client.post(
            "/delete_account", data={"current_password": "wrong-password", "confirm_deletion": "y"}
        )
        self.assertEqual(response.status_code, 400)
        with self.app.app_context():
            self.assertEqual(db.session.scalar(db.select(db.func.count(User.id))), 1)
        response = self.client.post(
            "/delete_account", data={"current_password": self.password, "confirm_deletion": "y"}
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.assertEqual(db.session.scalar(db.select(db.func.count(User.id))), 0)

    def test_security_headers_are_present(self):
        response = self.client.get("/landing")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])
        self.assertIn("'nonce-", response.headers["Content-Security-Policy"])

    def test_inline_scripts_receive_the_response_csp_nonce(self):
        self.signup()
        for path in ("/measurements", "/create_workout"):
            with self.subTest(path=path):
                response = self.client.get(path)
                policy = response.headers["Content-Security-Policy"]
                nonce = policy.split("'nonce-", 1)[1].split("'", 1)[0]
                self.assertIn(f'nonce="{nonce}"'.encode(), response.data)

    def test_duplicate_username_is_rejected(self):
        self.signup()
        self.client.post("/logout")
        response = self.signup("different@example.com", "USER123")
        self.assertIn(b"username is already taken", response.data)

    def test_routine_and_workout_session_lifecycle(self):
        self.signup()
        with self.app.app_context():
            exercise_ids = list(db.session.scalars(db.select(Exercise.id).limit(2)))
        response = self.client.post(
            "/create_workout",
            data={"name": "Push Day", "description": "Test routine", "exercises": exercise_ids},
            follow_redirects=True,
        )
        self.assertIn(b"Push Day", response.data)
        with self.app.app_context():
            workout_id = db.session.scalar(db.select(Workout.id))

        response = self.client.post("/start_empty_workout", json={"workout_id": workout_id})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(len(payload["exercises"]), 2)
        session_id = payload["session_id"]
        exercise_id = payload["exercises"][0]["id"]

        response = self.client.post(
            "/add_exercise_set",
            json={"session_id": session_id, "exercise_id": exercise_id, "set_number": 1, "reps": 8, "weight": 60},
        )
        self.assertEqual(response.status_code, 200)
        self.client.post("/end_workout_session", json={"session_id": session_id, "workout_name": "Push Day"})
        with self.app.app_context():
            session = db.session.get(WorkoutSession, session_id)
            self.assertIsNotNone(session.end_time)
            self.assertEqual(db.session.scalar(db.select(db.func.count(ExerciseSet.id))), 1)

    def test_routine_can_be_viewed_and_edited_only_by_its_owner(self):
        self.signup()
        with self.app.app_context():
            exercise_ids = list(db.session.scalars(db.select(Exercise.id).order_by(Exercise.id).limit(3)))
        self.client.post(
            "/create_workout",
            data={"name": "Original routine", "description": "Before", "exercises": exercise_ids[:2]},
        )
        with self.app.app_context():
            workout_id = db.session.scalar(db.select(Workout.id).where(Workout.name == "Original routine"))
        response = self.client.get(f"/routine/{workout_id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Edit your routine", response.data)
        response = self.client.post(
            f"/routine/{workout_id}",
            data={"name": "Updated routine", "description": "After", "exercises": exercise_ids},
            follow_redirects=True,
        )
        self.assertIn(b"Routine updated", response.data)
        with self.app.app_context():
            workout = db.session.get(Workout, workout_id)
            self.assertEqual(workout.name, "Updated routine")
            self.assertEqual({item.id for item in workout.exercises}, set(exercise_ids))
        self.client.post("/logout")
        self.signup("other@example.com", "other-user")
        self.assertEqual(self.client.get(f"/routine/{workout_id}").status_code, 404)

    def test_active_workout_is_recovered_instead_of_duplicated(self):
        self.signup()
        first = self.client.post("/start_empty_workout", json={}).get_json()
        second = self.client.post("/start_empty_workout", json={}).get_json()
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertEqual(first["session_id"], second["session_id"])
        response = self.client.get("/tracking")
        self.assertIn(f'"id": {first["session_id"]}'.encode(), response.data)
        with self.app.app_context():
            self.assertEqual(db.session.scalar(db.select(db.func.count(WorkoutSession.id))), 1)

    def test_sets_are_updated_deleted_and_completed_sessions_are_immutable(self):
        self.signup()
        with self.app.app_context():
            exercise_id = db.session.scalar(db.select(Exercise.id))
        session_id = self.client.post("/start_empty_workout", json={}).get_json()["session_id"]
        self.client.post(
            "/add_session_exercise", json={"session_id": session_id, "exercise_id": exercise_id}
        )
        for reps in (8, 10):
            response = self.client.post(
                "/add_exercise_set",
                json={
                    "session_id": session_id,
                    "exercise_id": exercise_id,
                    "set_number": 1,
                    "reps": reps,
                    "weight": 50,
                    "rest_time": 90,
                },
            )
            self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            self.assertEqual(db.session.scalar(db.select(db.func.count(ExerciseSet.id))), 1)
            self.assertEqual(db.session.scalar(db.select(ExerciseSet.reps)), 10)

        response = self.client.post(
            "/end_workout_session",
            json={"session_id": session_id, "workout_name": "Upper Body", "notes": "Strong session"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.client.post(
                "/add_exercise_set",
                json={"session_id": session_id, "exercise_id": exercise_id, "set_number": 2, "reps": 5},
            ).status_code,
            404,
        )
        with self.app.app_context():
            session = db.session.get(WorkoutSession, session_id)
            self.assertEqual(session.name, "Upper Body")
            self.assertEqual(session.notes, "Strong session")

    def test_active_workout_supports_notes_ordering_and_set_deletion(self):
        self.signup()
        with self.app.app_context():
            exercise_ids = list(db.session.scalars(db.select(Exercise.id).limit(2)))
        session_id = self.client.post("/start_empty_workout", json={}).get_json()["session_id"]
        for exercise_id in exercise_ids:
            self.assertEqual(
                self.client.post(
                    "/add_session_exercise", json={"session_id": session_id, "exercise_id": exercise_id}
                ).status_code,
                200,
            )
        response = self.client.post(
            "/reorder_session_exercises",
            json={"session_id": session_id, "exercise_ids": list(reversed(exercise_ids))},
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            "/update_workout_session",
            json={"session_id": session_id, "name": "Evening training", "notes": "Felt recovered"},
        )
        self.assertEqual(response.status_code, 200)
        for set_number in (1, 2):
            self.client.post(
                "/add_exercise_set",
                json={
                    "session_id": session_id,
                    "exercise_id": exercise_ids[0],
                    "set_number": set_number,
                    "reps": 12,
                },
            )
        self.assertEqual(
            self.client.post(
                "/delete_exercise_set",
                json={"session_id": session_id, "exercise_id": exercise_ids[0], "set_number": 1},
            ).status_code,
            200,
        )
        with self.app.app_context():
            session = db.session.get(WorkoutSession, session_id)
            self.assertEqual([item.exercise_id for item in session.session_exercises], list(reversed(exercise_ids)))
            self.assertEqual(session.name, "Evening training")
            self.assertEqual(session.notes, "Felt recovered")
            remaining_set = db.session.scalar(db.select(ExerciseSet))
            self.assertEqual(remaining_set.set_number, 1)

        self.assertEqual(
            self.client.post(
                "/remove_session_exercise",
                json={"session_id": session_id, "exercise_id": exercise_ids[1]},
            ).status_code,
            200,
        )
        with self.app.app_context():
            session = db.session.get(WorkoutSession, session_id)
            self.assertEqual([item.order for item in session.session_exercises], [1])

    def test_empty_workout_cannot_be_completed(self):
        self.signup()
        session_id = self.client.post("/start_empty_workout", json={}).get_json()["session_id"]
        response = self.client.post("/end_workout_session", json={"session_id": session_id})
        self.assertEqual(response.status_code, 409)
        self.assertIn(b"at least one completed set", response.data)

    def test_progress_report_calculates_volume_records_frequency_and_history(self):
        self.signup()
        now = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)
        with self.app.app_context():
            user = db.session.scalar(db.select(User).where(User.email == "user@example.com"))
            exercise = db.session.scalar(db.select(Exercise).order_by(Exercise.id))
            completed = WorkoutSession(
                user=user,
                name="Strength session",
                start_time=now - timedelta(days=1, hours=1),
                end_time=now - timedelta(days=1),
            )
            session_exercise = SessionExercise(
                workout_session=completed,
                exercise=exercise,
                order=1,
                exercise_name="Historical Exercise Name",
                target_name="Historical Target",
                equipment_name="barbell",
            )
            session_exercise.sets.extend(
                [
                    ExerciseSet(set_number=1, reps=5, weight=100, is_completed=True),
                    ExerciseSet(set_number=2, reps=10, weight=80, is_completed=True),
                    ExerciseSet(set_number=3, reps=20, weight=None, is_completed=True),
                    ExerciseSet(set_number=4, reps=15, weight=200, is_completed=True),
                    ExerciseSet(set_number=5, reps=1, weight=500, is_completed=False),
                ]
            )
            active = WorkoutSession(user=user, name="Ignored active workout", start_time=now)
            active_exercise = SessionExercise(
                workout_session=active,
                exercise=exercise,
                order=1,
                exercise_name=exercise.name,
                target_name=exercise.target,
                equipment_name=exercise.equipment,
            )
            active_exercise.sets.append(
                ExerciseSet(set_number=1, reps=10, weight=999, is_completed=True)
            )
            db.session.add_all([completed, active])
            db.session.commit()
            exercise_id = exercise.id

            report = progress_report(user.id, "metric", range_days=30, now=now)
            self.assertEqual(report["summary"]["workouts"], 1)
            self.assertEqual(report["summary"]["sets"], 4)
            self.assertEqual(report["summary"]["reps"], 50)
            self.assertEqual(report["summary"]["volume"], 4300)
            self.assertEqual(report["summary"]["durationHours"], 1)
            self.assertEqual(report["streakWeeks"], 1)
            self.assertEqual(report["records"][0]["name"], "Historical Exercise Name")
            self.assertEqual(report["records"][0]["heaviestWeight"], 200)
            self.assertEqual(report["records"][0]["estimatedOneRepMax"], 116.7)
            self.assertEqual(report["records"][0]["maxReps"], 20)
            self.assertEqual(report["exerciseHistory"][0]["volume"], 4300)
        response = self.client.get(f"/progress?range=30&exercise_id={exercise_id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Historical Exercise Name", response.data)
        self.assertIn(b"Estimated 1RM trend", response.data)
        self.assertIn(b"View accessible weekly data table", response.data)

    def test_progress_is_scoped_to_the_authenticated_user(self):
        self.signup("owner@example.com", "owner")
        now = datetime.now(timezone.utc)
        with self.app.app_context():
            owner = db.session.scalar(db.select(User).where(User.email == "owner@example.com"))
            exercise = db.session.scalar(db.select(Exercise).order_by(Exercise.id))
            session = WorkoutSession(
                user=owner,
                name="Owner workout",
                start_time=now - timedelta(hours=1),
                end_time=now,
            )
            item = SessionExercise(
                workout_session=session,
                exercise=exercise,
                order=1,
                exercise_name=exercise.name,
                target_name=exercise.target,
                equipment_name=exercise.equipment,
            )
            item.sets.append(ExerciseSet(set_number=1, reps=5, weight=100, is_completed=True))
            db.session.add(session)
            db.session.commit()
        self.client.post("/logout")
        self.signup("viewer@example.com", "viewer")
        response = self.client.get("/progress")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Complete a workout to start building personal records", response.data)
        self.assertNotIn(b"Owner workout", response.data)

    def test_imperial_preference_converts_inputs_and_workout_loads(self):
        self.signup()
        response = self.client.post(
            "/profile-info",
            data={"first_name": "Test", "username": "user123", "unit_system": "imperial"},
            follow_redirects=True,
        )
        self.assertIn(b"Imperial", response.data)
        self.client.post(
            "/measurements",
            data={"weight-weight": 220.4623, "weight-date": "2026-08-20", "weight-submit": "Log weight"},
        )
        with self.app.app_context():
            self.assertAlmostEqual(db.session.scalar(db.select(Weight.weight)), 100, places=2)
            exercise_id = db.session.scalar(db.select(Exercise.id))
        session_id = self.client.post("/start_empty_workout", json={}).get_json()["session_id"]
        self.client.post(
            "/add_session_exercise", json={"session_id": session_id, "exercise_id": exercise_id}
        )
        self.client.post(
            "/add_exercise_set",
            json={
                "session_id": session_id,
                "exercise_id": exercise_id,
                "set_number": 1,
                "reps": 5,
                "weight": 220.4623,
            },
        )
        with self.app.app_context():
            self.assertAlmostEqual(db.session.scalar(db.select(ExerciseSet.weight)), 100, places=2)
        response = self.client.get("/tracking")
        self.assertIn(b'"weight": 220.5', response.data)
        self.assertIn(b'data-weight-unit="lb"', response.data)

    def test_user_cannot_modify_another_users_session(self):
        self.signup("owner@example.com", "owner")
        response = self.client.post("/start_empty_workout", json={})
        session_id = response.get_json()["session_id"]
        self.client.post("/logout")
        self.signup("attacker@example.com", "attacker")
        self.assertEqual(self.client.post("/end_workout_session", json={"session_id": session_id}).status_code, 404)
        self.assertEqual(self.client.post("/delete_session", json={"sessionId": session_id}).status_code, 404)

    def test_measurements_are_scoped_and_updated_by_date(self):
        self.signup()
        self.client.post("/measurements", data={"height-height": 180, "height-date": "2026-08-16", "height-submit": "Log height"})
        self.client.post("/measurements", data={"weight-weight": 80.5, "weight-date": "2026-08-16", "weight-submit": "Log weight"})
        self.client.post("/measurements", data={"weight-weight": 79.5, "weight-date": "2026-08-16", "weight-submit": "Log weight"})
        with self.app.app_context():
            self.assertEqual(db.session.scalar(db.select(db.func.count(Height.id))), 1)
            self.assertEqual(db.session.scalar(db.select(db.func.count(Weight.id))), 1)
            self.assertEqual(db.session.scalar(db.select(Weight.weight)), 79.5)


if __name__ == "__main__":
    unittest.main()
