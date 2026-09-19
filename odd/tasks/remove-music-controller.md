# Remove music controller — solo visual restante

## Objective
Borrar por completo el controlador de música del centro de comandos y reajustar
la altura del contenedor para que no sobre espacio vacío.

## Problem / why
Pedido explícito del usuario: no necesita más el controlador de música; quiere
fuera todo lo que lo relaciona, y la ventana más baja acorde a lo que quede.

## Scope (archivos, líneas sobre HEAD actual con notifications ya removido)
- `control-center/control_center/services/media.py` (borrado entero, 75 líneas)
- `control-center/control_center/app.py`:
  import servicio (:26), import `MEDIA_HEIGHT` (:8-10), estado (:52-62,66),
  `art_provider` + registro (:58,99), timer 1s (:116), `media_card()` (:1178-1222),
  `on_media_action` (:1224-1229), `on_media_seek` (:1231-1238),
  `refresh_async` legs (:1240-1255), `tick_media_progress` (:1261-1269),
  `update_media_progress` (:1271-1279), `apply_status` bloque media (:1281-1301),
  `set_media_art` (:1303-1321), `page.append(self.media_card())` (:358)
- `control-center/control_center/config.py`: `MEDIA_HEIGHT` (:15),
  `ALLOWED/DENIED_PLAYER_HINTS` (:22-31), `ART_CACHE` (:9, si nadie más lo usa)
- `control-center/style.css`: bloque música :148-192
- Altura (4 pins, cambiar JUNTOS): `config.py:14 PANEL_HEIGHT`,
  `app.py:106 set_default_size`, `app.py:287 place_window resize`,
  `app.py:299 set_size_request`, `hypr/hyprland.lua:735 size={420,760}`
  (los 3 de app.py usan las constantes: solo cambia config.py + hyprland.lua)
- Cache: `~/.cache/lnx-df-control-center/artwork` (solo si se verifica
  música-exclusivo; regenerable)

## Out of scope (no tocar)
- `slider_row("output")` volumen (:1112-1138), tiles, resto del centro
- `playerctl` / `swayosd-client` instalados y sus usos: hypr media keys
  (:638-646), `config/solaar/osd.sh` — siguen
- waybar launcher (`on-click: lnx-control-center`), `infra/commands.py`
- Rama hermana `feat/visual-only-notifications` (esta rama parte de su tip;
  stacked a propósito para no pelear líneas)
- 8 dirtys preexistentes ajenos (codex/fish/gtk/hypr-data/kitty/opencode/tmux)

## Constraints
- Borrar la cadena COMPLETA o crashea: import, estado, timer, worker legs,
  unpack en `apply_status`, art provider. Nada a medias.
- Trampa CSS compartido: `.media-button` lo reusa el mute por-app del detalle
  de audio (`app.py:892`) — conservar la regla o migrar ese uso a otra clase,
  nunca borrado blanket del bloque `.media-*`.
- Altura: candidato `PANEL_HEIGHT 600` (760−160: card 150 + spacing ~10);
  verificar en runtime y ajustar ±20px; `on_stage_clicked` usa
  `panel.get_height()` (auto-adapta, no tocar).
- `format_time` (utils.py:30-32) queda sin uso: borrar import/uso o la función
  si de verdad nadie más la usa; `snap_volume` se conserva.

## Authorized scope
Borrado total del controlador de música + reajuste de altura. Autorizado en
este hilo. Push/PR: decisión del usuario.

## Acceptance criteria
- [ ] `rg -i "media|player_status|cached_art|MEDIA_HEIGHT|art_provider"` en
      `control-center/` solo devuelve lo intencional (`.media-button` reusado
      o cero si se migró; `app.get("media")` de audio-detail renombrado o
      justificado)
- [ ] Sin referencias a `playerctl`/`swayosd` en `control-center/`
- [ ] `py_compile` OK, `git diff --check` limpio, daemon reiniciado sin
      Traceback/Error, probado sin reproductor y con reproductor corriendo
- [ ] Los 4 pins de altura sincronizados al mismo valor final (documentado)

## Applicable checks
`rg` residual, `py_compile`, `diff --check`, reload daemon + log, prueba viva.
TDD: OFF (sin runner; functional checks). No inventar comandos.

## Delivery
Forecast <400 líneas (mayoría borrado). Rama nueva stacked sobre el tip actual.
Sin PR salvo pedido.

## Tasks
- [x] T1 — Borrar cadena música: servicio, app.py (import/estado/timer/card/
      actions/worker/apply/art/call), config.py (MEDIA_HEIGHT/hints/ART_CACHE),
      hypr pin de altura. Route: delegated-direct (8+ archivos; single writer).
  Outcome: cadena py eliminada (services/media.py borrado; app.py sin
  import/estado/timer/card/actions/seek/worker-legs/tick/update/apply-block/
  art/call; config.py sin MEDIA_HEIGHT/hints/ART_CACHE verificado sin otro
  importador; utils.py sin format_time, snap_volume conservado; Path import
  removido por quedar sin uso). `py_compile: OK`, `diff --check: clean`.
  Residuales py: cero. Pendiente CSS + altura en T2.
- [ ] T2 — CSS (bloque música menos `.media-button` o migración del uso en
      :892) + `PANEL_HEIGHT` + verificación pins sincronizados. Mismo writer.
- [ ] T3 — Verificación acceptance completa y reporte evidencia. Mismo writer.

## Progress
- 2026-09-19: doc creado tras mapeo delegado (general). Pendiente: writer.
- Commits: (anotar aquí)

## Next step
Lanzar single writer con T1–T3 en rama nueva desde el tip actual.
