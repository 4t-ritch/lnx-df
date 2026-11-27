# Claude Code status line

`statusline.py` renders the Claude Code status line:

```
 feat/vis-port |  ritch/dotfiles (main) |  Opus (low) | 5h ▰▰▱▱▱▱▱▱▱▱ 24% | 7d ▰▰▰▰▱▱▱▱▱▱ 41%
```

Segments:

- Git branch of the current directory.
- Repository root tail (last two path components) and the linked worktree name, or `main`.
- Model display name with the reasoning effort in parentheses when the model reports one, e.g. `Opus (low)`.
- 5-hour and 7-day rate-limit usage bars.

## Theme

`themes/ritch-rose.json` is a Claude Code custom theme. The installer links it
to `~/.claude/themes/ritch-rose.json`; Claude discovers themes in that directory
by file stem. Select it with `/theme` or:

```json
"theme": "custom:ritch-rose"
```

It replicates the Codex `ritch-rose` palette so both CLIs look the same:

| Element | Color |
| --- | --- |
| background | `#151316` |
| text | `#C9C0C5` |
| rose accent | `#D185AB` |
| branch cyan | `#8FB0B6` |
| path blue | `#93A9C4` |
| subtle gray | `#6F636B` |


## Wiring

The installer links `~/.claude/statusline.py` to this file. Claude Code reads
the command from `~/.claude/settings.json`, which stays machine-local because
it also holds hooks and permissions. Add this block there:

```json
"statusLine": {
  "command": "~/.claude/statusline.py",
  "refreshInterval": 60,
  "type": "command"
}
```

## Usage cache

Claude Code only sends `rate_limits` after the first API response and drops a
window once `resets_at` passes. Every observed snapshot is persisted to
`${XDG_CACHE_HOME:-~/.cache}/claude-statusline/usage.json` and reused when the
current payload has no fresh value. Inside one reset window usage is
cumulative, so a lower percentage from a concurrent session never overwrites a
newer cached value.

## Customization

- Icons: `GIT_ICON`, `TREE_ICON`, `STAR_ICON` constants at the top.
- Colors: `PINK`, `CYAN` and `BLUE` match the `ritch-rose` theme accents.
- Bar width and glyphs: `BAR_WIDTH`, `BAR_FILLED`, `BAR_EMPTY`.

The branch label matches the Fish prompt: `>` for commits ahead of upstream,
`<` for commits behind, and `!` for local changes, including untracked files.
Indicators combine in that order (for example, `main ><!`).
