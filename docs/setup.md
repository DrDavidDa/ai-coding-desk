# Setup

## Host (Windows)

```bat
cd /d E:\ai-coding-desk\host
py -3 -m pip install -r requirements.txt
copy ..\..\Documents\PlatformIO\Projects\PaperColor_Study\zhipu_token.txt secrets\zhipu_token.txt
py -3 desk_host.py
```

Default bind: `0.0.0.0:8787`. Device polls `GET /v1/status?key=<HOST_KEY>`.
Default key is `desk-local` (change in `secrets/host_key.txt`).

Token files (never commit):

- `host/secrets/zhipu_token.txt` — Cookie `bigmodel_token_production` value
- `host/secrets/sf_api_key.txt` — SiliconFlow（可从 PaperColor 工程复制；没有则自动读那份）
- Claude: `%USERPROFILE%\.claude\.credentials.json` (already on disk if `claude` works)
- Codex: `%USERPROFILE%\.codex\auth.json`
- Cursor: host reads the local Cursor session and pulls `cursor.com/api/usage-summary`
- Kimi Code: `%USERPROFILE%\.kimi-code\credentials\kimi-code.json` (refreshed in place)

## Chrome extension (Cursor)

1. `chrome://extensions` → Developer mode → Load unpacked → `chrome-extension/`
2. Stay logged in at https://cursor.com/dashboard/usage
3. Popup → set host `http://127.0.0.1:8787` and the same key

## Firmware

Firmware **compiled** for `waveshare_lcd_154` (Arduino-ESP32 2.0.17, Arduino_GFX 1.4.7, LVGL 8.3.11).

```bat
cd /d E:\ai-coding-desk\firmware
pio run -e waveshare_lcd_154
pio run -e waveshare_lcd_154 -t upload --upload-port COMx
```

Identify the 1.54 by USB serial / MAC. PaperColor on this machine was COM4
(`44:1B:F6:C1:7E:C8`) — do not flash that board. Hold BOOT while plugging USB
if the port does not appear.

## First boot / Wi-Fi

1. Device starts a captive portal `Desk154-Setup` if NVS has no SSID.
2. Or USB: `py -3 host/write_config.py --port COMx` (chunks + ACK, PaperColor protocol).

Serial diagnostics (newline-terminated, same as PaperColor):

- `#STATUS`
- `#POLL`
- `#CFGREAD`
- `#CFGCLEAR` / `#CFGLINE|k=v` / `#CFGDONE`
