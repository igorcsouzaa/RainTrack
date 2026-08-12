import unittest

import app as raintrack
from werkzeug.security import check_password_hash


class AppTests(unittest.TestCase):
    def setUp(self):
        raintrack.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = raintrack.app.test_client()

    def test_public_pages_render(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/about").status_code, 200)

    def test_private_page_redirects_anonymous_user(self):
        response = self.client.get("/graphs")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/"))

    def test_post_without_csrf_is_rejected(self):
        self.assertEqual(self.client.post("/", data={"entry": "x", "password": "y"}).status_code, 400)

    def test_initial_database_password_hash(self):
        stored = "pbkdf2:sha256:600000$0XI5OxuHLgspSnwm$62718ce06d9522aa25f89cc07adeaddcceb460b9069763124979b85a204eb7e0"
        self.assertTrue(check_password_hash(stored, "RainTrack@123"))

    def test_guest_cannot_access_administration(self):
        with self.client.session_transaction() as session:
            session.update(user_id="guest", user_name="Convidado", user_role=0, is_guest=True)
        self.assertEqual(self.client.get("/admin").status_code, 403)
        self.assertEqual(self.client.get("/stations").status_code, 403)
        self.assertEqual(self.client.get("/parameters").status_code, 403)

    def test_guest_profile_returns_home_without_database(self):
        with self.client.session_transaction() as session:
            session.update(user_id="guest", user_name="Convidado", user_role=0, is_guest=True)
        response = self.client.get("/user_profile")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/home"))

    def test_station_validation(self):
        values, error = raintrack.validate_station("Estação", "-23.2", "-45.9", "AA:BB:CC:DD:EE:FF", ["1"])
        self.assertIsNone(error)
        self.assertEqual(values[3], "AABBCCDDEEFF")
        self.assertIsNotNone(raintrack.validate_station("Estação", "91", "0", "AABBCCDDEEFF", ["1"])[1])

    def test_user_and_parameter_validation(self):
        self.assertIsNone(raintrack.validate_user("Nome", "nome@example.com", "12345678901", "0", "senha-forte"))
        self.assertIsNotNone(raintrack.validate_user("Nome", "invalido", "123", "3", "curta"))
        self.assertIsNone(raintrack.validate_parameter("Temperatura", "°C", "temperature", "1")[1])
        self.assertIsNotNone(raintrack.validate_parameter("X", "u", "script", "99")[1])


if __name__ == "__main__":
    unittest.main()
