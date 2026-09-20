# Feature: pi-remove-local-qwen-routing

## Objective
Remove all local Qwen/llamacpp references from Pi config files so Pi uses gentle-pi routing only.

## Problem
`pi` via gentle-ai still dials local Qwen because `~/.pi/gentle-ai/models.json` pins `orchestrator` to `llamacpp-local/qwen3.5-4b`, plus leftover provider, profile env, and wrapper cases. Plain `pi` defaults to `openai-codex/gpt-5.6-sol` and does not read `opencode.json`.

## Why
User explicitly authorized: no local models in Pi files, use gentle-pi routing. Prior partial cleanup (#3707) removed 9b profile but left 4b chain.

## Scope
Authorized scope (Pi files only, read + edit):
- `/home/ritch/.pi/gentle-ai/models.json`
- `/home/ritch/.pi/gentle-ai/profiles.json` (read-only reference, fix only if it points to local)
- `/home/ritch/.pi/agent/models.json`
- `/home/ritch/.pi/agent/profiles/gentle-ai-full-qwen4b.env`
- `/home/ritch/.pi/agent/profiles/README.md` + `gentle-ai-local-yolo.md` if they document local
- `/home/ritch/.local/bin/pi-gentle-qwen` + `pi-gentle-qwen-stop` (remove local cases only)
- `/home/ritch/.pi/settings.json`, `/home/ritch/.pi/agent/settings.json` (verify, do not force rewrite by pi-agent)

Out of scope: `dotfiles/config/opencode/opencode.json` llamacpp block (not read by pi, leave untouched), weight dirs under `/home/ritch/dev/models_ai/` (destructive, needs separate confirmation), `sessions/logs` history, remote OpenRouter `qwen` catalog entries.

## Constraints
- READ-ONLY first: backup edited files (timestamped `.bak`) before edit.
- JSON must stay valid after each edit.
- Do not delete weights without explicit confirmation.
- Do not rewrite files outside authorized scope.
- Preserve other providers/models in `agent/models.json` if present; if only local exists, leave empty `providers: {}` valid JSON.

## Tasks
- [x] T1 [delegated] Repoint orchestrator routing: `~/.pi/gentle-ai/models.json` `orchestrator.model` from `llamacpp-local/qwen3.5-4b` to routed `openai-codex/gpt-5.6-sol` (match `gpt` profile in `profiles.json`). Verify JSON.
- [x] T2 [delegated] Remove local provider: `~/.pi/agent/models.json` remove `llamacpp-local` block. Verify JSON, preserve other providers.
- [x] T3 [delegated] Remove local profile + wrapper: delete or neuter `gentle-ai-full-qwen4b.env` (prefer delete + note), update `profiles/README.md` + `gentle-ai-local-yolo.md` docs, remove `qwen9b/qwen4b` cases in `pi-gentle-qwen` to fallback to gentle-pi routing. Verify no executable offers local.
- [x] T4 [delegated] Verify no local refs: grep `qwen|llamacpp|127.0.0.1:8080|127.0.0.1:18080|qwen3.5-4b|qwen3.5-9b` in `~/.pi/**/*.json`, `~/.pi/agent/profiles/*`, `~/.local/bin/pi-gentle*` (exclude sessions/logs history). Functional check: `pi --help` + gentle-ai models dump. Record evidence.
- Route: delegated direct (writer trigger: 2+ non-trivial files, 4-file mapping already done). No SDD.
- TDD: off / N/A for config — ordinary functional checks only. Source: no test runner configured for Pi JSON configs.
- Delivery strategy: `ask-on-risk` (default), forecast <50 lines, no PR slice needed. Files live outside dotfiles repo (`~/.pi`, `~/.local/bin`), so no branch/commit expected unless dotfiles symlinks involved — record actual commit identities or `n/a (home configs unversioned)`.

## Acceptance
- `~/.pi/gentle-ai/models.json` orchestrator = routed model, no `llamacpp-local`.
- `~/.pi/agent/models.json` has no `llamacpp-local`, valid JSON.
- No `qwen/llamacpp/127.0.0.1` refs in Pi configs + wrappers (history excluded).
- `pi` resolves via gentle-pi routing.

## Applicable checks
- `python3 -m json.tool` on edited JSONs
- `grep -R` for leftover local refs
- `pi --help` (or `pi --version` if help hangs)

## Progress
- 2026-09-20: doc created, 4 tasks, awaiting writer.
- 2026-09-20: writer success (ses_f42d85777ffeXRrCOfIuTYewV9). T1-T4 done. Parent spot-check OK: MODELS_OK, AGENT_OK, live refs CLEAN (only .bak hits), orchestrator=openai-codex/gpt-5.6-sol. RDD off (global), no review candidate. Git n/a (home configs unversioned). Engram mirror pending (ambiguous sessions).

## Verification evidence
- Writer: json.tool OK x3, targeted grep CLEAN, bash -n OK x2, pi --help exit 0, orchestrator dump + providers {}.
- Parent: MODELS_OK, AGENT_OK, grep only .bak (`gentle-ai-full-qwen4b.env.20260919-2252.bak:2-7`), orchestrator `{'model': 'openai-codex/gpt-5.6-sol'}`. Profiles dir shows .env deleted (only .bak left).
- Commit: n/a (home configs unversioned, outside dotfiles repo).

## Next step
- Done. Optional soak: delete .bak files after verification period; weights `~/dev/models_ai/` left intact per scope. No further code action.
