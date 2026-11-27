function yt --description 'yt-dlp downloader with progress and audio/video modes'
  set -l yt_helper (path dirname (path dirname (path resolve (status filename))))/scripts/yt-sync.py
  # Accept optional language values without consuming the following URL.
  set -l parse_options 1
  set -l normalized
  set -l language_pattern '^(all|[a-z]{2,3}([-_][a-z0-9]+)*(,[a-z]{2,3}([-_][a-z0-9]+)*)*)$'
  while test (count $argv) -gt 0
    set -l arg "$argv[1]"
    set -e argv[1]
    if test "$arg" = '--'
      set parse_options 0
    else if test $parse_options -eq 1
      if contains -- "$arg" '-cc' '--captions'
        set -l language es
        if test (count $argv) -gt 0; and string match -qir -- $language_pattern "$argv[1]"
          set language "$argv[1]"
          set -e argv[1]
        end
        set arg "--captions=$language"
      else if string match -qr '^-cc=' -- "$arg"
        set arg (string replace -r -- '^-cc=' '--captions=' "$arg")
      end
    end
    set -a normalized "$arg"
  end
  argparse 'a/audio' 'v/video' 'captions=' 'h/help' -- $normalized
  or return

  if set -q _flag_help
    printf '%s\n' \
      'Usage: yt [-a|--audio|-v|--video] [-cc [LANGS]|--captions[=LANGS]] URL ...' \
      'Audio (Vorbis) is the default. File names use only the media title.' \
      'File names: Artist - Title for audio; Title only for video.' \
      '-cc, --captions: save published and original automatic captions, excluding automatic translations and live chat.' \
      'Caption languages: Spanish (es) by default; use -cc all or -cc en,ja to choose.' \
      'Playlists use a folder named after their title.' \
      'Without -cc, subtitles are not downloaded. Completed items show their final path.'
    printf '%s\n' 'Existing media is verified and skipped; damaged media is replaced only after a verified download.' \
      'With -cc, missing subtitle tracks are filled without downloading healthy media again.'
    return 0
  end

  if test (count $argv) -eq 0
    printf '%s\n' 'Error: Specify at least one URL.' >&2
    return 1
  end

  if set -q _flag_audio; and set -q _flag_video
    printf '%s\n' 'Error: Use only one mode: -a for audio or -v for video.' >&2
    return 1
  end

  set -l caption_languages
  if set -q _flag_captions
    set -l requested (string lower -- "$_flag_captions")
    if not string match -qr -- $language_pattern "$requested"
      printf '%s\n' 'Error: Use language codes such as es, en, ja, en,ja or all with -cc.' >&2
      return 1
    end
    if test "$requested" = all
      set caption_languages 'all,-live_chat'
    else
      set -l patterns
      for language in (string split ',' -- "$requested")
        set -a patterns "(?i:$language(?:[-_].*)?)"
      end
      set caption_languages (string join ',' -- $patterns)',-live_chat'
    end
  end

  function __yt_render_progress --argument-names line
    set -l payload (string replace -r '^__YT_PROGRESS__' '' -- $line)
    set -l parts (string split -m 3 '|' -- $payload)
    set -l percent_raw (string trim -- $parts[1])
    set -l speed_raw (string trim -- $parts[2])
    set -l eta_raw (string trim -- $parts[3])
    set -l filename (path basename -- "$parts[4]")
    set filename (string replace -ar '[\x00-\x1f\x7f]' ' ' -- "$filename")

    if test -z "$eta_raw" -o "$eta_raw" = "NA"
      set eta_raw '--:--'
    end

    set -l percent_num (string replace -r '%$' '' -- $percent_raw | string trim)

    if test -z "$percent_num"
      return
    end

    # CR plus erase-in-line resets one physical row, so never wrap or reach
    # the final column (which can enable delayed terminal auto-wrap).
    set -l columns $COLUMNS
    if not string match -qr '^[1-9][0-9]*$' -- "$columns"
      set columns 80
    end
    set -l available (math "max(1, $columns - 1)")
    set speed_raw (string shorten --max 11 -- "$speed_raw")
    set eta_raw (string shorten --max 8 -- "$eta_raw")
    set -l stats (printf ' %6s • %11s • ETA %8s' "$percent_raw" "$speed_raw" "$eta_raw")
    set -l stats_width (string length --visible -- "$stats")
    set -l width (math "min(24, max(4, floor($available / 4)))")
    set -l name_width (math "$available - $stats_width - $width - 3")

    if test $name_width -lt 8
      # Narrow panes prioritize the filename and percentage over decoration.
      set name_width (math "max(1, $available - "(string length --visible -- "$percent_raw")" - 1)")
      set -l label (string shorten --max $name_width -- "$filename")
      set -l compact (string shorten --max $available -- "$label $percent_raw")
      printf '\r\e[2K%s' "$compact"
      return
    end

    set filename (string shorten --max $name_width -- "$filename")
    set -l filled (math "round(($percent_num / 100) * $width)")

    if test $filled -lt 0
      set filled 0
    else if test $filled -gt $width
      set filled $width
    end

    set -l empty (math "$width - $filled")
    set -l bar (string join '' -- (string repeat -n $filled '█') (string repeat -n $empty '░'))

    set -l rendered (printf '%s [%s]%s' "$filename" "$bar" "$stats")
    printf '\r\e[2K%s' (string shorten --max $available -- "$rendered")
  end

  function __yt_run_with_custom_progress
    set -l helper $argv[1]
    set -e argv[1]
    set -l bundle "$HOME/.local/share/yt/yt-dlp.pyz"
    set -l python_env
    if test -f "$bundle"
      set python_env "PYTHONPATH="(string join : -- "$bundle" $PYTHONPATH)
    end
    env $python_env python3 "$helper" --cookies-from-browser brave --quiet --no-warnings --progress --newline \
      --progress-template "__YT_PROGRESS__%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s|%(progress.filename)s" \
      --print 'after_move:__YT_DONE__%(filepath)s' \
      $argv 2>&1 | while read -l line
        if string match -qr '^__YT_PROGRESS__' -- $line
          __yt_render_progress $line
        else if string match -qr '^__YT_DONE__' -- $line
          set -l filepath (string replace -r '^__YT_DONE__' '' -- "$line")
          printf '\r\e[2KDownloaded: %s\n' "$filepath"
        else if string match -qr '^__YT_SYNC__' -- $line
          printf '\r\e[2K%s\n' (string replace -r '^__YT_SYNC__' '' -- "$line")
        else if string match -qr '^(ERROR:|WARNING:|ERROR |WARNING )' -- $line
          printf '\n%s\n' "$line" >&2
        end

      end

    return $pipestatus[1]
  end

  set -l yt_args
  if set -q _flag_video
    set yt_args \
      -f "bestvideo*+bestaudio/best" \
      --embed-metadata \
      -o "%(playlist_title|.)s/%(title)s.%(ext)s" \
      $argv
  else
    set yt_args \
      -f "bestaudio/best" -x \
      --audio-format vorbis \
      --audio-quality 0 \
      --embed-thumbnail \
      --convert-thumbnails jpg \
      --embed-metadata \
      -o "%(playlist_title|.)s/%(title)s.%(ext)s" \
      $argv
  end

  if set -q _flag_captions
    set yt_args --write-subs --write-auto-subs --sub-langs "$caption_languages" --sleep-subtitles 5 $yt_args
  else
    set yt_args --no-write-subs --no-write-auto-subs $yt_args
  end

  __yt_run_with_custom_progress "$yt_helper" $yt_args
  set -l yt_status $status
  functions -e __yt_render_progress __yt_run_with_custom_progress

  if test $yt_status -ne 0
    return $yt_status
  end

  printf '\n'
end
