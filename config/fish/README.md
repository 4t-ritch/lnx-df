# Download with `yt`

`yt` shows the current filename beside its progress bar and keeps a `Downloaded:`
line with the final path after conversion or merging completes. Live updates fit
the terminal width: long names are shortened only on screen, and narrow panes
show the name and percentage. The completed path remains unabridged.

```fish
yt -a 'PLAYLIST_URL'       # Audio: Vorbis (also the default)
yt -v 'PLAYLIST_URL'       # Video and audio
yt -v -cc 'PLAYLIST_URL'       # Spanish source captions (default for -cc)
yt -v -cc all 'PLAYLIST_URL'   # All source subtitle tracks
yt -v -cc en,ja 'VIDEO_URL'    # English and Japanese source tracks
yt --help
```

Playlists save their content inside a directory named after their YouTube title,
relative to the current directory. Individual videos stay in the current directory.
New audio and video files use `Title.ext` without an author prefix. Metadata
is still embedded independently of the filename.
Subtitle filenames follow their media's base name. yt-dlp sanitizes unsafe
characters in playlist and file names. Previously indexed downloads keep their
recorded names rather than being renamed or duplicated. If an indexed file was
deleted, a new download uses the current title-only template instead of its stale
recorded name. Reload the Fish function after configuration changes.

`-cc` (or `--captions`) selects Spanish by default. Use `-cc es`, `-cc en`,
`-cc en,ja`, or `-cc all` to choose languages; `-cc=all` and `--captions=all`
also work. A base language includes its regional source variants (e.g. `es-419`).
If a requested language is unavailable, no translated replacement is generated.
Without `-cc`, subtitles remain disabled.

Eligible tracks are the source tracks shown in YouTube's subtitle menu:
creator-published tracks plus original-language automatic captions. For example,
Japanese marked "auto-generated" is retained when it is the original ASR track;
translations generated into other languages are excluded. Original aliases such
as `ja` and `ja-orig` produce one track, and a published track takes priority over
an automatic track in the same language. Live chat is excluded.

Without this flag, subtitles are not downloaded. It also works in audio mode.
Subtitles remain separate language-tagged files, not burned into the video.
In VLC, use **Subtitle → Add Subtitle File** to select a track.

Actual subtitle requests are spaced by five seconds. Each completed caption is
saved immediately, so a later failure (including HTTP 429) does not discard the
previous successes. If YouTube still rate-limits requests, wait before rerunning
the same command: it will skip healthy media and already saved captions. Existing
extra subtitle files from older runs are not deleted automatically.

Live progress represents one media item across its video/audio streams, rather
than resetting for each stream. Known stream sizes provide byte weights; otherwise
streams have equal weights, so this is an estimate. Completed fragment counts are
preferred over changing HLS size estimates. Displayed progress never decreases,
the bar length does not change with speed/ETA text, and 100% is reserved for the
verified, committed media file (before separate subtitle reconciliation).
The permanent `Downloaded:` line is the final postprocessed media path.
Unavailable playlist entries are skipped by yt-dlp's default behavior; errors are
shown and the command can still return a nonzero status after downloading the rest.

## Brave session

HTTPS YouTube requests use the **Main** profile of the configured Brave Flatpak
from the first request. The profile directory is resolved from `Local State`
under `~/.var/app/com.brave.Browser/config/BraveSoftware/Brave-Browser`; the current
Main directory is `Default`. Missing, ambiguous, or unsafe profile metadata stops
the command instead of selecting another profile or retrying anonymously.

Cookies are loaded directly by yt-dlp, never exported to a cookie file. Only
YouTube/YouTu.be/Googlevideo-domain cookies remain in the request cookie jar;
unrelated sites' session cookies are removed in memory. Non-YouTube commands and
local info-file tests do not load browser cookies. The browser database is not
modified. An OS keyring may need to be unlocked for Chromium cookie decryption.
The native Brave installation's similarly named profile is not used.

Using a signed-in session does not guarantee that YouTube will never rate-limit
or challenge a request. The command no longer retries the same error through an
unspecified browser profile.

## Weekly synchronization

Run the same command from the same download directory. The hidden `.yt-sync.json`
index links each source ID and mode (audio/video) to its verified final file, so a
renamed YouTube title does not create another copy. Keep this index with the files.
The `.yt-sync.lock` file prevents two `yt` runs in that directory at once.

Every run hashes existing media with SHA-256. New files and legacy downloads are
also decoded with FFmpeg, preserving video timestamps and the demuxer timebase
so variable-frame-rate output is not rejected by validation-only rounding. Checks
still reject decode/truncation errors and compare each stream's decoded duration
against YouTube's duration. Later runs reuse that validation only if the hash and
source duration still match. A changed hash triggers a replacement, even after an
intentional local edit. Duration checks allow small encoder/timestamp differences
(0.25–2 seconds, depending on length); this is not a source-provided checksum or a
guarantee against every conceivable defect. Live/unknown-duration content cannot
be verified and is reported as an error rather than silently accepted.

Repairs download into a temporary directory on the same filesystem. Only a
verified replacement replaces the damaged file; a failed download keeps the old
file and reports an error. Unrelated files and symlink targets are not removed.
Legacy files are recognized by embedded YouTube URL metadata; an unreadable file
with the exact expected name can also be repaired. Readable unidentified name
collisions use a source-ID suffix instead of overwriting another file.

With `-cc`, the available subtitle tracks are checked on every run, even when media
is skipped. Only missing or empty selected source sidecars are downloaded; existing nonempty tracks and
healthy media are left unchanged. A newly available language is picked up next run.
Subtitle errors can therefore be retried without downloading the media again.
This does not delete local content removed from the online playlist, or schedule
weekly execution automatically.

## Offline checks

Requires Fish, Python, FFmpeg/ffprobe, and the installed `yt_dlp` Python module:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s config/fish/tests -p 'test_*.py'
fish -n config/fish/functions/yt.fish
```

Tests use local media fixtures and mocked Fish routing. They do not contact YouTube,
read browser cookies, or modify real downloads.

### Optional user-local yt-dlp bundle

If present, `~/.local/share/yt/yt-dlp.pyz` takes precedence for `yt` only.
Move the bundle aside to return to the system Python package.
