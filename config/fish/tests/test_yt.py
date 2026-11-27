"""Offline tests for the public Fish yt command; never download or read cookies."""
import json
import errno
import fcntl
import pty
import re
import struct
import termios
import unicodedata
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from yt_dlp import YoutubeDL

FUNCTION = Path(__file__).resolve().parents[1] / 'functions/yt.fish'
MOCK = '''#!/usr/bin/python3
import json, os, sys
from pathlib import Path
from yt_dlp import YoutubeDL
args = sys.argv[1:]
with open(os.environ['YT_CALLS'], 'a') as f:
    f.write(json.dumps(args) + '\\n')
if os.environ.get('YT_AUTH') and '--cookies-from-browser' not in args:
    print('ERROR: Sign in required')
    sys.exit(1)
if os.environ.get('YT_FAIL'):
    print('ERROR: unavailable video')
    sys.exit(7)
template = args[args.index('--progress-template') + 1]
output = args[args.index('-o') + 1]
playlist = 'playlist' in args[-1]
with YoutubeDL({'quiet': True, 'cachedir': False, 'outtmpl': output}) as y:
    for title in (['First | Song', 'Second Song'] if playlist else ['Single Song']):
        if os.environ.get('YT_LONG_TITLE'):
            title = title + ' 日本語-long-title' * 35
        info = dict(id='fixture', title=title, artist='Artist', ext='webm')
        if playlist:
            info['playlist_title'] = 'My Playlist'
        filename = y.prepare_filename(info)
        for percent in (['50.0%'] * 40 + ['100.0%'] if os.environ.get('YT_MANY_PROGRESS') else ['50.0%', '100.0%']):
            print(y.evaluate_outtmpl(template, {'info': info, 'progress': {
                '_percent_str': percent, '_speed_str': ('100.50MiB/s' if percent == '100.0%' else '1MiB/s') if os.environ.get('YT_VARY_SPEED') else '1MiB/s',
                '_eta_str': 'NA', 'filename': filename}}))
        final = str(Path(filename).with_suffix('.mkv' if '-x' not in args else '.ogg'))
        if '--print' in args:
            marker = args[args.index('--print') + 1].split(':', 1)[1]
            print(y.evaluate_outtmpl(marker, {'filepath': final}))
'''


class YtTests(unittest.TestCase):
    def run_yt(self, *args, terminal_width=None, local_bundle=False, **extra):
        with tempfile.TemporaryDirectory(prefix='yt-test-') as tmp:
            root = Path(tmp)
            mock = root / 'yt-dlp'
            mock.write_text(MOCK)
            mock.chmod(0o755)
            # Keep this suite focused on Fish option/progress/auth routing.
            # The real Python engine has separate local-media integration tests.
            launcher = root / 'python3'
            launcher.write_text('#!/bin/sh\nshift\nexec yt-dlp "$@"\n')
            launcher.chmod(0o755)
            bundle = root / '.local/share/yt/yt-dlp.pyz'
            if local_bundle:
                bundle.parent.mkdir(parents=True)
                bundle.touch()
                launcher.write_text(launcher.read_text().replace('shift', 'test "${PYTHONPATH%%:*}" = "$HOME/.local/share/yt/yt-dlp.pyz" || exit 8\nshift'))
            calls = root / 'calls.jsonl'
            env = dict(os.environ, HOME=tmp, XDG_CONFIG_HOME=tmp,
                       PATH=tmp + ':' + os.environ['PATH'], YT_CALLS=str(calls),
                       COLUMNS=str(terminal_width or 180))
            env.update(extra)
            command = ['fish', '--no-config', '-c', 'source "$argv[1]"; yt $argv[2..]',
                       str(FUNCTION), *args]
            if terminal_width is None:
                result = subprocess.run(command, cwd=tmp, env=env, capture_output=True)
            else:
                master, slave = pty.openpty()
                fcntl.ioctl(slave, termios.TIOCSWINSZ,
                            struct.pack('HHHH', 24, terminal_width, 0, 0))
                process = subprocess.Popen(command, cwd=tmp, env=env, stdout=slave,
                                           stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
                os.close(slave)
                chunks = []
                try:
                    while True:
                        try:
                            chunk = os.read(master, 65536)
                        except OSError as err:
                            if err.errno == errno.EIO:
                                break
                            raise
                        if not chunk:
                            break
                        chunks.append(chunk)
                finally:
                    os.close(master)
                _, stderr = process.communicate(timeout=10)
                result = subprocess.CompletedProcess(command, process.returncode,
                                                     b''.join(chunks), stderr)
            # Preserve CR characters; text=True would turn redraws into newlines.
            result.stdout = result.stdout.decode()
            result.stderr = result.stderr.decode()
            recorded = [json.loads(line) for line in calls.read_text().splitlines()] if calls.exists() else []
            return result, recorded

    def test_user_local_bundle_is_used_when_present(self):
        result, _ = self.run_yt('-a', 'https://example.invalid/video', local_bundle=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_progress_names_and_completed_playlist_items(self):
        result, _ = self.run_yt('-v', 'https://example.invalid/playlist')
        self.assertEqual(result.returncode, 0, result.stderr)
        # yt-dlp sanitizes a literal pipe in the on-disk filename.
        for title in ['First ｜ Song', 'Second Song']:
            self.assertIn(f'{title}.webm [', result.stdout)
            self.assertIn(f'Downloaded: My Playlist/{title}.mkv\n', result.stdout)
        self.assertIn('50.0%', result.stdout)
        self.assertRegex(result.stdout, r'ETA\s+--:--')

    def test_terminal_progress_redraws_without_wrapping_long_unicode_names(self):
        for columns in [35, 80, 120]:
            with self.subTest(columns=columns):
                result, _ = self.run_yt('-v', 'https://example.invalid/video',
                    terminal_width=columns, YT_LONG_TITLE='1', YT_MANY_PROGRESS='1')
                self.assertEqual(result.returncode, 0, result.stderr)
                progress = [chunk for chunk in result.stdout.split('\r\x1b[2K')
                            if 'ETA ' in chunk or ('%' in chunk and not chunk.startswith('Downloaded:'))]
                self.assertEqual(len(progress), 41)
                for chunk in progress:
                    self.assertNotIn('\n', chunk)
                    width = sum(0 if unicodedata.combining(c) else
                                2 if unicodedata.east_asian_width(c) in 'WF' else 1
                                for c in chunk)
                    self.assertLessEqual(width, columns - 1,
                                         'Progress wraps and leaves previous physical rows behind')
                self.assertIn('100.0%', progress[-1])
                self.assertEqual(result.stdout.count('Downloaded:'), 1)
                self.assertIn(' 日本語-long-title' * 35, result.stdout)

    def test_bar_width_is_stable_when_speed_label_changes(self):
        result, _ = self.run_yt('-v', 'https://example.invalid/video',
                                terminal_width=75, YT_VARY_SPEED='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        bars = re.findall(r'\[([█░]+)\]', result.stdout)
        self.assertEqual(len(bars), 2)
        self.assertEqual(len(bars[0]), len(bars[1]))

    def test_playlist_directory_in_both_modes(self):
        for mode in ['-a', '-v']:
            with self.subTest(mode=mode):
                result, calls = self.run_yt(mode, 'https://example.invalid/playlist')
                self.assertEqual(result.returncode, 0, result.stderr)
                args = calls[0]
                with YoutubeDL({'quiet': True, 'cachedir': False,
                                'outtmpl': args[args.index('-o') + 1]}) as y:
                    name = y.prepare_filename(dict(id='x', title='Song', artist='Artist',
                                                   ext='webm', playlist_title='My Playlist'))
                self.assertEqual(Path(name).parent, Path('My Playlist'))
                self.assertEqual(Path(name).name, 'Song.webm')

    def test_existing_modes_and_single_video_location(self):
        for mode in [[], ['-a'], ['--audio'], ['-v'], ['--video']]:
            with self.subTest(mode=mode):
                result, calls = self.run_yt(*mode, 'https://example.invalid/video')
                self.assertEqual(result.returncode, 0, result.stderr)
                args = calls[0]
                video = mode in [['-v'], ['--video']]
                self.assertEqual(args[args.index('-f') + 1],
                                 'bestvideo*+bestaudio/best' if video else 'bestaudio/best')
                self.assertEqual('-x' in args, not video)
                with YoutubeDL({'quiet': True, 'cachedir': False,
                                'outtmpl': args[args.index('-o') + 1]}) as y:
                    name = y.prepare_filename(dict(id='x', title='Song', artist='Artist', ext='webm'))
                self.assertEqual(Path(name), Path('Song.webm'))
                self.assertIn('--embed-metadata', args)

    def test_caption_flags_apply_to_whole_playlist(self):
        for flag in ['-cc', '--captions']:
            with self.subTest(flag=flag):
                result, calls = self.run_yt('-v', flag, 'https://example.invalid/playlist')
                self.assertEqual(result.returncode, 0, result.stderr)
                args = calls[0]
                self.assertIn('--write-subs', args)
                self.assertIn('--write-auto-subs', args)
                self.assertEqual(args[args.index('--sub-langs') + 1], '(?i:es(?:[-_].*)?),-live_chat')
                self.assertNotIn('-cc', args)
                self.assertEqual(args[args.index('--sleep-subtitles') + 1], '5')

    def test_caption_language_choice_and_default_spanish(self):
        from yt_dlp import parse_options
        tracks = {lang: [{'ext': 'vtt', 'url': 'https://example.invalid/' + lang}]
                  for lang in ['es', 'es-419', 'en', 'pt', 'ja']}
        cases = [([], {'es', 'es-419'}), (['es'], {'es', 'es-419'}),
                 (['all'], set(tracks)), (['en,ja'], {'en', 'ja'})]
        for language, expected in cases:
            with self.subTest(language=language):
                result, calls = self.run_yt('-v', '-cc', *language, 'https://example.invalid/video')
                self.assertEqual(result.returncode, 0, result.stderr)
                opts = parse_options(['--ignore-config', *calls[0]]).ydl_opts
                # Authentication routing is tested separately; never open a real browser here.
                opts.pop('cookiesfrombrowser', None)
                with YoutubeDL(opts) as y:
                    self.assertEqual(set(y.process_subtitles('fixture', tracks, {})), expected)
                self.assertEqual(calls[0][-1], 'https://example.invalid/video')
        for flag in ['-cc=all', '--captions=all']:
            result, calls = self.run_yt('-a', flag, 'https://example.invalid/playlist')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(calls[0][calls[0].index('--sub-langs') + 1], 'all,-live_chat')
        result, calls = self.run_yt('-v', '-cc=es.*', 'https://example.invalid/video')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(calls)

    def test_subtitle_selection_keeps_all_languages_but_not_chat(self):
        with YoutubeDL({'quiet': True, 'cachedir': False, 'writesubtitles': True,
                        'writeautomaticsub': True,
                        'subtitleslangs': ['all', '-live_chat']}) as y:
            track = lambda url: [{'ext': 'vtt', 'url': url}]
            selected = y.process_subtitles('fixture',
                {'en': track('manual-en'), 'ja': track('manual-ja'),
                 'live_chat': track('chat')},
                {'en': track('auto-en'), 'es': track('auto-es')})
            self.assertEqual(set(selected), {'en', 'ja', 'es'})
            self.assertEqual(selected['en']['url'], 'manual-en')
            self.assertIsNone(y.process_subtitles('no-captions', {}, {}))

    def test_help_and_option_terminator(self):
        result, calls = self.run_yt('--help')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('-cc', result.stdout)
        self.assertFalse(calls)
        result, calls = self.run_yt('-v', '--', '-cc')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls[0][-1], '-cc')
        self.assertIn('--no-write-subs', calls[0])

    def test_captions_off_without_flag(self):
        result, calls = self.run_yt('-v', 'https://example.invalid/video')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--no-write-subs', calls[0])
        self.assertIn('--no-write-auto-subs', calls[0])

    def test_error_status_and_browser_session_from_first_attempt(self):
        result, calls = self.run_yt('-v', 'https://example.invalid/video', YT_FAIL='1')
        self.assertEqual(result.returncode, 7)
        self.assertIn('ERROR: unavailable video', result.stderr)
        self.assertEqual(len(calls), 1)
        result, calls = self.run_yt('-v', '-cc', 'https://example.invalid/video', YT_AUTH='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][calls[0].index('--cookies-from-browser') + 1], 'brave')
        self.assertIn('--write-subs', calls[0])

    def test_existing_invalid_arguments(self):
        for args in [[], ['-a', '-v', 'url'], ['--unknown', 'url']]:
            with self.subTest(args=args):
                result, calls = self.run_yt(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(calls)


if __name__ == '__main__':
    unittest.main()
