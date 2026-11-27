#!/usr/bin/env python3
"""ID-aware, integrity-checked local reconciliation for the Fish yt command."""
import contextlib
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from urllib.parse import parse_qs, urlparse

from yt_dlp import YoutubeDL, parse_options
from yt_dlp.cookies import CookieLoadError
from yt_dlp.utils import DownloadError, subtitles_filename

MEDIA = {'.webm', '.mkv', '.mp4', '.m4a', '.ogg', '.opus', '.mp3', '.flac', '.wav', '.mov'}


class SyncError(DownloadError):
    """An unsafe or unverifiable reconciliation operation."""


def resolve_brave_main_profile(root=None):
    """Resolve the authorized Flatpak Main profile, never a browser default guess."""
    root = Path(root) if root is not None else (
        Path.home() / '.var/app/com.brave.Browser/config/BraveSoftware/Brave-Browser')
    try:
        state = json.loads((root / 'Local State').read_text())
        matches = [name for name, entry in state['profile']['info_cache'].items()
                   if str(entry.get('name', '')).casefold() == 'main']
        if len(matches) != 1:
            raise ValueError('expected exactly one profile named Main')
        directory = Path(matches[0])
        if directory.is_absolute() or len(directory.parts) != 1 or directory.name in {'.', '..'}:
            raise ValueError('unsafe profile directory')
        profile = (root / directory).resolve()
        if not profile.is_relative_to(root.resolve()) or not profile.is_dir():
            raise ValueError('Main profile directory is missing or outside the browser root')
        return str(profile)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as err:
        raise SyncError(f'Cannot resolve Brave Flatpak profile Main: {err}; no other profile will be used.') from err


def youtube_cookie_domain(domain):
    host = domain.lstrip('.').lower()
    return any(host == base or host.endswith('.' + base)
               for base in ('youtube.com', 'youtu.be', 'googlevideo.com'))


def restrict_youtube_cookies(jar):
    # Browser extraction stays in memory; unrelated site's sessions must not be
    # forwarded when a command contains another site's URL or a redirect.
    for cookie in list(jar):
        if not youtube_cookie_domain(cookie.domain):
            jar.clear(cookie.domain, cookie.path, cookie.name)


class ItemProgress:
    """Monotonic progress across an item's video/audio streams and fragments."""

    def __init__(self, info, filename, emit=None):
        formats = info.get('requested_formats') or [info]
        self.parts = {str(f.get('format_id', index)): 0.0 for index, f in enumerate(formats)}
        sizes = [finite_duration(f.get('filesize') or f.get('filesize_approx')) for f in formats]
        self.weights = dict(zip(self.parts, sizes if all(sizes) else [1.0] * len(formats)))
        self.filename = str(filename)
        self.emit = emit or (lambda line: print(line, flush=True))
        self.percent = 0.0
        self.finished = False
        self.lock = threading.Lock()

    def __call__(self, data):
        if data.get('status') not in {'downloading', 'finished'}:
            return
        with self.lock:
            if self.finished:
                return
            key = str(data.get('info_dict', {}).get('format_id', ''))
            if key in self.parts:
                keys = [key]
            elif len(self.parts) == 1 or key == '+'.join(self.parts):
                keys = list(self.parts)
            else:
                return
            if data['status'] == 'finished':
                fraction = 1.0
            elif data.get('fragment_count') and data.get('fragment_index') is not None:
                fraction = data['fragment_index'] / data['fragment_count']
            else:
                total = data.get('total_bytes') or data.get('total_bytes_estimate') or 0
                fraction = (data.get('downloaded_bytes') or 0) / total if total else 0.0
            for part in keys:
                self.parts[part] = max(self.parts[part], min(1.0, fraction))
            estimate = 100 * sum(self.parts[k] * self.weights[k] for k in self.parts) / sum(self.weights.values())
            # A transfer finishing is not the same as a verified, committed file.
            self.percent = max(self.percent, min(99.9, estimate))
            speed = finite_duration(data.get('speed'))
            speed_text = f'{speed / 1024**2:.2f}MiB/s' if speed else 'NA'
            eta = data.get('eta')
            eta_text = f'{int(eta) // 60:02d}:{int(eta) % 60:02d}' if isinstance(eta, (int, float)) and math.isfinite(eta) and eta >= 0 else 'NA'
            self.emit(f'__YT_PROGRESS__{self.percent:.1f}%|{speed_text}|{eta_text}|{self.filename}')

    def complete(self):
        with self.lock:
            self.finished = True
            self.percent = 100.0
            self.emit(f'__YT_PROGRESS__100.0%|NA|NA|{self.filename}')


def probe(path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_format', '-show_streams',
                             '-of', 'json', str(path)], capture_output=True, text=True)
    if result.returncode:
        raise ValueError('unreadable media')
    return json.loads(result.stdout)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def source_id(url):
    parsed = urlparse(str(url))
    if parsed.hostname in {'youtu.be', 'www.youtu.be'}:
        return parsed.path.strip('/')
    if parsed.hostname in {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com'}:
        return parse_qs(parsed.query).get('v', [None])[0] or parsed.path.rsplit('/', 1)[-1]
    return None


def media_streams(metadata):
    return [s for s in metadata.get('streams', [])
            if s.get('codec_type') in {'audio', 'video'}
            and not s.get('disposition', {}).get('attached_pic')]


def finite_duration(value):
    try:
        number = float(value)
        return number if math.isfinite(number) and number > 0 else None
    except (TypeError, ValueError):
        return None


def validate(path, info, audio, previous=None, diagnostics=None):
    """Hash every run; fully decode changed/new files and compare each stream's end."""
    def reject(reason):
        if diagnostics is not None:
            diagnostics.append(reason)
        return None

    try:
        if not path.is_file() or not path.stat().st_size:
            return reject('missing or empty media file')
        metadata = probe(path)
        streams = media_streams(metadata)
        kinds = {s['codec_type'] for s in streams}
        required = {'audio'} if audio else {'video'}
        if not audio and info.get('acodec') != 'none':
            required.add('audio')
        if not required <= kinds or (audio and 'video' in kinds):
            return reject('required audio/video streams are missing')
        checksum = digest(path)
        if previous and checksum != previous.get('sha256'):
            return reject('file checksum has changed')
        expected = finite_duration(info.get('duration'))
        if expected is None or info.get('is_live'):
            raise SyncError('Cannot verify completeness without a finite source duration (live content is not supported).')
        tolerance = max(0.25, min(2.0, expected * 0.005))
        if (previous and checksum == previous.get('sha256')
                and finite_duration(previous.get('duration')) is not None
                and abs(previous['duration'] - expected) <= tolerance):
            return dict(sha256=checksum, duration=expected)
        for stream in streams:
            # Default 1/framerate can round valid VFR timestamps to equal DTS.
            # Preserve the input timebase rather than ignoring muxer diagnostics.
            timing = ['-fps_mode', 'passthrough', '-enc_time_base', 'demux'] if stream['codec_type'] == 'video' else []
            decoded = subprocess.run([
                'ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-err_detect', 'explode',
                '-i', str(path), '-map', f"0:{stream['index']}",
                *timing, '-progress', 'pipe:1', '-f', 'null', '-'], capture_output=True, text=True)
            times = re.findall(r'^out_time_us=(\d+)$', decoded.stdout, re.MULTILINE)
            if decoded.returncode or decoded.stderr.strip() or not times:
                detail = ' '.join(decoded.stderr.split())[:240] or 'no decoded duration reported'
                return reject(f"{stream['codec_type']} stream {stream['index']}: {detail} (exit {decoded.returncode})")
            duration = int(times[-1]) / 1_000_000
            if abs(duration - expected) > tolerance:
                return reject(f"{stream['codec_type']} duration {duration:.3f}s differs from expected {expected:.3f}s")
        return dict(sha256=checksum, duration=expected)
    except (OSError, ValueError, KeyError, TypeError) as err:
        return reject(f'cannot read or inspect media: {err}')


class SyncYoutubeDL(YoutubeDL):
    def __init__(self, params, *, root=None, audio=False):
        params = dict(params)
        self.live_progress = '__YT_PROGRESS__' in params.get('progress_template', {}).get('download', '')
        self.current_progress = None
        if self.live_progress:
            params['noprogress'] = True
        self.root = Path(root or Path.cwd()).resolve()
        self.audio = audio
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = None
        try:
            fd = os.open(self.root / '.yt-sync.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            self.lock = os.fdopen(fd, 'w')
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.state_path = self.checked_path('.yt-sync.json')
            self.state = {'version': 1, 'items': {}}
            if self.state_path.exists():
                self.state = json.loads(self.state_path.read_text())
                if self.state.get('version') != 1 or not isinstance(self.state.get('items'), dict):
                    raise ValueError('invalid state schema')
                for entry in self.state['items'].values():
                    if (not isinstance(entry, dict) or not isinstance(entry.get('path'), str)
                            or not re.fullmatch(r'[0-9a-f]{64}', str(entry.get('sha256', '')))
                            or finite_duration(entry.get('duration')) is None):
                        raise ValueError('invalid sync item schema')
            super().__init__(params)
            if self.live_progress:
                self.add_progress_hook(self.emit_progress)
        except (OSError, ValueError, TypeError, AttributeError, SyncError, CookieLoadError) as err:
            if self.lock:
                self.lock.close()
            if isinstance(err, CookieLoadError):
                raise
            raise SyncError(f'Cannot open sync state or another yt sync is running: {err}') from err

    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.lock.close()

    def emit_progress(self, data):
        if self.current_progress is not None:
            self.current_progress(data)

    def process_subtitles(self, video_id, normal_subtitles, automatic_captions):
        # Original ASR captions belong in the source-track menu; translations do
        # not. yt-dlp can expose the original twice (e.g. ja and ja-orig).
        originals = {}
        for language, formats in (automatic_captions or {}).items():
            base = language.removesuffix('-orig')
            source_formats = [fmt for fmt in formats if 'tlang' not in parse_qs(
                urlparse(fmt.get('url') or '').query, keep_blank_values=True)]
            if source_formats:
                source_query = parse_qs(urlparse(source_formats[0].get('url') or '').query)
                base = source_query.get('lang', [base])[0] or base
            # Same-language translation aliases (en-en, es-es, ...) may have
            # no tlang at all; their source language already has a real track.
            if base in (normal_subtitles or {}):
                continue
            if source_formats and (base not in originals or language.endswith('-orig')):
                originals[base] = source_formats
        return super().process_subtitles(video_id, normal_subtitles, originals)

    def checked_path(self, relative):
        path = self.root / relative
        if not isinstance(relative, str) or Path(relative).is_absolute():
            raise SyncError('Sync paths must be relative to the download directory.')
        try:
            path.resolve().relative_to(self.root)
        except ValueError as err:
            raise SyncError('Sync path leaves the download directory.') from err
        for part in [path, *path.parents]:
            if part == self.root:
                break
            if part.is_symlink():
                raise SyncError(f'Refusing symlink in download path: {path}')
        return path

    def item_key(self, info):
        return f"{info.get('extractor_key', 'Youtube')}:{info['id']}:{'audio' if self.audio else 'video'}"

    def save(self, key, path, health):
        self.state['items'][key] = dict(path=str(path.relative_to(self.root)), **health)
        with tempfile.NamedTemporaryFile(mode='w', dir=self.root, prefix='.yt-sync-', delete=False) as stream:
            temporary = Path(stream.name)
            try:
                json.dump(self.state, stream)
                stream.flush()
                os.fsync(stream.fileno())
                os.replace(temporary, self.state_path)
            finally:
                temporary.unlink(missing_ok=True)

    @contextlib.contextmanager
    def output_to(self, path, **options):
        original = self.params.copy()
        # Escape literal percent signs before appending the one template field.
        template = str(path.with_suffix('')).replace('%', '%%') + '.%(ext)s'
        self.params.update(outtmpl={'default': template}, paths={}, **options)
        try:
            yield
        finally:
            self.params.clear()
            self.params.update(original)

    def locate(self, info):
        key = self.item_key(info)
        previous = self.state['items'].get(key)
        if previous is not None:
            if not isinstance(previous, dict) or not isinstance(previous.get('path'), str):
                raise SyncError('Invalid sync item; refusing to modify any files.')
            path = self.checked_path(previous['path'])
            if path.suffix.lower() not in MEDIA:
                raise SyncError('Sync item is not a supported media path.')
            if self.audio or path.exists():
                return path, previous
            # A deleted video must not pin a new download to an obsolete name.
        predicted = Path(self.prepare_filename(info))
        if predicted.is_absolute():
            try:
                predicted = predicted.relative_to(self.root)
            except ValueError as err:
                raise SyncError('Output must be inside the download directory.') from err
        path = self.checked_path(str(predicted))
        if self.audio:
            path = path.with_suffix('.ogg')
        # Adopt old downloads by embedded source URL, even after a title change.
        candidates = sorted(path.parent.iterdir()) if path.parent.is_dir() else []
        unreadable = []
        reserved = {item['path'] for item_key, item in self.state['items'].items() if item_key != key}
        for candidate in candidates:
            if candidate.suffix.lower() not in MEDIA or candidate.is_symlink() or not candidate.is_file():
                continue
            try:
                metadata = probe(candidate)
            except (ValueError, OSError):
                if (candidate.stem == path.stem
                        and (not self.audio or candidate.suffix == '.ogg')
                        and str(candidate.relative_to(self.root)) not in reserved):
                    unreadable.append(candidate)
                continue
            kinds = {s['codec_type'] for s in media_streams(metadata)}
            if ('video' in kinds) == self.audio:
                continue
            tags = dict(metadata.get('format', {}).get('tags', {}))
            for stream in metadata.get('streams', []):
                tags.update(stream.get('tags', {}))
            urls = [value for name, value in tags.items() if name.lower() in {'purl', 'comment'}]
            if any(source_id(url) == info['id'] for url in urls):
                return candidate, None
        if len(unreadable) == 1:
            return unreadable[0], None
        # Exact old filenames with unreadable bytes are the only unindexed repair candidates.
        if path.exists():
            try:
                metadata = probe(path)
            except (ValueError, OSError):
                if str(path.relative_to(self.root)) not in reserved:
                    return path, None
            # Do not overwrite a readable unrelated file that happens to share the title.
            path = path.with_name(f"{path.stem} [{info['id']}]{path.suffix}")
            if path.exists():
                raise SyncError(f'Unidentified file already occupies the output path: {path}')
        return path, None

    def sync_captions(self, info, target):
        if not (self.params.get('writesubtitles') or self.params.get('writeautomaticsub')):
            return
        missing = {}
        final = dict(info, ext=target.suffix[1:])
        for language, track in (info.get('requested_subtitles') or {}).items():
            if (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', language)
                    or not re.fullmatch(r'[A-Za-z0-9]+', track['ext'])):
                raise SyncError('Unsafe subtitle language or extension.')
            name = subtitles_filename(str(target), language, track['ext'], final['ext'])
            path = self.checked_path(str(Path(name).relative_to(self.root)))
            if not path.is_file() or not path.stat().st_size:
                missing[language] = dict(track)
        if not missing:
            return
        for language, track in missing.items():
            final['requested_subtitles'] = {language: track}
            with tempfile.TemporaryDirectory(prefix='.yt-captions-', dir=target.parent) as tmp:
                stage = Path(tmp) / target.name
                with self.output_to(stage, overwrites=False):
                    written = self._write_subtitles(final, str(stage))
                if written is None:
                    raise SyncError(f'Subtitle download incomplete for {target.name}; rerun with -cc.')
                for downloaded, _ in written:
                    downloaded = Path(downloaded)
                    if not downloaded.is_file() or not downloaded.stat().st_size:
                        raise SyncError(f'Empty subtitle: {downloaded.name}')
                    dest = self.checked_path(str((target.parent / downloaded.name).relative_to(self.root)))
                    os.replace(downloaded, dest)
                    print(f'__YT_SYNC__Captions: {dest.relative_to(self.root)}', flush=True)

    def process_info(self, info):
        target, previous = self.locate(info)
        key = self.item_key(info)
        print(f'__YT_SYNC__Checking: {target.relative_to(self.root)}', flush=True)
        health = validate(target, info, self.audio, previous)
        if health:
            self.save(key, target, health)
            print(f'__YT_SYNC__Skipped (verified): {target.relative_to(self.root)}', flush=True)
            self.sync_captions(info, target)
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        subtitles = info.get('requested_subtitles')
        progress = ItemProgress(info, target.name) if self.live_progress else None
        with tempfile.TemporaryDirectory(prefix='.yt-download-', dir=target.parent) as tmp:
            stage = Path(tmp) / target.name
            # Reconcile sidecars separately, after the media has been verified and committed.
            self.current_progress = progress
            try:
                with self.output_to(stage, writesubtitles=False, writeautomaticsub=False, forceprint={}):
                    super().process_info(info)
            finally:
                self.current_progress = None
            final = Path(info.get('filepath') or stage)
            if not final.resolve().is_relative_to(Path(tmp).resolve()):
                raise SyncError('Downloader returned a file outside the staging directory.')
            if not final.is_file() or not info.get('__write_download_archive'):
                raise SyncError(f'Download or postprocessing incomplete: {target.name}')
            diagnostics = []
            health = validate(final, info, self.audio, diagnostics=diagnostics)
            if not health:
                reason = diagnostics[-1] if diagnostics else 'unknown validation failure'
                kept = 'existing file kept' if target.exists() else 'no final file was saved'
                raise SyncError(f'Download failed integrity verification: {target.name}: {reason}; {kept}.')
            destination = target.with_suffix(final.suffix)
            destination = self.checked_path(str(destination.relative_to(self.root)))
            if destination != target and destination.exists():
                raise SyncError(f'Refusing to overwrite another file: {destination}')
            os.replace(final, destination)
            if destination != target and target.exists():
                target.unlink()
            self.save(key, destination, health)
        info['requested_subtitles'] = subtitles
        info['filepath'] = str(destination)
        if progress:
            progress.filename = destination.name
            progress.complete()
        print(f'__YT_DONE__{destination.relative_to(self.root)}', flush=True)
        self.sync_captions(info, destination)


def main(argv=None):
    parsed = parse_options(argv)
    # Archive-only skips would bypass integrity and newly available captions.
    parsed.ydl_opts['download_archive'] = None
    # Never export browser cookies, even if a global yt-dlp config requests it.
    parsed.ydl_opts['cookiefile'] = None
    for command in ['ffmpeg', 'ffprobe']:
        if not shutil.which(command):
            print(f'ERROR: {command} is required for verified synchronization.', file=sys.stderr)
            return 1
    try:
        use_main = any(urlparse(url).scheme == 'https'
                       and (urlparse(url).hostname or '').lower().removeprefix('www.')
                       in {'youtube.com', 'm.youtube.com', 'music.youtube.com', 'youtu.be'}
                       for url in parsed.urls)
        parsed.ydl_opts['cookiesfrombrowser'] = (
            ('brave', resolve_brave_main_profile(), None, None) if use_main else None)
        audio = any(pp.get('key') == 'FFmpegExtractAudio' for pp in parsed.ydl_opts.get('postprocessors', []))
        with SyncYoutubeDL(parsed.ydl_opts, audio=audio) as ydl:
            if use_main:
                restrict_youtube_cookies(ydl.cookiejar)
            if parsed.options.load_info_filename:
                return ydl.download_with_info_file(parsed.options.load_info_filename)
            return ydl.download(parsed.urls)
    except CookieLoadError:
        print('ERROR: Cannot load Brave Main cookies. Check the profile and OS keyring; no other profile or anonymous retry was used.', file=sys.stderr)
        return 1
    except (DownloadError, OSError) as err:
        print(f'ERROR: {err}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
