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
- [x] `rg -i "media|player_status|cached_art|MEDIA_HEIGHT|art_provider"` en
      `control-center/` solo devuelve lo intencional (`.media-button` reusado
      o cero si se migró; `app.get("media")` de audio-detail renombrado o
      justificado)
  Verificado: solo `app.get("media")` (clave PipeWire `media.name`, origen
  audio.py:195/208-209) + `.media-button` (mute per-app, regla conservada).
  Cero `player_status/cached_art/MEDIA_HEIGHT/art_provider`.
- [x] Sin referencias a `playerctl`/`swayosd` en `control-center/`
  Verificado con rg: cero.
- [x] `py_compile` OK, `git diff --check` limpio, daemon reiniciado sin
      Traceback/Error, probado sin reproductor y con reproductor corriendo
  `py_compile: OK`, `diff-check: limpio`, daemon PID único 1507958 con código
  final, log sin Traceback/Error (solo warnings preexistentes radv +
  GtkImage-baselines, sin tocar). Con reproductor (`playerctl -l` →
  `brave.instance2` con video): toggle muestra panel con tiles vivos, hide
  limpio, screenshots cc-600/cc-285/cc-final. Sin reproductor: partial
  honesto — no se mató el browser del usuario; cobertura por construcción
  (ninguna rama restante consulta reproductores; rg prueba cero
  playerctl/swayosd).
- [x] Los 4 pins de altura sincronizados al mismo valor final (documentado)
  Valor final 285: config.py `PANEL_HEIGHT=285` + hyprland.lua
  `size={420,285}` + 3 pins app.py por constantes (set_default_size:91,
  place_window:271, set_size_request:283). `hyprctl reload: ok`.

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
- [x] T2 — CSS (bloque música menos `.media-button` o migración del uso en
      :892) + `PANEL_HEIGHT` + verificación pins sincronizados. Mismo writer.
  Outcome: style.css sin `.media-card/.media-content/.media-title/
  media-subtitle/.media-time/.media-controls`; `.media-button` CONSERVADA con
  comentario (reusada por mute per-app audio-detail app.py:875); pins
  sincronizados en 285 (config.py PANEL_HEIGHT + hyprland.lua size={420,285};
  los 3 de app.py usan las constantes, sin tocar). DESVÍO del candidato 600:
  screenshot runtime a 600 mostró gap vacío de 334px (contenido termina y=337,
  panel cerraba y=671); a 285 el panel cierra y=357 con padding inferior 19px,
  sin gap ni clip. Detail pages usan ScrolledWindow (auto-adapta).
- [x] T3 — Verificación acceptance completa y reporte evidencia. Mismo writer.
  Outcome: todo acceptance verificado salvo sin-reproductor en partial
  honesto (ver Acceptance). Cache `~/.cache/lnx-df-control-center/artwork`
  (109MB, writer exclusivo era `cached_art_path`) eliminada.

## Progress
- 2026-09-19: doc creado tras mapeo delegado (general). Pendiente: writer.
- 2026-09-19: T1 done — writer directo (sin subagentes).
- 2026-09-19: T2 done — writer directo (sin subagentes).
- 2026-09-19: T3 done — writer directo (sin subagentes).
- Commits: 73562a1 feat(control-center): remove music controller chain (T1);
  c35b579 feat(control-center): drop music CSS and shrink panel to 285 (T2);
  (T3: este doc, commit abajo)

## Next step
Lanzar single writer con T1–T3 en rama nueva desde el tip actual.
