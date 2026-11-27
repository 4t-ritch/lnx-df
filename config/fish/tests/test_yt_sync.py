"""Offline reconciliation tests using real media, ffmpeg, and yt-dlp's file downloader."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
import unittest
import warnings
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/yt-sync.py'


def load_sync():
    spec = importlib.util.spec_from_file_location('yt_sync', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SyncTests(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings('ignore', category=ResourceWarning, module=r'yt_dlp.*|tempfile|importlib.*')
        self.temp = tempfile.TemporaryDirectory(prefix='yt-sync-test-')
        self.root = Path(self.temp.name)
        self.source = self.root / 'source.webm'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                        'color=c=black:s=32x32:r=10:d=2', '-f', 'lavfi', '-i',
                        'sine=frequency=440:duration=2', '-c:v', 'libvpx', '-c:a',
                        'libvorbis', '-metadata', 'purl=https://www.youtube.com/watch?v=fixture',
                        str(self.source)], check=True, capture_output=True)
        self.dest = self.root / 'downloads'
        self.dest.mkdir()
        self.sync = load_sync()
        self.addCleanup(self.temp.cleanup)

    def info(self, title='Song'):
        return dict(id='fixture', title=title, artist='Artist', extractor_key='Youtube',
                    webpage_url='https://www.youtube.com/watch?v=fixture',
                    url=self.source.as_uri(), protocol='file', ext='webm',
                    format_id='fixture', format='fixture', vcodec='vp8', acodec='vorbis',
                    duration=2, playlist_title='Playlist')

    def downloader(self, audio=False, captions=False):
        params = dict(quiet=True, no_warnings=True, cachedir=False, enable_file_urls=True,
                      outtmpl='%(playlist_title|.)s/%(artist)s - %(title)s.%(ext)s',
                      writesubtitles=captions, writeautomaticsub=captions,
                      subtitleslangs=['all', '-live_chat'],
                      overwrites=False, noprogress=True, postprocessors=[], final_ext='ogg' if audio else None)
        if audio:
            params['postprocessors'] = [dict(key='FFmpegExtractAudio', preferredcodec='vorbis',
                                             preferredquality='0')]
        return self.sync.SyncYoutubeDL(params, root=self.dest, audio=audio)

    def test_repeated_sync_and_title_change_skip_healthy_audio_and_video(self):
        for audio in [False, True]:
            with self.subTest(audio=audio), self.downloader(audio=audio) as y:
                y.process_info(self.info())
                paths = list((self.dest / 'Playlist').glob('*.ogg' if audio else '*.webm'))
                self.assertEqual(len(paths), 1)
                path = paths[0]
                before = path.read_bytes(), path.stat().st_mtime_ns
                with patch.object(self.sync.YoutubeDL, 'process_info', side_effect=AssertionError('downloaded twice')):
                    y.process_info(self.info('Renamed title'))
                self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

    def test_corrupt_and_incomplete_files_are_repaired_for_each_mode(self):
        for audio in [False, True]:
            with self.subTest(audio=audio), self.downloader(audio=audio) as y:
                y.process_info(self.info())
                state = json.loads((self.dest / '.yt-sync.json').read_text())
                entry = state['items'][y.item_key(self.info())]
                path = self.dest / entry['path']
                path.write_bytes(b'broken')
                y.process_info(self.info())
                self.assertGreater(path.stat().st_size, 100)
                # A decodable but short file must not pass based on decode alone.
                short = self.root / ('short.ogg' if audio else 'short.webm')
                subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-t', '0.2',
                                '-c', 'copy', str(short)], check=True, capture_output=True)
                path.write_bytes(short.read_bytes())
                y.process_info(self.info())
                self.assertGreater(float(self.sync.probe(path)['format']['duration']), 1.8)

    def test_validation_preserves_video_timestamp_precision(self):
        actual_run = subprocess.run
        def emulate_observed_muxer_rounding(command, **kwargs):
            if (command[0] == 'ffmpeg' and '-map' in command
                    and command[command.index('-map') + 1] == '0:0'
                    and '-enc_time_base' not in command):
                return subprocess.CompletedProcess(command, 0,
                    'out_time_us=2000000\n',
                    'Application provided invalid, non monotonically increasing dts to muxer')
            return actual_run(command, **kwargs)
        with patch.object(self.sync.subprocess, 'run', side_effect=emulate_observed_muxer_rounding):
            self.assertIsNotNone(self.sync.validate(self.source, self.info(), False))

    def test_deleted_indexed_video_uses_current_filename_template(self):
        with self.downloader(captions=True) as y:
            y.process_info(self.info())
            old = next((self.dest / 'Playlist').glob('*.webm'))
            old.unlink()  # Explicitly isolated fixture deletion, not user data.
            y.params['outtmpl']['default'] = '%(playlist_title|.)s/%(title)s.%(ext)s'
            info = self.info()
            info['requested_subtitles'] = {'es': {'ext': 'vtt', 'data': 'WEBVTT\n\n'}}
            y.process_info(info)
            expected = self.dest / 'Playlist/Song.webm'
            self.assertTrue(expected.exists())
            self.assertTrue(expected.with_suffix('.es.vtt').exists())
            self.assertFalse(old.exists())
            self.assertEqual(y.state['items'][y.item_key(info)]['path'], 'Playlist/Song.webm')

    def test_failed_repair_keeps_original_and_other_files(self):
        with self.downloader() as y:
            y.process_info(self.info())
            state = json.loads((self.dest / '.yt-sync.json').read_text())
            path = self.dest / state['items'][y.item_key(self.info())]['path']
            path.write_bytes(b'damaged original')
            unrelated = path.parent / 'other.txt'
            unrelated.write_text('keep')
            with patch.object(self.sync.YoutubeDL, 'process_info', side_effect=RuntimeError('offline')):
                with self.assertRaises(RuntimeError):
                    y.process_info(self.info())
            self.assertEqual(path.read_bytes(), b'damaged original')
            self.assertEqual(unrelated.read_text(), 'keep')

    def test_missing_captions_fill_without_media_or_caption_overwrite(self):
        with self.downloader(captions=True) as y:
            info = self.info()
            info['requested_subtitles'] = {
                lang: {'ext': 'vtt', 'data': 'WEBVTT\n\n00:00.000 --> 00:01.000\nHello\n'}
                for lang in ['en', 'es']}
            y.process_info(info)
            media = next((self.dest / 'Playlist').glob('*.webm'))
            english = media.with_suffix('.en.vtt')
            spanish = media.with_suffix('.es.vtt')
            self.assertTrue(english.exists() and spanish.exists())
            keep = media.stat().st_mtime_ns, english.stat().st_mtime_ns
            spanish.unlink()
            info = self.info('New title')
            info['requested_subtitles'] = {
                lang: {'ext': 'vtt', 'data': 'WEBVTT\n\n00:00.000 --> 00:01.000\nHello\n'}
                for lang in ['en', 'es', 'ja']}
            with patch.object(self.sync.YoutubeDL, 'process_info', side_effect=AssertionError('media redownload')):
                y.process_info(info)
            self.assertTrue(spanish.exists())
            self.assertTrue(media.with_suffix('.ja.vtt').exists())
            self.assertEqual((media.stat().st_mtime_ns, english.stat().st_mtime_ns), keep)

    def test_caption_selection_matches_menu_including_original_japanese(self):
        def track(language, translated=False, name=None):
            return [dict(ext='vtt', name=name or language,
                         url='https://www.youtube.com/api/timedtext?lang=' + language
                         + ('&tlang=fr' if translated else '&kind=asr'))]
        published = {lang: track(lang, name='Published ' + lang) for lang in ['en', 'es', 'pt']}
        automatic = {'ja': track('ja', name='Japanese compatibility'),
                     'ja-orig': track('ja', name='Japanese (Original)'),
                     'en': track('en'), 'en-en': track('en'),
                     'es-es': track('es'), 'pt-pt': track('pt'),
                     'fr': track('en', translated=True),
                     'ln-en': track('en', translated=True)}
        with self.downloader(captions=True) as y:
            selected = y.process_subtitles('fixture', published, automatic)
            self.assertEqual(set(selected), {'en', 'es', 'pt', 'ja'})
            self.assertEqual(selected['ja']['name'], 'Japanese (Original)')
            self.assertEqual(selected['en']['name'], 'Published en')
        with self.downloader(captions=False) as y:
            self.assertIsNone(y.process_subtitles('fixture', published, automatic))

    def test_successful_captions_survive429_and_retry_only_fetches_remaining(self):
        with self.downloader(captions=True) as y:
            y.process_info(self.info())
            media = next((self.dest / 'Playlist').glob('*.webm'))
            before = media.read_bytes(), media.stat().st_mtime_ns
            info = self.info()
            info['requested_subtitles'] = {
                lang: {'ext': 'vtt', 'data': 'WEBVTT\n\n00:00.000 --> 00:01.000\nHello\n'}
                for lang in ['en', 'es', 'pt', 'ja']}
            original = y._write_subtitles
            calls = []
            def fail_second(track_info, filename):
                languages = list(track_info['requested_subtitles'])
                calls.extend(languages)
                if 'es' in languages:
                    raise self.sync.DownloadError('HTTP Error 429: Too Many Requests')
                return original(track_info, filename)
            with patch.object(y, '_write_subtitles', side_effect=fail_second):
                with self.assertRaises(self.sync.DownloadError):
                    y.process_info(info)
            self.assertEqual(calls, ['en', 'es'])
            english = media.with_suffix('.en.vtt')
            self.assertTrue(english.exists(), 'Earlier completed caption was lost after later429')
            english_before = english.read_bytes(), english.stat().st_mtime_ns
            calls.clear()
            def record(track_info, filename):
                calls.extend(track_info['requested_subtitles'])
                return original(track_info, filename)
            with patch.object(y, '_write_subtitles', side_effect=record):
                y.process_info(info)
            self.assertEqual(calls, ['es', 'pt', 'ja'])
            self.assertEqual((english.read_bytes(), english.stat().st_mtime_ns), english_before)
            self.assertEqual((media.read_bytes(), media.stat().st_mtime_ns), before)

    def test_legacy_file_is_adopted_and_invalid_manifest_fails_closed(self):
        path = self.dest / 'Playlist' / 'Artist - Song.webm'
        path.parent.mkdir()
        path.write_bytes(self.source.read_bytes())
        with self.downloader() as y, patch.object(self.sync.YoutubeDL, 'process_info', side_effect=AssertionError('legacy redownload')):
            y.process_info(self.info())
        state = self.dest / '.yt-sync.json'
        state.write_text('{bad')
        with self.assertRaises(self.sync.SyncError):
            self.downloader()
        self.assertEqual(path.read_bytes(), self.source.read_bytes())

    def test_audio_captions_are_reconciled_without_downloading_again(self):
        with self.downloader(audio=True, captions=True) as y:
            info = self.info()
            info['requested_subtitles'] = {'es': {'ext': 'vtt', 'data': 'WEBVTT\n\n'}}
            y.process_info(info)
            target = next((self.dest / 'Playlist').glob('*.ogg'))
            subtitle = target.with_suffix('.es.vtt')
            subtitle.write_bytes(b'')
            keep = target.read_bytes()
            with patch.object(self.sync.YoutubeDL, 'process_info', side_effect=AssertionError('audio redownload')):
                y.process_info(info)
            self.assertTrue(subtitle.stat().st_size)
            self.assertEqual(target.read_bytes(), keep)

    def test_symlink_refused_and_constructor_lock_released(self):
        state = self.dest / '.yt-sync.json'
        outside = self.root / 'outside.json'
        outside.write_text('{}')
        state.symlink_to(outside)
        with self.assertRaises(self.sync.SyncError):
            self.downloader()
        state.unlink()
        with self.downloader():
            pass
        self.assertEqual(outside.read_text(), '{}')

    def test_real_helper_cli_uses_local_info_and_then_skips(self):
        source = self.root / 'fixture.info.json'
        source.write_text(json.dumps(self.info()))
        command = ['python3', str(SCRIPT), '--ignore-config', '--enable-file-urls',
                   '--load-info-json', str(source), '--quiet', '--no-warnings',
                   '--progress-template', '__YT_PROGRESS__%(progress._percent_str)s',
                   '-o', '%(playlist_title)s/%(artist)s - %(title)s.%(ext)s']
        env = dict(os.environ, HOME=str(self.root), XDG_CONFIG_HOME=str(self.root),
                   PYTHONDONTWRITEBYTECODE='1')
        first = subprocess.run(command, cwd=self.dest, env=env, text=True, capture_output=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn('__YT_DONE__Playlist/Artist - Song.webm', first.stdout)
        percents = [float(line.split('|')[0].removeprefix('__YT_PROGRESS__').strip('%'))
                    for line in first.stdout.splitlines() if line.startswith('__YT_PROGRESS__')]
        self.assertGreater(len(percents), 1)
        self.assertEqual(percents, sorted(percents))
        self.assertEqual(percents[-1], 100.0)
        self.assertEqual(percents.count(100.0), 1)
        second = subprocess.run(command, cwd=self.dest, env=env, text=True, capture_output=True)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn('Skipped (verified)', second.stdout)
        self.assertNotIn('__YT_DONE__', second.stdout)

    def test_unsafe_manifest_path_and_concurrent_run_are_refused(self):
        with self.downloader() as first:
            with self.assertRaises(self.sync.SyncError):
                self.downloader()
        (self.dest / '.yt-sync.json').write_text(json.dumps({'version': 1, 'items': {
            'Youtube:fixture:video': {'path': '../source.webm', 'sha256': 'a' * 64, 'duration': 2}}}))
        with self.downloader() as y, self.assertRaises(self.sync.SyncError):
            y.process_info(self.info())
        self.assertTrue(self.source.exists())


class BrowserSessionTests(unittest.TestCase):
    def test_main_profile_resolution_uses_metadata_and_refuses_wrong_identity(self):
        sync = load_sync()
        with tempfile.TemporaryDirectory(prefix='yt-profile-test-') as tmp:
            root = Path(tmp)
            (root / 'Default').mkdir()
            state = root / 'Local State'
            state.write_text(json.dumps({'profile': {'info_cache': {'Default': {'name': 'Main'}}}}))
            self.assertEqual(sync.resolve_brave_main_profile(root), str(root / 'Default'))
            state.write_text(json.dumps({'profile': {'info_cache': {'Default': {'name': 'Other'}}}}))
            with self.assertRaises(sync.SyncError):
                sync.resolve_brave_main_profile(root)
            state.write_text(json.dumps({'profile': {'info_cache': {
                'Default': {'name': 'Main'}, 'Profile 1': {'name': 'main'}}}}))
            with self.assertRaises(sync.SyncError):
                sync.resolve_brave_main_profile(root)

    def test_main_profile_rejects_symlink_outside_browser_root(self):
        sync = load_sync()
        with tempfile.TemporaryDirectory(prefix='yt-profile-test-') as tmp:
            root = Path(tmp) / 'browser'
            root.mkdir()
            (root / 'Default').symlink_to(Path(tmp), target_is_directory=True)
            (root / 'Local State').write_text(json.dumps({
                'profile': {'info_cache': {'Default': {'name': 'Main'}}},
            }))
            with self.assertRaises(sync.SyncError):
                sync.resolve_brave_main_profile(root)

    def test_youtube_pins_main_before_client_and_does_not_export_cookies(self):
        sync = load_sync()
        with patch.object(sync, 'resolve_brave_main_profile', return_value='/fixture/Main') as resolver, \
             patch.object(sync, 'SyncYoutubeDL') as client:
            client.return_value.__enter__.return_value.download.return_value = 0
            status = sync.main(['--ignore-config', '--cookies-from-browser', 'brave',
                                'https://youtu.be/LKjvc3p2lgg'])
            self.assertEqual(status, 0)
            resolver.assert_called_once_with()
            opts = client.call_args.args[0]
            self.assertEqual(opts['cookiesfrombrowser'], ('brave', '/fixture/Main', None, None))
            self.assertIsNone(opts.get('cookiefile'))

    def test_cookie_loading_failure_does_not_retry_or_download(self):
        sync = load_sync()
        from yt_dlp.cookies import CookieLoadError
        with patch.object(sync, 'resolve_brave_main_profile', return_value='/fixture/Main'), \
             patch.object(sync, 'restrict_youtube_cookies', side_effect=CookieLoadError('synthetic')), \
             patch.object(sync, 'SyncYoutubeDL') as client:
            self.assertEqual(sync.main(['--ignore-config', 'https://youtu.be/LKjvc3p2lgg']), 1)
            client.assert_called_once()
            client.return_value.__enter__.return_value.download.assert_not_called()

    def test_cookie_jar_is_scoped_to_youtube_domains(self):
        import http.cookiejar
        sync = load_sync()
        jar = http.cookiejar.CookieJar()
        for domain in ['.youtube.com', 'youtu.be', 'r1.googlevideo.com',
                       '.example.invalid', '.google.com', 'youtube.com.evil.invalid']:
            jar.set_cookie(http.cookiejar.Cookie(0, 'fixture', 'synthetic', None, False,
                domain, True, domain.startswith('.'), '/', True, True, None, True,
                None, None, {}, False))
        sync.restrict_youtube_cookies(jar)
        self.assertEqual({cookie.domain for cookie in jar},
                         {'.youtube.com', 'youtu.be', 'r1.googlevideo.com'})

    def test_no_cross_site_cookie_use_or_fallback_if_main_missing(self):
        sync = load_sync()
        with patch.object(sync, 'resolve_brave_main_profile') as resolver, \
             patch.object(sync, 'SyncYoutubeDL') as client:
            client.return_value.__enter__.return_value.download.return_value = 0
            self.assertEqual(sync.main(['--ignore-config', '--cookies-from-browser', 'brave',
                                        'https://example.invalid/video']), 0)
            resolver.assert_not_called()
            self.assertIsNone(client.call_args.args[0].get('cookiesfrombrowser'))
        with patch.object(sync, 'resolve_brave_main_profile', side_effect=sync.SyncError('Main unavailable')), \
             patch.object(sync, 'SyncYoutubeDL') as client:
            self.assertEqual(sync.main(['--ignore-config', 'https://youtu.be/LKjvc3p2lgg']), 1)
            client.assert_not_called()


class ItemProgressTests(unittest.TestCase):
    def progress(self, formats):
        sync = load_sync()
        lines = []
        return sync.ItemProgress({'requested_formats': formats}, 'episode.webm', emit=lines.append), lines

    def event(self, identity, **values):
        return dict(status='downloading', info_dict={'format_id': identity}, speed=1024**2, eta=12, **values)

    def percentages(self, lines):
        return [float(line.split('|', 1)[0].removeprefix('__YT_PROGRESS__').strip('% ')) for line in lines]

    def test_hls_estimates_and_late_fragment_updates_cannot_reverse_progress(self):
        progress, lines = self.progress([{'format_id': '616'}, {'format_id': '251'}])
        progress(self.event('616', fragment_index=10, fragment_count=100,
                            downloaded_bytes=500, total_bytes_estimate=1000))
        progress(self.event('616', fragment_index=12, fragment_count=100,
                            downloaded_bytes=600, total_bytes_estimate=2000))
        progress(self.event('616', fragment_index=11, fragment_count=100,
                            downloaded_bytes=550, total_bytes_estimate=2500))
        values = self.percentages(lines)
        self.assertEqual(values, sorted(values))
        self.assertEqual(values[-1], 6.0)

    def test_video_audio_share_one_item_and_only_verified_completion_reaches100(self):
        progress, lines = self.progress([{'format_id': 'video', 'filesize': 900},
                                         {'format_id': 'audio', 'filesize': 100}])
        progress(self.event('video', downloaded_bytes=900, total_bytes=900))
        progress(dict(self.event('video'), status='finished'))
        progress(self.event('audio', downloaded_bytes=1, total_bytes=100))
        progress(dict(self.event('audio', downloaded_bytes=100, total_bytes=100), status='finished'))
        self.assertEqual(self.percentages(lines), [90.0, 90.0, 90.1, 99.9])
        progress.complete()
        self.assertEqual(self.percentages(lines)[-1], 100.0)
        self.assertTrue(all('episode.webm' in line for line in lines))
        # Late callbacks cannot pull an already verified item back down.
        progress(self.event('audio', downloaded_bytes=1, total_bytes=100))
        self.assertEqual(self.percentages(lines)[-1], 100.0)

    def test_parallel_callbacks_are_emitted_in_monotonic_order(self):
        progress, lines = self.progress([{'format_id': 'video'}, {'format_id': 'audio'}])
        events = [self.event(identity, downloaded_bytes=n, total_bytes=100)
                  for n in range(100) for identity in ['video', 'audio']]
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(progress, events))
        values = self.percentages(lines)
        self.assertEqual(len(values), 200)
        self.assertEqual(values, sorted(values))
        self.assertLess(values[-1], 100)

    def test_byte_estimate_revisions_and_next_item_reset(self):
        progress, lines = self.progress([{'format_id': 'audio'}])
        progress(self.event('audio', downloaded_bytes=50, total_bytes_estimate=100))
        progress(self.event('audio', downloaded_bytes=60, total_bytes_estimate=200))
        self.assertEqual(self.percentages(lines), [50.0, 50.0])
        other, fresh = self.progress([{'format_id': 'audio'}])
        other(self.event('audio', downloaded_bytes=1, total_bytes=100))
        self.assertEqual(self.percentages(fresh), [1.0])


if __name__ == '__main__':
    unittest.main()
