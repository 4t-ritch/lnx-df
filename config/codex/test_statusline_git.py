import unittest
from unittest.mock import patch

from config.claude import statusline as claude
from config.codex import statusline as codex


class GitStatusTests(unittest.TestCase):
    def test_fish_symbols_on_both_statuslines(self):
        for module, git_name in ((claude, "git_output"), (codex, "git")):
            for headers, entries, expected in (
                ("", "", "main"),
                ("", "? untracked\n", "main !"),
                ("# branch.ab +1 -0\n", "", "main >"),
                ("# branch.ab +0 -2\n", "", "main <"),
                ("# branch.ab +1 -2\n", "1 M. tracked\n", "main ><!"),
            ):
                with self.subTest(module=module.__name__, expected=expected):
                    with patch.object(module, git_name, return_value=(
                        "# branch.oid abcdef0123456\n# branch.head main\n"
                        + headers + entries
                    )):
                        self.assertEqual(module.git_branch("."), expected)
