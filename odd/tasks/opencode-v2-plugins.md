# Migrar plugins OpenCode a formato V2

## Objective
Que todos los plugins de `~/.config/opencode` carguen sin error bajo OpenCode v2.

## Problem / why
Tras migrar a v2 (2.0.10), los 9 plugins fallan. Dos causas (log
`~/.local/share/opencode/log/opencode.log` 21:55):
1. `Cannot find package '@opencode/plugin'`: 5 plugins `.ts` importan el
   paquete V2 pero `node_modules` solo tiene `@opencode-ai/plugin` (v1).
2. `Missing key "default"`: `engram.ts`, `gentle-agent-state.js` y
   `herdr-agent-state.js` usan formato v1 (sin default export con id);
   v2 exige `export default` con definición (`Plugin.define`, ver
   `telemetry-runtime.ts` como referencia ya migrada en el mismo repo).
3. TUI: `opencode-subagent-statusline@^1.3.0` (paquete v1-era) también falla.

## Scope
- `~/.config/opencode/plugins/`: `engram.ts`, `gentle-agent-state.js`,
  `herdr-agent-state.js`, `model-variants.ts`, `opencode-review-transport.ts`,
  `sdd-task-result-artifacts.ts`, `skill-registry.ts` (telemetry-runtime.ts ya
  está en formato v2, no tocar salvo imports)
- `~/.config/opencode/package.json` (+ `package-lock.json`): agregar
  `@opencode/plugin` v2 acorde al CLI (2.0.10); quitar `@opencode-ai/plugin`
  solo si nada lo sigue importando
- `~/.config/opencode/tui.json`: statusline (upgrade a versión v2-compatible
  si existe; si no existe, NO borrar silencioso: dejar y reportar blocked)

## Out of scope (no tocar)
- `~/.local/share/opencode/` (estado/sesiones), `opencode.json`,
  `~/dotfiles/config/opencode/` (drift ya flaggeado, no reconciliar aquí),
  skills/agents/commands/prompts
- Headers `gentle-ai:managed`: conservarlos; son archivos gestionados

## Constraints
- Backup `cp -a ~/.config/opencode /tmp/...` antes de editar.
- No interactivo: nada de TUI colgada; usar `timeout` en todo probe.
- Referencia de formato v2: `telemetry-runtime.ts` + tipos del paquete
  `@opencode/plugin` instalado + docs oficiales si hace falta.
- No国有企业 romper lo que anda: `telemetry-runtime.ts` y `tui-plugins/*.tsx`
  que hoy cargan, intactos.

## Authorized scope
Migrar los 9 plugins al formato/paquetes V2 + verificación de carga.
Autorizado en este hilo.

## Acceptance criteria
- [ ] `~/.config/opencode/log` o server boot sin `failed to load plugin`
      (grep en `~/.local/share/opencode/log/opencode.log` tras recarga)
- [ ] Los 8 server plugins aparecen cargados; TUI statusline ok o blocked
      reportado con motivo
- [ ] `git diff --check` n/a (no es repo); backup existe

## Applicable checks
Recarga de server + grep de log, `tsc`-level smoke si es barato (no instalar
toolchains nuevas). TDD: OFF.

## Delivery
Sin commits (config viva, no repo). Sin PR.

## Tasks
- [ ] T1 — Instalar `@opencode/plugin` v2 + migrar los 5 `.ts` con import
      roto al formato default-export (plantilla: telemetry-runtime.ts).
      Route: delegated-direct (8 archivos + deps; single writer).
- [ ] T2 — Migrar `engram.ts`, `gentle-agent-state.js`, `herdr-agent-state.js`
      al formato v2 + resolver TUI statusline (upgrade o blocked reportado).
      Mismo writer.
- [ ] T3 — Verificación: reboot server, grep `failed to load plugin` = 0,
      reporte comando:resultado. Mismo writer.

## Progress
- 2026-09-19: doc creado tras diagnóstico (log + lectura directa). Pendiente.

## Next step
Lanzar single writer con T1–T3 (backup primero).
