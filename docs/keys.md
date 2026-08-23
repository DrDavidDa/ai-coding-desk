# Keys, HID, RGB

## Physical (active-LOW)

Cap L→R facing the screen: **BOOT | PWR | PLUS**.

Claude YES / n / MODE are **not** on the puck. Those are Claude Code CLI
permission keys (`Enter` / `n` / `Shift+Tab` or Windows `Alt+M`). Cursor and
Codex do not use that TUI. BOOT is already Enter, so YES was a duplicate.
Use the computer keyboard for `n` and MODE.

| Focused surface | BOOT | PWR (run) | PWR (idle) |
|---|---|---|---|
| **Cursor app** | Enter / Ctrl+Enter after Stop | Stop | ↑ |
| **Coding CLI** | Enter (nudge after Stop) | Ctrl+C | ↑ |
| **Other apps** | ignored | — | refresh meters |

| Button | GPIO | Short | Long / hold |
|---|---|---|---|
| BOOT | 0 | Enter (Play/submit). Ignored while recording. | download strap |
| PWR | 5 | recording: cancel. Run: Stop. Idle coding: Up. Other apps: sync. | 3 s blank screen (MCU stays up) |
| PLUS | 4 | ignored (device-mic) | talk; release injects text (no Enter) |

**Settings (Phase 1):** six wallpapers (Wave/Ember/Ink/Phosphor/Night/Stone), voice mode, inject target, PC status, warn thresholds, idle timer, SYNC. NVS keys `wall_id`, `idle_sec`; serial `#CFGLINE|wall_id=N`, `#CFGLINE|idle_sec=N`.

**Shake** (not a key tap): recording → cancel. Agent running → Stop. **任意页连晃 3 下**（约 3.5 秒内）→ AI 庙抽签浮层；签已出时再晃 = 重抽，点空白收起。TOKEN 页不响应晃动手势。单次晃后停顿较久 → undo。
**Flip face-down**: mute dings, block talk/inject, RGB off. Backlight stays full on. Flip back up restores audio/RGB.
**Knock the desk**: ignored. This panel has no useful backlight range; PWM stays 100%.

Touch: DESK (顶栏发送/取消/讲话 + 麦克风/**方块结束**圆钮；录音显示秒数并脉冲) swipe left → USAGE.
Caps are **global** on every page: PLUS talks without forcing DESK; REC shows a top flash
bar + timer pill when away from DESK. Swipe past last USAGE page opens **Settings** (not dead-end).
**Settings entry:** long-press top **发送** ~1.2s on DESK, or swipe left past last USAGE page.
Settings exit: swipe right or ‹ back chip → previous page (DESK or USAGE).
**记住：右侧圆钮 = 方块 STOP = 结束录音并发送（不是取消）。取消只走顶栏「取消」/ PWR。**
**Easter eggs (independent):**
- **TOKEN** — DESK 页长按方块 STOP ~1.2s（未录音）→ 压缩机 +1K 游戏
- **AI 庙** — 任意页 **连晃 3 下**（约 3.5 秒内），或 USAGE 顶栏标题连点 5 次 → 直接出签
Swipe right on DESK stays. Logo tap opens PLAN; any swipe on PLAN returns to USAGE.
Quota: 70% one ding, 90% one ding and again every 2 min. Lamp already goes red at 90%.
USAGE: **liquid tiles** = remaining % (Wave skin). Sync is a small ↻ chip.
PACK/TOKEN: tap queues compressor (+~1K tokens, auto K/M/B/T). Hold 1.4s to reset. Token count persists. (No oracle on this page.)

BLE name: `Desk154`. Pair in Windows Bluetooth settings. No host BLE stack required.

## RGB priority (GPIO 43 UART TX pad)

1. Quota >= 90% — red blink
2. PTT — rainbow
3. Agent working blue / waiting amber blink / done green / error red
4. Idle white breathe; >= 70% amber breathe

## Serial (USB CDC, `\n` terminated)

`#STATUS` `#POLL` `#CFGREAD` `#CFGCLEAR` `#CFGLINE|k=v` `#CFGDONE` `#ENTER host` `#PWR` `#UNDO` `#STOP`

Do not send GLM JWT to the device. Host URL + Wi-Fi only.
