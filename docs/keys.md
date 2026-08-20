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
| PWR | 5 | recording: cancel. Run: Stop. Idle coding: Up. Other apps: sync. | 3 s power off |
| PLUS | 4 | ignored (device-mic) | talk; release injects text (no Enter) |

**Shake** (not a key tap): recording → cancel. Agent running → Stop. Idle → undo last inject (or Ctrl+Z). Compressor page → press.
**Flip face-down**: mute dings, block talk/inject, RGB off. Backlight stays full on. Flip back up restores audio/RGB.
**Knock the desk**: ignored. This panel has no useful backlight range; PWM stays 100%.

Touch: DESK (顶栏发送/取消/讲话 + 麦克风/禁止圆钮；录音显示秒数并脉冲) swipe left → USAGE → compressor.
Swipe right on DESK stays. Logo tap opens PLAN; any swipe on PLAN returns to USAGE.
Quota: 70% one ding, 90% one ding and again every 2 min. Lamp already goes red at 90%.
PACK: tap or shake queues a press. Counter is `节省 {amt} 词元`, starts at 0K. Wood knock plays 35ms into the piston-down frame. Hold 1.4s to reset. Token count persists.

BLE name: `Desk154`. Pair in Windows Bluetooth settings. No host BLE stack required.

## RGB priority (GPIO 43 UART TX pad)

1. Quota >= 90% — red blink
2. PTT — rainbow
3. Agent working blue / waiting amber blink / done green / error red
4. Idle white breathe; >= 70% amber breathe

## Serial (USB CDC, `\n` terminated)

`#STATUS` `#POLL` `#CFGREAD` `#CFGCLEAR` `#CFGLINE|k=v` `#CFGDONE` `#ENTER host` `#PWR` `#UNDO` `#STOP`

Do not send GLM JWT to the device. Host URL + Wi-Fi only.
