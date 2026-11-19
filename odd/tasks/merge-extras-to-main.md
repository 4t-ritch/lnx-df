# Feature: merge-extras-to-main

## Objective
Integrar las ramas extra locales a `main`, borrar las ramas extra y pushear si hace falta.

## Problem / Why
Hay 2 ramas locales por delante de `main` (`feat/visual-only-notifications`, `feat/remove-music-controller`) que tienen que quedar consolidadas en `main`.

## Scope
- Ramas: `feat/visual-only-notifications` (7 commits), `feat/remove-music-controller` (12 commits, incluye a la anterior como ancestro)
- Base de ambas: `8411ae1` (= tip actual de `main`, sin divergencia)
- Remoto: `origin` = `git@github.com:4tRitch/lnx-df.git`, `main` en sync con `origin/main`

## Constraints
- Autorizado: merge a `main`, borrado de ramas extra, push a `origin` solo si hace falta.
- Push, PR y merge quedan bajo decisión del usuario según policy ordinaria; acá el usuario ya lo autorizó.
- No crear artefactos SDD; ruta orgánica.

## Authorized scope
- `git merge` de las 2 ramas extra hacia `main`
- `git branch -d` de las ramas extra
- `git push` a `origin` solo si `main` queda por delante

## Acceptance criteria
- [ ] `main` contiene los commits de ambas ramas extra
- [ ] `git branch` ya no lista ramas extra
- [ ] `git status -sb` limpio (salvo untracked `.codegraph/` preexistente)
- [ ] `origin/main` actualizado si hizo falta push

## TDD
- Modo: off (fuente: repo dotfiles sin runner de tests detectable)
- Checks ordinarios: `git status`, `git log`, `git diff --stat`, verificación de sync con remote

## Delivery
- Forecast: ~2968 líneas autoradas acumuladas (1516 ins + 1452 del en diff `main..feat/remove-music-controller`), merge sin trabajo nuevo.
- Estrategia: directa a `main` (autorizada), sin PR slicing.
- Heurística 400 líneas/task: solo advisory, no bloquea este merge.

## Route
- Por tarea: inline (operaciones `git` de estado, permitidas inline)
- Evidencia de triggers: merge sin lectura de 4+ ficheros ni edición de 2+ ficheros no-triviales; si aparece conflicto, se delega según trigger de preparación.

## Tasks
- [x] T1 Merge `feat/visual-only-notifications` a `main`
  - Checks: `git log main` contiene `f22a56b`, `git status` limpio
- [x] T2 Merge `feat/remove-music-controller` a `main`
  - Checks: `git log main` contiene `e301de0`, diff vacío contra la rama
- [x] T3 Limpieza y sync
  - `git branch -d` de ambas ramas extra, `git push` si `main` va por delante
  - Checks: `git branch` solo `main`, `git status -sb` en sync

## Progress
- 2026-09-20: creado documento, base verificada (`8411ae1`), `visual` es ancestro de `remove` (YES).

## Verification evidence
- `git merge-base --is-ancestor f22a56b main` => YES, `e301de0` => YES
- `git branch --merged main` listaba ambas antes del borrado
- `git branch -d` borró ambas; `git branch` final solo `main`
- `git push origin main`: `8411ae1..e301de0 main -> main`, luego `## main...origin/main` en sync
- T2 requirió mover `.codegraph/.gitignore` untracked (idéntico al de la rama, backup en `/tmp/opencode/merge-backup/`); tras el merge el `.gitignore` quedó trackeado y los db ignorados.

## Next step
- Listo. Doc de seguimiento en `odd/tasks/merge-extras-to-main.md` (untracked, no pusheado).
