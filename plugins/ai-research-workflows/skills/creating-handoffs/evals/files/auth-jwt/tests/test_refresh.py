import unittest

from src.auth.session import SessionManager


class TestRefresh(unittest.TestCase):
    def test_refresh_issues_a_valid_token(self):
        sm = SessionManager(b"test-key")
        token = sm.login("u1", now=1000)
        self.assertEqual(sm.validate(sm.refresh(token, now=1100), now=1200)["sub"], "u1")


if __name__ == "__main__":
    unittest.main()
