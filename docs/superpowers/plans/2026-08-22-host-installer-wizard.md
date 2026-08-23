# Host Installer + Pairing Wizard — Phase 2 Plan

> **Prerequisite:** Phase 1 firmware (Settings + six wallpapers) flashed and verified on MAC `28:84:85:56:EE:E0`.

**Goal:** Buyer installs one Windows exe, plugs USB, clicks **一键配对** — no `pip install`, manual IP, or `write_config.py`.

**Architecture:** PyInstaller bundle of `desk_host.py` + collectors; first-run Tk/wizard UI calls `desk_pair.push_config()`; tray shows green when serial + `/v1/status` OK. Device Settings **PC** row reflects paired state (Phase 1 already shows OK/--).

**Spec:** `docs/superpowers/specs/2026-08-22-desk154-settings-wallpapers-design.md` (Phase 2 section)

---

## File map

| File | Responsibility |
|------|----------------|
| `host/desk_pair.py` | MAC COM detect, LAN host URL, `#CFG*` push (**done**) |
| `host/setup_wizard.py` | Dev CLI wizard (**done**) |
| `host/write_config.py` | Thin wrapper over `desk_pair` |
| `host/desk_host.py` | Import `find_desk_port` from `desk_pair` |
| `host/desk154.spec` | PyInstaller spec → `Desk154Setup.exe` |
| `host/installer/` | NSIS/Inno stub or PyInstaller one-file |
| `docs/setup-buyer.md` | One-page buyer guide + QR |

---

## Task 1: Shared pairing module ✅

- [x] `desk_pair.py`: `find_desk_port`, `local_host_url`, `push_config`, `probe_status`
- [x] `setup_wizard.py` CLI for dev pairing
- [ ] Refactor `write_config.py` + `desk_host.find_desk_port` to use `desk_pair`

**Verify:** `py -3 setup_wizard.py --no-push` lists correct COM when Desk154 plugged in

---

## Task 2: GUI wizard (first-run)

- [ ] Tkinter or custom window: welcome → autostart toggle → **Pair now**
- [ ] Show detected COM + MAC; block if wrong device (not `28848556EEE0`)
- [ ] Auto-fill `host_url` from `local_host_url()`; editable if multi-NIC
- [ ] Optional Wi-Fi SSID/password fields (same as `wifi_extra.txt` flow)
- [ ] Progress: push → `#STATUS` probe → “Open Cursor and speak” hint
- [ ] Write `%LocalAppData%/Desk154/first_run.done` to skip on relaunch

**Verify:** Fresh VM without Python: exe only, pair succeeds

---

## Task 3: PyInstaller bundle

- [ ] `desk154.spec`: one-folder or one-file, include `collectors/`, `secrets/` template
- [ ] Entry: `desk_host.py` with tray; wizard spawns on first run before tray
- [ ] Autostart: registry `Run` key or Startup folder shortcut
- [ ] Version stamp in tray tooltip

**Verify:** `Desk154Setup.exe` < 80 MB; starts on login; `/healthz` on :8787

---

## Task 4: Tray polish

- [ ] Icon states: green (serial + poll OK), amber (host up, no device), red (error)
- [ ] Menu: Refresh / Open data folder / Open secrets folder / Pair again / Quit
- [ ] “Pair again” launches wizard push without reinstall

**Verify:** Unplug USB → tray amber; replug → green within 10 s

---

## Task 5: Device + docs

- [ ] Settings PC row: optional QR chip → download URL (Phase 2 landing page)
- [ ] `docs/setup-buyer.md` — single page, screenshots, QR
- [ ] Remove buyer-facing `write_config.py` / manual IP from README

**Verify:** Non-developer can complete flow from QR card in box

---

## Task 6: Smoke test matrix

- [ ] Pair → speak → inject in Cursor (device mic)
- [ ] Pair → HID mic mode → inject Claude
- [ ] Wi-Fi push optional SSID → puck connects without serial quota fallback
- [ ] Re-pair after host IP change (DHCP)

---

## Out of scope (Phase 2)

- SoftAP captive portal
- OTA firmware
- macOS / Linux host installer

---

## Commit guidance

- Phase 2 can ship as: (1) `desk_pair` + CLI, (2) GUI + spec, (3) buyer docs
- Never commit `host/secrets/*` with real keys
