"""Check the bar layout without launching desktop controls."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LayoutTests(unittest.TestCase):
    def test_clocks_keep_date_and_time_without_calendar(self):
        bars = json.loads((ROOT / 'config.jsonc').read_text())
        self.assertEqual([bar['output'] for bar in bars], [['DP-2'], ['HDMI-A-1']])
        for bar in bars:
            with self.subTest(output=bar['output']):
                self.assertIn('clock', bar['modules-right'])
                self.assertEqual(bar['clock'], {
                    'format': '{:%a %d  %H:%M}', 'tooltip': False,
                })
        self.assertFalse((ROOT / 'scripts/calendar-popup.py').exists())

    def test_control_center_and_power_buttons_are_removed(self):
        bars = json.loads((ROOT / 'config.jsonc').read_text())
        for bar in bars:
            for module in ('custom/control-center', 'custom/power'):
                with self.subTest(output=bar['output'], module=module):
                    self.assertNotIn(module, bar['modules-right'])
                    self.assertNotIn(module, bar)
        css = (ROOT / 'style.css').read_text()
        self.assertNotIn('#custom-control-center', css)
        self.assertNotIn('#custom-power', css)

    def test_existing_workspace_keyboard_and_tray_layout_is_preserved(self):
        bars = json.loads((ROOT / 'config.jsonc').read_text())
        for bar in bars:
            self.assertEqual(bar['modules-left'], ['hyprland/workspaces', 'hyprland/window'])
            self.assertEqual(bar['modules-center'], [])
            self.assertEqual(bar['custom/keyboard']['on-click'],
                             '~/.config/waybar/scripts/keyboard-layout.sh --menu')
        self.assertEqual(bars[0]['modules-right'], ['tray', 'custom/keyboard', 'clock'])
        self.assertEqual(bars[1]['modules-right'], ['custom/keyboard', 'clock'])


if __name__ == '__main__':
    unittest.main()
