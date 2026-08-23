# Desk154 Settings + Six Wallpapers — Design

**Date:** 2026-08-22  
**Status:** Approved (priority locked)  
**Scope:** Phase 1 = device settings + 6 prebaked wallpapers. Phase 2 = Host installer + pairing wizard (separate plan).

## Priority (user locked)

1. **Phase 1 — Device:** `PAGE_SETTINGS`, six static wallpapers, NVS persistence, dual entry paths.  
2. **Phase 2 — Host:** single Windows installer, first-run wizard, one-click pair (no manual IP).

## Product constraints (unchanged)

- PC assistant remains **required** for Chinese ASR → Cursor/Claude inject and quota collectors (`docs/product-wireless.md`). Settings page must show honest **PC connected / not connected** + QR to download Host (Phase 2 URL).
- **Recording HCI invariants** unchanged (`docs/superpowers/specs/recording-controls.md`): square STOP = send; cancel = top chip / PWR; TOKEN egg = long-press STOP only.
- Flash **DIO 16MB**; target board MAC `28:84:85:56:EE:E0` only.

---

## Phase 1 — Six wallpapers

### Locked set

| `wall_id` | Name   | Source (to author)     | Veil tweak | UI note |
|-----------|--------|------------------------|------------|---------|
| 0         | Wave   | `wave-bg-240.png` (existing) | baseline   | current Wave skin |
| 1         | Ember  | new `wall-ember-240.png`     | slightly lighter | warm orange/black |
| 2         | 宣纸   | new `wall-ink-240.png`       | light veil | **dark chrome** on controls (invert glass) |
| 3         | 磷光   | new `wall-phosphor-240.png`  | medium     | green terminal grid |
| 4         | 夜空   | new `wall-night-240.png`     | medium     | indigo + stars |
| 5         | 石面   | new `wall-stone-240.png`     | heavier    | cool concrete grey |

Each asset: **240×240 RGB565 LE**, ~115 KB flash → **~690 KB total** (acceptable at ~37% app flash used today).

### Pipeline

```
docs/assets/wall-*.png
  → firmware/tools/png_to_wave.py --all   # batch
  → firmware/src/assets/wave/{wave,ember,ink,phosphor,night,stone}.rgb565
  → extra_script.py emits wave_img.S (concat or multiple incbin symbols)
  → wave_img.c: const lv_img_dsc_t kWallImgs[6]
  → attach_wave(scr, veil_opa, wall_id) picks kWallImgs[wall_id]
```

Preview wall: `docs/desk154-settings-preview.html` (companion; CSS placeholders until PNGs land).

### Persistence

- NVS namespace `desk154`, key `wall_id` (uint8, 0–5), default **0 (Wave)**.
- Extend `DeskConfig` + `#CFGLINE|wall_id=N` for USB push (optional; UI is primary).

### Behaviour

- Change wallpaper in Settings → immediate `attach_wave` on all `sScreens[]` + save NVS.
- **宣纸 (ink)** may require `ui_set_chrome_dark(bool)` so DESK/USAGE text stays readable; other skins use current light-on-glass tokens.

---

## Phase 1 — Settings page (`PAGE_SETTINGS`)

### Entry (dual path — locked)

| Path | Gesture | Notes |
|------|---------|-------|
| A | DESK top chip **发送** long-press ~1.2 s | Same timing family as STOP egg; no conflict if handlers are separate widgets |
| B | USAGE swipe **left past last logo page** | Replaces toast `END`; opens Settings instead of dead-end |

Exit: swipe right, or back chip ‹ → previous page (DESK if came from A, USAGE if came from B).

**Not** on main swipe ring: PACK/TOKEN egg stays long-press STOP / USAGE title ×5 only.

### Page map

```text
PAGE_DESK ↔ PAGE_USAGE (multi-page) → PAGE_PLAN (tile tap)
              ↓ past last page
         PAGE_SETTINGS (2 sub-screens, vertical or horizontal tabs)

PAGE_IDLE / PAGE_PACK / PAGE_PLAN: unchanged
```

### Screen 1 — LOOK / WALL

| Row | Control | NVS / action |
|-----|---------|--------------|
| Wallpaper | 2×3 or paged 4-thumb grid, tap to apply | `wall_id` |
| 语音 | cycle: 本机麦 / HID | `voice_mode` device\|hid |
| 注入到 | cycle: CURSOR / CLAUDE / CODEX | `voice_target` |
| 电脑 | read-only: 已连接 / 未连接 | USB serial recent OR `net_poll` ok within 60 s |

### Screen 2 — MORE

| Row | Control | NVS / action |
|-----|---------|--------------|
| 额度警告 | tap cycles 70/90 display (both stored) | `warn_threshold`, `alert_threshold` |
| 息屏 | 3 min / 5 min / 关 | new `idle_sec` (0 = off, default 180) |
| 同步 | tap → `#POLL` + toast SYNC | existing `net_poll_now` |
| TOKEN | hint text only: 长按清零在 TOKEN 页 | no new action |

Footer: `swipe back` (match PLAN foot style).

### Visual

- Same Wave chrome as review wall: static BG + veil ~55% on settings (readable rows).
- Typography: existing `font_idle_*` + Montserrat labels; Chinese via extended idle fonts if needed (`设置` `壁纸` `语音` …).

### Files (primary)

| Area | Files |
|------|-------|
| Assets | `docs/assets/wall-*.png`, `firmware/src/assets/wave/*.rgb565` |
| Tools | `firmware/tools/png_to_wave.py`, `firmware/extra_script.py`, `firmware/src/wave_img.{h,c,S}` |
| Config | `firmware/src/config.{h,cpp}`, `serial_cmd.cpp` |
| UI | `firmware/src/ui.{h,cpp}` — enum, `make_settings`, nav, `attach_wave` |
| Docs | `docs/keys.md`, `docs/handoff.md`, preview HTML |

---

## Phase 2 — Host installer + pairing wizard (outline only)

Deferred until Phase 1 ships. Requirements captured here for continuity.

### Minimum user steps (sellable)

1. Install **Desk154Setup.exe** (PyInstaller/Nuitka; no Python on customer machine).
2. Wizard: autostart ON → plug USB → **一键配对** (push `host_url` + `host_key` via `#CFG*`).
3. Optional: Wi-Fi SSID/password push from wizard (replaces `write_config.py` for buyers).
4. Tray: green = device + poll OK; test inject one line in Cursor.

### Device side (Phase 2)

- Settings row **电脑** shows paired state; QR opens download page.
- No change to Phase 1 wallpaper/settings layout.

### Host side (Phase 2)

| Deliverable | Purpose |
|-------------|---------|
| `Desk154Setup.exe` | Install to `%LocalAppData%`, autostart, secrets dir |
| First-run wizard | MAC-detect COM, pair, smoke test |
| Tray menu | Refresh / Open settings folder / Quit |
| Remove from buyer docs | `pip install`, manual IP, `write_config.py` |

---

## Out of scope (both phases)

- SoftAP captive portal (future; reduces PC for Wi-Fi only).
- OTA firmware update UI.
- On-device ASR or zero-PC Chinese inject.
- Replacing TOKEN/PACK easter egg with Settings.

## Success criteria

**Phase 1**

- [ ] All six wallpapers selectable; persist across reboot.
- [ ] Settings reachable via both entry paths; exit returns correctly.
- [ ] Changing voice_mode / voice_target affects `buttons.cpp` / `voice.cpp` after save.
- [ ] Flash build < 45% app slot; DESK154 MAC flash verified.
- [ ] Preview HTML updated with final PNG thumbnails.

**Phase 2**

- [ ] Fresh Windows VM: install exe → pair → speak in Cursor without editing txt/json.
- [ ] README/setup.md buyer path is one page + QR.

## References

- `docs/desk154-settings-preview.html` — visual companion
- `docs/superpowers/specs/2026-08-22-desk154-wave-design.md` — Wave HCI baseline
- `docs/product-wireless.md` — why Host stays mandatory
