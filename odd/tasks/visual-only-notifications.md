# Visual-only notifications — sin guardado ni sección en el centro

## Objective
Que las notificaciones sean solo visuales: nada se guarda en lista/HUD y la sección
Notifications del centro de comandos deja de existir en ningún lado.

## Problem / why
Pedido explícito del usuario: Super+Backspace debe generar solo la notificación
visual; la función que guarda notificaciones debe borrarse de la config; la sección
Notifications del centro de comandos debe eliminarse por completo.

## Scope (archivos)
Fuente: `/home/ritch/dotfiles/config/` — deployado: `/home/ritch/.config/`
(archivos regulares, NO symlinks: todo cambio va en fuente + deployado).
- `hypr/scripts/clipboard-clear.sh` (binding Super+Backspace en `hypr/hyprland.lua:496`)
- `swaync/config.json` (bloque `scripts.lnx-control-center-history`, líneas ~51-56)
- `control-center/log-swaync-notification` (SAVE FUNCTION a borrar)
- `control-center/control_center/app.py` (`notifications_card()` ~1249-1459,
  llamada en main ~367, refresh `1475/1503/1521`, estado `63-65`)
- `control-center/control_center/services/notifications.py` (borrado completo)
- `control-center/control_center/config.py:10` (constante `NOTIFICATION_HISTORY`)
- `control-center/control_center/ui/molecules/notifications.py`
  (`hover_reveal_action_row`, solo usado por notificaciones)
- `control-center/style.css` (bloque notificaciones ~123-130 y ~203-330)

## Out of scope (no tocar)
- `waybar` custom/notification (lee swaync directo, independiente, se conserva)
- Centro nativo de swaync (`swaync-client -t` desde waybar) e historial de
  `sessions/`/`logs/` (historial, no lista viva)
- `config/dunst/dunstrc` (huérfano, dunst inactivo), `swaync/style.css` salvo que
  el writer confirme bloque muerto inequívoco
- Archivos dirty preexistentes en worktree (`codex`, `fish`, `gtk-3.0`, `hypr/data`,
  `kitty`, `opencode`, `tmux`): no tocar, no commitear

## Constraints
- Quitar el hook Y el bloque `scripts` de swaync en la misma unidad de cambio
  (`script-fail-notify: true` generaría popups de error si queda el bloque solo).
- Limpiar imports huérfanos en `app.py` y referencias en refresh/apply_status.
- DND: el toggle campana vive dentro de la sección y se elimina con ella.
  Control DND restante: click derecho en waybar (`swaync-client -d`). Reportarlo
  al cierre por si el usuario quiere reubicarlo.
- Cache `~/.cache/lnx-df-control-center/notifications.jsonl`: truncar (es cache).

## Authorized scope
Borrado de la función de guardado + sección Notifications + Super+Backspace
solo-visual. Autorizado por el usuario en este hilo. Push/PR: decisión del usuario.

## Acceptance criteria
- [ ] Super+Backspace muestra popup y NO agrega nada a `notifications.jsonl`
- [ ] `rg -i notification` en `control-center/` sin restos de sección/servicio/CSS
      (salvo menciones en comentarios intencionales, justificadas)
- [ ] `python3 -m py_compile` pasa en `control_center/app.py`
- [ ] Recarga de swaync + `lnx-control-center --daemon` sin errores; prueba viva
      Super+Backspace y Super+N

## Applicable checks
`rg` residual, `py_compile`, reload servicios, prueba viva de ambos shortcuts.
TDD: OFF (sin test runner en repo de desktop-config; functional checks en su lugar).
Deliberado: repo sin framework de tests; no inventar runner.

## Delivery
Forecast: muy por debajo de 400 líneas (+/-, mayoría borrado). Estrategia:
cambio único directo, work-unit commits en feature branch. Sin PR salvo pedido.

## Tasks
- [x] T1 — `clipboard-clear.sh` solo-visual (hint transient o `hyprctl notify`;
      verificar que no dispare el hook). Route: delegated-direct (evidencia: 8+
      archivos tocados en el cambio total; single writer para todo).
      Done 2026-09-19: `hyprctl notify` puro. Empírico: `notify-send` normal →
      hook dispara (jsonl +227B); `notify-send -e` transient → hook IGUAL dispara
      (+254B, hint guardado); `hyprctl notify` → jsonl 0B + `ok`. Script vivo con
      hook aún instalado: exit=0, jsonl 0 líneas.
- [x] T2 — Borrar guardado: eliminar `log-swaync-notification` + bloque `scripts`
      en `swaync/config.json`; truncar cache jsonl. Mismo writer, mismo commit o
      commit propio por tarea.
      Done 2026-09-19: hook borrado + bloque `scripts` removido (mismo commit,
      JSON revalidado); cache truncado a 0B. Post-cambio: `notify-send` normal →
      jsonl 0B/0 líneas; `swaync-client --reload-config` exit=0, swaync vivo.
- [ ] T3 — Borrar sección del centro: card + métodos + llamada + servicio +
      constante + helper + CSS + imports. Mismo writer.
- [ ] T4 — Verificación completa (acceptance) y reporte de evidencia. Mismo writer.

## Progress
- 2026-09-19: doc creado tras exploración delegada (general). Pendiente: writer.
- 2026-09-19: T1 done — `d8f5fcd feat(hypr): visual-only clipboard-clear notification via hyprctl`.
- 2026-09-19: T2 done — commit pendiente (hook + scripts atómicos, ver abajo).
- Commits: (recorder identities aquí)

## Next step
Lanzar single writer con T1–T4.
