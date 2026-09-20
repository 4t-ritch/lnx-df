# Migrar a OpenCode v2, eliminar v1

## Objective
Quedarse solo con OpenCode v2 y eliminar v1 de la máquina.

## Problem / why
Pedido explícito del usuario: ya instaló v2, quiere migrarse y no tener más v1.

## Scope
- v1: `/home/linuxbrew/.linuxbrew/bin/opencode` (brew `anomalyco/tap`, 1.18.31,
  hoy gana el `opencode` pelado por orden de PATH)
- v2: shims pnpm `opencode` + `opencode2` (2.0.8), hoy `opencode2` es la vía
  directa
- Estado compartido (NO TOCAR): `~/.local/share/opencode/`
  (`auth.json`, `account.json`, `opencode.db ~803MB`) — nunca correr
  `opencode uninstall` de ninguna versión
- Alias `opc` (fish) sigue funcionando solo

## Out of scope (no tocar)
- `~/.local/share/opencode/` completo
- Reconciliar drift live (`~/.config/opencode`) vs dotfiles
  (`~/dotfiles/config/opencode`): solo flaggear, no redeployar
- `~/.opencode/` override, plugins v1-era (solo verificar compat o reportar)

## Constraints
- Backup de `~/.config/opencode/` antes de cualquier cambio.
- Verificar v2 ANTES de desinstalar v1 (versión, auth, resolución PATH).
- Desinstalar v1 solo con `brew uninstall opencode` (+ `brew untap`
  únicamente si el tap queda sin otras fórmulas).
- Tras el borrado, `opencode` pelado pasa a ser v2: verificarlo explícito.

## Authorized scope
Smoke-test no-interactivo de v2 + `brew uninstall` de v1 + verificación PATH.
Autorizado en este hilo.

## Acceptance criteria
- [ ] Backup existe y verificable
- [ ] `opencode2 --version` → 2.x, `auth list` muestra las cuentas
- [ ] `brew uninstall opencode` OK; `which -a opencode` resuelve a pnpm v2;
      `opencode --version` → 2.x
- [ ] `~/.local/share/opencode/` intacto (auth + db presentes)

## Applicable checks
Comandos con output observado. TDD: OFF (sysadmin, sin runner).
No interactivo: nada que pida login o TUI.

## Delivery
Cambio único, sin commits (no hay repo involucrado salvo flag de drift).
Sin PR.

## Tasks
- [x] T1 — Backup live config + checks v2 (versión, auth list, which).
      Route: delegated-direct (múltiples comandos con estado + riesgo).
      DONE 2026-09-19: backup /tmp/opencode-config-backup-20260919-152347 (149M, exit 0);
      `which -a opencode` → /home/linuxbrew/.linuxbrew/bin/opencode + /home/ritch/.local/share/pnpm/bin/opencode;
      `opencode --version` → 1.18.31; `opencode2 --version` → opencode v2.0.8;
      `opencode2 auth list` → OpenCode Go API key stored, OpenAI OAuth stored, OpenRouter API key stored (exit 0, sin login).
- [x] T2 — `brew uninstall opencode` (+ untap condicional) + verificación
      PATH/versión/estado compartido. Mismo writer.
      DONE 2026-09-19: `brew uninstall opencode` exit 0 (Cellar/opencode/1.18.31, 4 files 185MB;
      autoremove ripgrep 15.2.0 + pcre2 10.48 — reportado como side-effect);
      tap anomalyco/tap NO untappeado (tap-info sigue listando opencode, opencode-v2, sst, torpedo + cask hex);
      `which -a opencode` → solo /home/ritch/.local/share/pnpm/bin/opencode;
      `opencode --version` → opencode v2.0.8; `opencode2 --version` → opencode v2.0.8 (igual T1);
      `ls ~/.local/share/opencode/auth.json` (2.4K) + `opencode.db` (768M) presentes.
      No se tocó ~/.local/share/opencode/, ~/.config/opencode/, ~/dotfiles/config/opencode/, ~/.opencode/, fish.

## Progress
- 2026-09-19: doc creado tras mapeo delegado (general). Pendiente: writer.

## Next step
Lanzar single writer con T1–T2.
