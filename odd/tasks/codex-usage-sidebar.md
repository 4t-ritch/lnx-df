# Codex Usage Sidebar — Feature Document

## Objective
Add a local OpenCode V2 TUI plugin that shows Codex subscription consumption in the right sidebar: monthly remaining, weekly remaining, and cost. Use an independent OpenCode credential (user decision: Token aparte en OpenCode).

## Problem
User cannot see Codex plan consumption inside OpenCode. Gentle-pi already implements this via `https://chatgpt.com/backend-api/wham/usage` with 5-minute cache and window parsing (week / 5h + percent + reset).

## Why
Keep usage visible during OpenCode sessions without switching to pi. Requested placement is between Context and MCP; V2 only supports whole `sidebar.content` / `sidebar.footer`, so closest durable placement is a `sidebar.content` block.

## Scope
- New local V2 file: `config/opencode/tui-plugins/codex-usage.tsx` (+ live copy in `~/.config/opencode/tui-plugins/`)
- Activation cleanup: `config/opencode/cli.json` + `config/opencode/tui.json` (+ live copies). Remove legacy npm `opencode-subagent-statusline` entry that causes `Invalid V2 TUI plugin module`; keep local `subagent-statusline-v2.tsx`.
- Independent credential: env-based reference only (for example `{env:CODEX_USAGE_TOKEN}` or OS store file outside repo). Never commit secrets.
- Fetch + parse mirroring gentle-pi schema (`ProviderUsage` / `UsageLimit` / `UsageWindow`), 5-minute throttle, explicit loading / error / unavailable states.
- UI: 1-2 lines + meter in `sidebar.content`; full reset times deferred to panel or tooltip.

## Constraints
- OpenCode V2 TUI API only: `import { Plugin } from "@opencode/plugin/tui"`, `export default Plugin.define({ id, setup(context) })`, `context.ui.slot`, `context.data`, `context.keymap.layer`, `context.storage`. Do not mix legacy `api.slots.register`.
- No secrets in repo. No `node_modules` edits. Preserve unrelated settings.
- Exact between-Context-and-MCP insertion is unsupported (closed V2 slot list). Do not fake MCP registration.
- Advisory heuristic only: prefer smallest coherent behavior with tests/docs; ~400 lines is planning guidance, not a cap or split trigger.

## Authorized scope
User explicitly authorized a plugin/modification in OpenCode for a Codex token visualizer with monthly remaining, weekly remaining, and cost, placed in the side panel between Context and MCP. Auth decision resolved: independent OpenCode credential. Branch-first work-unit commits on feature branch are authorized; push/PR/merge remain user decisions.

## Acceptance criteria
- Fresh standalone TUI loads with no `Invalid V2 TUI plugin module` for the new plugin.
- Sidebar shows monthly remaining, weekly remaining, and cost, or an explicit unavailable state with reason.
- Uses independent credential only; no pi `auth.json` dependency and no secret in repo.
- Live and canonical configs match for touched files; `git diff --check` passes.
- `opencode api get /api/plugin` remains healthy for server plugins.

## Applicable checks
- `node --check` / `bun build` for new TUI module
- Bounded `opencode --standalone` reconciliation + log grep for `Invalid V2 TUI plugin module`
- `cmp` live vs canonical for touched configs; `git diff --check`
- Structural readback for docs-only changes

## Checklist
- [x] T1 — Scaffold V2 sidebar plugin + config cleanup (route: delegated direct; trigger: writer — plugin file + cli.json/tui.json edits) — DONE in `1fe6625` on `feat/codex-usage-sidebar`. New `config/opencode/tui-plugins/codex-usage.tsx` (V2 `gentle-ai.codex-usage`, `sidebar.content` placeholder); removed legacy npm `opencode-subagent-statusline` from `tui.json`; added `codex-usage.tsx` to `cli.json`. Parent spot-check: `git diff --check` clean, `cmp` canonical vs live OK x3, log grep `Invalid V2 TUI plugin module` = 0.
- [x] T2 — Independent credential + usage fetch/parse/render (route: delegated direct; trigger: preparation + writer — API mapping + new code) — DONE in `70bc236`. Env `CODEX_USAGE_TOKEN` presence only, `wham/usage` 10s fetch, weekly/monthly remaining + cost/plan + reset, 5-min throttle, stale/unavailable states, `sidebar.content`. Parent spot-check: `git diff --check` DIFF-OK, `cmp` CMP-OK, log grep 0.
- [x] T3 — Verify standalone TUI, sync live/canonical, docs (route: delegated direct; trigger: per-action verification worker) — DONE in `c96ab4d`. Docs-only 8-line header, no logic change. Parent spot-check: `git diff --check` DIFF-OK, `cmp` CMP-OK, log grep `Invalid V2 TUI plugin module` = 0, `git status` shows only untracked `odd/tasks/*.md`.

## TDD
- Mode: disabled (ordinary functional checks only)
- Source: `sdd-init/lnx-df` reports `strict_tdd: disabled, no test runner`; no explicit ODD TDD choice
- Runner: none; use syntax/bundle checks + bounded standalone TUI + log grep above

## Delivery
- Strategy: `ask-on-risk` (default)
- Forecast: ~200-300 authored lines (new plugin + config edits), under 400 budget; no slicing planned
- Running count: 0; slice boundaries: none yet

## Progress
- Exploration done via read-only mapper (gentle-pi endpoint, schema, refresh; V2 slot list; statusline v1 vs V2 mismatch).
- Auth decision done: independent OpenCode credential.
- Reads: `config/opencode/cli.json`, `config/opencode/tui.json`, `config/opencode/tui-plugins/` (3 files inline, within bound).
- T1 done in `1fe6625`: skeleton + legacy npm entry removed; parent spot-check passed.
- T2 done in `70bc236`: live wiring with fixture harness 12/12, standalone 0 invalid-module; real-token fetch pending user token.
- T3 done in `c96ab4d`: docs header, final sync verified, no logic change.
- This doc created before first source write; updated after T1, T2, T3. Feature complete pending real-token check.

## Verification evidence
- `config/opencode/cli.json` lists 4 local plugins including `codex-usage.tsx`
- `config/opencode/tui.json` lists same 4 local plugins, no legacy npm entry
- `bun build` 10.41 KB exit 0; `node --check` OK; `git diff --check` clean
- `cmp` canonical vs live OK for all 3 touched files
- Bounded `timeout 15s opencode --standalone` exit 124 (expected kill); log grep `Invalid V2 TUI plugin module` = 0; no `codex-usage` errors
- `opencode api get /api/plugin` healthy (server plugins active; TUI plugin correctly absent there)

## Next step
Set `CODEX_USAGE_TOKEN` in OpenCode env and reopen TUI to confirm live numbers. Push/PR remain user decisions under ordinary repo policy. No further code planned.

## T4 — User reports no Codex block visible (2026-09-20)
- Diagnosis (read-only, `ses_f3ffda8c0ffehyJp5pRufBDpzp`): live vs canonical byte-identical (`codex-usage.tsx` sha `d1c4f1c6…f13f7a`, cli.json/tui.json list all 4 local plugins); branch `feat/codex-usage-sidebar` at `c96ab4d`; `opencode.log` has 0 `codex-usage` / 0 `Invalid V2` lines (TUI slots are silent in this log by design); placeholder path renders without token (null hypothesis refuted, `codex-usage.tsx:199-215`).
- Status: user restarted exact window + `restart` command, still no block. Stale-TUI hypothesis refuted for the restarted window.
- Deep diagnosis (`ses_f3ff7271dffesOsCkHym4iwpHC`): `hostname-badge` `sidebar_footer` also absent from sidebar → general TUI file-plugin loading failure, not codex-specific. `bun build` identical success for codex + sibling; runtime import OK (`id: gentle-ai.codex-usage`, `setup: function`). DEBUG standalone only renders home screen (cannot validate session slot); `opencode.log` confirms only backend `opencode.sidebar.context/mcp/footer`, never local file claims (silent by design).

## T5 — Isolate TUI loader + remove cli.json confounding path (2026-09-20)
- DONE in `210c30c`: `tui.json` listed only `codex-usage.tsx`; `cli.json` `plugins: []`; backups at `/tmp/opencode/tui.json.bak`, `/tmp/opencode/cli.json.bak`. User restarted and still sees nothing → isolation verdict is host-side, not cross-plugin interference.

## T6 — Restore canonical list after isolation verdict (2026-09-20)
- DONE in `3617a6d`: `tui.json` restored to 4 local entries (statusline-v2, logo, badge, codex-usage); `cli.json` keeps `plugins: []`. Parent spot-check DIFF-OK, TUI-OK. Rollback: `git revert 3617a6d`.
- Upstream escalation pack ready (redacted): opencode v2.0.11, 4-entry tui.json, `Plugin.define` + `sidebar.content` slot lines, bun build 10.41 KB OK, import smoke `id: gentle-ai.codex-usage | setup: function`, placeholder-by-code-path yet never renders even in isolation, sibling `sidebar_footer` also absent. Zero genuine `Invalid V2` loader errors (log hits are own command echoes).

## T7 — Delete Codex usage plugin per user request (2026-09-20)
- DONE in `dd6579b`: removed canonical + live `tui-plugins/codex-usage.tsx`, dropped its `tui.json` entry (back to 3 siblings), left `cli.json` `plugins: []`. Parent spot-check DIFF-OK, TUI-OK, LIVE-GONE. Rollback: `git revert dd6579b`.

## Verification evidence
- `config/opencode/cli.json` lists local `subagent-statusline-v2.tsx` + logo + badge (no npm statusline)
- `config/opencode/tui.json` still lists npm `opencode-subagent-statusline` (mismatch to fix in T1)
- `config/opencode/tui-plugins/` contains `gentle-logo.tsx`, `hostname-badge.tsx`, `subagent-statusline-v2.tsx`
- Explorer: `CODEX_USAGE_URL = https://chatgpt.com/backend-api/wham/usage`; `UsageStore` in-memory, 5-min throttle

## Next step
Delegate T1 writer with closed scope: create `codex-usage.tsx` skeleton + remove npm v1 entry from `tui.json` + ensure `cli.json`/`tui.json` consistency. No credential wiring in T1 beyond env placeholder.

## Rationale
Independent credential isolates OpenCode from pi login lifecycle at the cost of manual token maintenance. `sidebar.content` is the only inline sidebar option; order relative to Context/MCP is host-controlled. Cleaning the legacy npm entry fixes the persistent invalid-module error separately from the new feature.
## Locator
- Repo-relative: `odd/tasks/codex-usage-sidebar.md`
- Engram mirror topic: `odd/codex-usage-sidebar/tasks` (project: dotfiles; pending if save fails)
