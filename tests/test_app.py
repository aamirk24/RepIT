import unittest

from app import create_app, db
from app.models import Exercise, ExerciseSet, Height, SessionExercise, User, Weight, Workout, WorkoutSession
from app.seed import seed_exercises


class RepITTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "WTF_CSRF_ENABLED": False,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "SECRET_KEY": "test-secret",
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
                "password": "correct-horse",
                "confirm": "correct-horse",
            },
            follow_redirects=True,
        )

    def test_app_starts_without_network_or_api_key(self):
        response = self.client.get("/landing")
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            self.assertEqual(db.session.scalar(db.select(db.func.count(Exercise.id))), 20)

    def test_signup_login_logout_and_protected_route(self):
        self.assertEqual(self.client.get("/").status_code, 302)
        response = self.signup()
        self.assertIn(b"Welcome Back", response.data)

    def test_authenticated_pages_render(self):
        self.signup()
        for path in ("/", "/exercise", "/create_workout", "/tracking", "/profile-info", "/measurements", "/account", "/faq"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
        self.client.post("/logout")
        response = self.client.post(
            "/login", data={"email": "user@example.com", "password": "correct-horse"}, follow_redirects=True
        )
        self.assertIn(b"Welcome Back", response.data)

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
