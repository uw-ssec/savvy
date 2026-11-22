import unittest

from src.auth.session import SessionManager


class TestLogout(unittest.TestCase):
    def test_revoke(self):
        sm = SessionManager(b"test-key")
        token = sm.login("u1", now=1000)
        sm.logout(token)
        with self.assertRaises(ValueError):
            sm.validate(token, now=1001)


if __name__ == "__main__":
    unittest.main()
