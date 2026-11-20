import unittest

from config.codex import statusline


class UsageDisplayTests(unittest.TestCase):
    def test_remaining_percent_is_inverse_of_used_percent(self):
        self.assertEqual(statusline.remaining_percent(0), 100)
        self.assertEqual(statusline.remaining_percent(28), 72)
        self.assertEqual(statusline.remaining_percent(100), 0)


if __name__ == "__main__":
    unittest.main()
