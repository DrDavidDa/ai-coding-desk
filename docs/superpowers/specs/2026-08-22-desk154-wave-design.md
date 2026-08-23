# Desk154 Wave Skin — Design

**Date:** 2026-08-22  
**Status:** Approved (HTML review wall `docs/desk154-wave-pages.html`)  
**Scope:** Full-device Wave visual language + USAGE A + Token / AI temple oracle.

## Locked decisions

| Topic | Choice |
|---|---|
| Tone | **A Wave** — product-poster fluid cyan / orange / magenta |
| Background | One static 240×240 RGB565 wave image on DESK / USAGE / PLAN / IDLE / PACK |
| Veil | DESK ~22% · USAGE ~42% · PLAN ~48% · IDLE ~55% · PACK ~35% |
| USAGE | **A liquid tiles** — fill height = **remaining %**; brand name text large (~14px); &lt;20% hot edge |
| SYNC | No permanent “SYNC” label; amber ↻ only when host data is stale |
| DESK controls | Glass chips; mic + square STOP centered; icons ~44px |
| Right button | **Filled square STOP = end & send** (invariant; never ban icon / never cancel) |
| PACK | Counter = **TOKEN**; tap = **+1K**; display auto-scales K / M / B / T |
| Shake on PACK | **AI temple oracle** (上上 / 中平 / 下下 + short AI-user verse) — not token bonus |
| Global shake | Still undo / cancel / stop per `docs/keys.md` — does not open oracle off PACK |
| Out of milestone | Live fluid animation; Ember/Lab mix; on-device ASR; wireless Opus |

## Page map (unchanged HCI)

```text
DESK  ↔  USAGE (liquid grid, multi-page)
              │ tap tile
              ▼
            PLAN
IDLE ← timeout
PACK ← egg (long-press square STOP ~1.2s, or USAGE title ×5)
```

## Visual tokens

- Wave art: `docs/assets/wave-bg-240.png` → firmware `src/assets/wave/bg.rgb565`
- Controls: white glass, amber accent (讲话 / stale ↻ / pager), hot coral for REC chrome & low remain
- Typography: large brand names on USAGE A; Outfit-like Latin weights where Montserrat allows

## Invariants

See `docs/superpowers/specs/recording-controls.md` and `docs/keys.md`.

## Preview

- `docs/desk154-wave-pages.html` (serve via `docs` http.server)
- Firmware: `waveshare_lcd_154`
