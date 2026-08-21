# Desk154 Scheme 1 — UI / HCI Design

**Date:** 2026-08-21  
**Status:** Approved via HTML preview (`docs/desk154-lab.html`)  
**Scope:** Information architecture, global caps, Logo USAGE, compressor easter egg. Lab cold skin may follow in a separate experimental firmware env.

## Decisions

| Topic | Choice |
|---|---|
| Home | **DESK** (发送 / 取消 / 讲话 + 麦 / 禁) |
| Quota | **Logo fill USAGE** (not three-ring gauges) |
| Caps | **Global** on every page |
| REC feedback | Stay on page; top flash + toast; timer pill when not on DESK |
| Compressor | **Easter egg** — not in main swipe path |

## Page map

```text
DESK  ←→  USAGE (logo grid, multi-page)
                │ tap logo
                ▼
              PLAN (5H/7D/1M · Cursor AUTO/API · Claude YUAN)
              
IDLE ← timeout from DESK/USAGE (not during REC)

PACK ← egg only (long-press SYNC ~1.2s, or USAGE title ×5)
```

### DESK
Primary voice surface. On-screen chips mirror physical caps. Full REC timer + mic pulse while recording.

### USAGE
2×2 Logo tiles; gray base + color crop = remain %. SYNC refreshes host. Pager when >4 brands. Swipe past last page does **not** open the game (toast END).

### PLAN
Drill-down per vendor. Back → USAGE.

### IDLE
Clock / battery. Touch or any cap wakes to DESK.

### PACK (egg)
Compressor clicker. Back / swipe returns to USAGE. Caps still record/cancel/send globally.

## Global caps (physical + on-screen DESK chips)

| Cap | Action |
|---|---|
| 讲话 (PLUS) | Start/stop hold-to-talk (existing voice modes); **do not force DESK** |
| 取消 (PWR) | Cancel REC or stop agent / ESC |
| 发送 (BOOT) | Enter / send while REC ends with send |

While recording: navigation blocked; chrome shows on current page.

## Visual language (Lab tokens — HTML first)

- BG `#0B0D10`, surface `#161A22`, ink `#F4F6F8`, mute `#8B93A1`, accent `#E8A04A`, hot `#E07050`, track `#252A33`
- Thin tracks on PLAN; Logo USAGE unchanged in structure
- Three-ring mock = token inspiration only

## Preview

- HTML: `docs/desk154-lab.html`
- Firmware HCI: official `ui.cpp` (this iteration)
- Full Lab skin / `waveshare_lcd_154_lab`: follow-up
