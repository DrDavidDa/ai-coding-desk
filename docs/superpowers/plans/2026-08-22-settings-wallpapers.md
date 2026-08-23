# Settings + Six Wallpapers — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `PAGE_SETTINGS` with six selectable static wallpapers persisted in NVS, reachable from DESK (long-press 发送) and USAGE (swipe past last page).

**Architecture:** Batch-generate six 240×240 RGB565 blobs; expose `kWallImgs[6]` to LVGL; `attach_wave(scr, veil, id)` on all pages; new settings UI writes `DeskConfig` + dedicated `wall_id` NVS key. Phase 2 (Host installer) is a separate plan.

**Tech Stack:** ESP32-S3, LVGL 8.3, PlatformIO `waveshare_lcd_154`, Python/Pillow asset tool, existing `#CFG*` serial protocol.

**Spec:** `docs/superpowers/specs/2026-08-22-desk154-settings-wallpapers-design.md`

---

## File map

| File | Responsibility |
|------|----------------|
| `docs/assets/wall-{wave,ember,ink,phosphor,night,stone}-240.png` | Source art |
| `firmware/tools/png_to_wave.py` | Batch PNG → rgb565 |
| `firmware/extra_script.py` | incbin all six blobs |
| `firmware/src/wave_img.{h,c,S}` | LVGL descriptors array |
| `firmware/src/config.{h,cpp}` | `wall_id`, `idle_sec` |
| `firmware/src/ui.{h,cpp}` | `PAGE_SETTINGS`, nav, settings paint |
| `firmware/src/serial_cmd.cpp` | optional `#CFGLINE\|wall_id=` |
| `docs/desk154-settings-preview.html` | Update thumbs when PNGs exist |
| `docs/keys.md` | Settings entry + wallpaper note |

---

## Task 1: Author six wallpaper PNGs

- [x] Copy existing `docs/assets/wave-bg-240.png` → `wall-wave-240.png` (or keep alias in tool)
- [x] Create five new 240×240 PNGs (Ember, 宣纸, 磷光, 夜空, 石面) — distinct palettes per spec
- [x] Drop into `docs/assets/` with stable names
- [x] Update `docs/desk154-settings-preview.html` to use real PNG backgrounds where available

**Verify:** Open preview at `http://127.0.0.1:8765/desk154-settings-preview.html`

---

## Task 2: Batch asset pipeline

- [x] Extend `png_to_wave.py` to accept `--all` or list of inputs → `src/assets/wave/{name}.rgb565`
- [x] Update `extra_script.py` to emit six incbin symbols (or one concatenated blob + offsets table)
- [x] Rewrite `wave_img.c` / `wave_img.h`:
  - `extern const lv_img_dsc_t kWallImgs[WALL_COUNT];`
  - `WALL_COUNT = 6`
  - Helper `const lv_img_dsc_t *wall_img_get(uint8_t id)`
- [x] Keep backward `#define wave_bg_img kWallImgs[0]` if needed for minimal diff

**Verify:** `pio run -e waveshare_lcd_154` links; flash size delta ~+575 KB vs single wall

---

## Task 3: Config / NVS

- [x] Add to `DeskConfig`: `uint8_t wall_id = 0;`, `uint16_t idle_sec = 180;`
- [x] `config_load` / `config_save` / `config_apply_line` for `wall_id`, `idle_sec`
- [x] `config_dump_serial` includes new keys
- [x] Optional: `idle_sec=0` disables idle → PAGE_IDLE in `ui_loop`

**Verify:** `#CFGREAD` over serial shows `wall_id=0`

---

## Task 4: `attach_wave` multi-wallpaper

- [x] Change signature: `attach_wave(lv_obj_t *scr, lv_opa_t veil, uint8_t wall_id)`
- [x] `ui_init`: pass `gCfg.wall_id` (or loaded NVS) for each screen
- [x] Add `ui_apply_wallpaper(uint8_t id)` — updates all screens' bg img, saves config, refresh current page
- [x] For **宣纸 (id=2)**: set flag `sChromeDark`; adjust DESK/USAGE label colors in `ui_refresh_from_status`

**Verify:** Manual `#CFGLINE|wall_id=1` + reboot shows Ember on DESK

---

## Task 5: `PAGE_SETTINGS` UI

- [x] Add `PAGE_SETTINGS` to enum; `sScreens[PAGE_COUNT]`, `show_current` branch
- [x] `make_settings(scr)` — two logical subpages (LOOK + MORE) via `sSettingsSub` index
- [x] LOOK: thumb grid (6 walls), tap → `ui_apply_wallpaper`
- [x] LOOK: rows for voice_mode, voice_target (cycle on tap, save config)
- [x] LOOK: PC status label (derive from USB + last successful poll timestamp)
- [x] MORE: warn/alert display, idle_sec cycle, SYNC row, TOKEN hint
- [x] Back ‹ chip + swipe right to exit

**Verify:** On device, all rows tappable; wallpaper swaps instantly

---

## Task 6: Navigation / entry

- [x] **发送 long-press** on DESK: if not recording, after ~1200 ms → `sPage = PAGE_SETTINGS`; remember `sSettingsFrom = DESK`
- [x] **USAGE last page swipe left**: in `ui_next_page` / `on_swipe`, replace `ui_toast("END")` with open settings; `sSettingsFrom = USAGE`
- [x] Exit settings: restore `sSettingsFrom` page on back/swipe right
- [x] Ensure `bubble_tree` + event bubble rules from touch fix remain (don't regress swipe)

**Verify:** Both entry paths; exit returns to correct page; PACK egg unchanged

---

## Task 7: Fonts & copy

- [ ] Regenerate `font_idle_12/16` with glyphs: 设置 壁纸 语音 注入 电脑 连接 同步 息屏 警告 …
- [x] English labels where screen tight: WALL / MORE / LOOK OK per preview

**Verify:** No tofu on settings rows

---

## Task 8: Docs & flash

- [x] Update `docs/keys.md` — settings entry, six wallpapers
- [x] Update `docs/handoff.md` — flash size note (~690 KB walls)
- [x] Build + flash MAC `28:84:85:56:ee:e0` only (DIO)
- [ ] Smoke: swipe, settings, wallpaper persist reboot, voice_mode still works

---

## Phase 2 stub

Plan: `docs/superpowers/plans/2026-08-22-host-installer-wizard.md`

- [x] `host/desk_pair.py` — shared MAC detect + `#CFG*` push
- [x] `host/setup_wizard.py` — dev CLI pairing
- [ ] PyInstaller spec for `desk_host.py`
- [ ] GUI wizard + QR URL in device Settings row

---

## Commit guidance

- Phase 1 can be 2–3 commits: (1) assets+pipeline, (2) UI+config, (3) docs/fonts
- Do not commit `host/secrets/*` or buyer keys
