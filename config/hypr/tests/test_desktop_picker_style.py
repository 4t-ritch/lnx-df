"""Run with python3 config/hypr/tests/test_desktop_picker_style.py."""
import importlib.util
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GdkPixbuf, Gtk

SOURCE = Path(__file__).resolve().parents[1] / "scripts/desktop-picker-gtk.py"
spec = importlib.util.spec_from_file_location("desktop_picker_style_test", SOURCE)
picker = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = picker
spec.loader.exec_module(picker)


def flush():
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)


class PickerStyleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provider = Gtk.CssProvider()
        cls.errors = []
        cls.provider.connect("parsing-error", lambda _p, _s, error: cls.errors.append(str(error)))
        cls.provider.load_from_data(picker.CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), cls.provider,
                                                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def test_image_pixels_reach_square_corners(self):
        window = Gtk.OffscreenWindow()
        self.addCleanup(window.destroy)
        preview = picker.ImagePreview()
        pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, False, 8, 112, 63)
        pixbuf.fill(0x117FE7FF)
        preview.set_pixbuf(pixbuf)
        window.add(preview)
        window.show_all()
        flush()
        rendered = window.get_pixbuf()
        data, stride, channels = rendered.get_pixels(), rendered.get_rowstride(), rendered.get_n_channels()
        for x, y in ((3, 3), (108, 3), (3, 59), (108, 59), (56, 31)):
            offset = y * stride + x * channels
            self.assertEqual(tuple(data[offset:offset + 3]), (17, 127, 231), (x, y))

    def test_keyboard_focus_highlights_the_emoji_rectangle(self):
        window = Gtk.OffscreenWindow()
        self.addCleanup(window.destroy)
        flow = Gtk.FlowBox()
        flow.get_style_context().add_class("emoji-flow")
        button = Gtk.Button(label="😀")
        button.get_style_context().add_class("emoji-button")
        flow.add(button)
        window.add(flow)
        window.show_all()
        child = flow.get_children()[0]
        child.set_state_flags(Gtk.StateFlags.FOCUSED, False)
        flush()
        border = button.get_style_context().get_border_color(button.get_state_flags())
        self.assertGreaterEqual(border.alpha, 0.70)
        self.assertEqual(child.get_style_context().get_property("outline-width", child.get_state_flags()), 0)
        self.assertFalse(self.errors)

    def test_png_is_decoded_and_scaled_without_real_clipboard_access(self):
        fixture = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, False, 8, 320, 180)
        fixture.fill(0x117FE7FF)
        success, png = fixture.save_to_bufferv("png", [], [])
        self.assertTrue(success)
        with patch.object(picker, "run_capture", return_value=bytes(png)) as capture:
            thumbnail = picker.load_image_preview("1\tfixture.png")
        capture.assert_called_once_with(["cliphist", "decode"], input_bytes=b"1\tfixture.png\n")
        self.assertIsNotNone(thumbnail)
        self.assertEqual((thumbnail.get_width(), thumbnail.get_height()), (112, 63))
        self.assertEqual(tuple(thumbnail.get_pixels()[:3]), (17, 127, 231))


if __name__ == "__main__":
    unittest.main()
