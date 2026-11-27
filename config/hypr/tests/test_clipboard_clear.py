#!/usr/bin/env python3
"""Black-box tests for clipboard-clear notifications using isolated command mocks."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts" / "clipboard-clear.sh"


class ClipboardClearTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="clipboard-clear-test-")
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.state = self.root / "clipboard-state"
        self.state.write_text("fixture entry\n", encoding="utf-8")
        self.log = self.root / "calls.log"

    def tearDown(self):
        self.temp.cleanup()

    def command(self, name, body):
        path = self.bin / name
        path.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8")
        path.chmod(0o755)
        return path

    def run_script(self):
        env = os.environ.copy()
        env["PATH"] = str(self.bin)
        env["CALL_LOG"] = str(self.log)
        env["CLIPBOARD_STATE"] = str(self.state)
        return subprocess.run(
            ["/bin/bash", str(SCRIPT)], env=env, text=True, capture_output=True, check=False
        )

    def test_success_wipes_fixture_then_sends_quiet_swaync_notification(self):
        self.command(
            "cliphist",
            'printf "cliphist %s\\n" "$*" >> "$CALL_LOG"\n'
            'test "$1" = wipe && : > "$CLIPBOARD_STATE"',
        )
        self.command(
            "notify-send",
            'printf "notify-send %s\\n" "$*" >> "$CALL_LOG"',
        )

        result = self.run_script()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.state.read_text(encoding="utf-8"), "")
        lines = self.log.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[0], "cliphist wipe")
        self.assertIn("--app-name=Clipboard", lines[1])
        self.assertIn("--expire-time=2500", lines[1])
        self.assertIn("--hint=boolean:suppress-sound:true", lines[1])
        self.assertIn("--hint=boolean:transient:true", lines[1])
        self.assertTrue(lines[1].endswith("Clipboard history cleared"), lines[1])

    def test_missing_cliphist_keeps_error_status_and_uses_quiet_swaync_alert(self):
        self.command(
            "notify-send",
            'printf "notify-send %s\\n" "$*" >> "$CALL_LOG"',
        )

        result = self.run_script()

        self.assertEqual(result.returncode, 1)
        lines = self.log.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        self.assertIn("--app-name=Clipboard", lines[0])
        self.assertIn("--expire-time=3500", lines[0])
        self.assertIn("--hint=boolean:suppress-sound:true", lines[0])
        self.assertIn("--hint=boolean:transient:true", lines[0])
        self.assertTrue(lines[0].endswith("cliphist is not installed"), lines[0])
        self.assertEqual(self.state.read_text(encoding="utf-8"), "fixture entry\n")

    def test_hyprctl_fallback_retains_existing_visual_message_and_duration(self):
        self.command(
            "cliphist",
            'printf "cliphist %s\\n" "$*" >> "$CALL_LOG"\n'
            'test "$1" = wipe && : > "$CLIPBOARD_STATE"',
        )
        self.command(
            "hyprctl",
            'printf "hyprctl %s\\n" "$*" >> "$CALL_LOG"',
        )

        result = self.run_script()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.log.read_text(encoding="utf-8").splitlines(),
            [
                "cliphist wipe",
                "hyprctl notify 1 2500 rgb(a6e3a1) Clipboard history cleared",
            ],
        )

    def test_missing_cliphist_uses_hyprctl_fallback_and_still_exits_one(self):
        self.command(
            "hyprctl",
            'printf "hyprctl %s\\n" "$*" >> "$CALL_LOG"',
        )

        result = self.run_script()

        self.assertEqual(result.returncode, 1)
        self.assertEqual(
            self.log.read_text(encoding="utf-8").splitlines(),
            ["hyprctl notify 1 3500 rgb(ff6666) cliphist is not installed"],
        )
        self.assertEqual(self.state.read_text(encoding="utf-8"), "fixture entry\n")


if __name__ == "__main__":
    unittest.main()
