# Desk154 交接文档

更新于：2026-08-20

## 设备

| 项 | 值 |
|---|---|
| 板子 | Waveshare ESP32-S3-Touch-LCD-1.54（SKU 33869） |
| MAC | `28:84:85:56:EE:E0` |
| 应用口（CDC） | 通常 **COM8**（SER=`28848556EEE0`） |
| 下载口（ROM） | 通常 **COM7**（SER=`28:84:85:56:EE:E0`） |
| PIO env | `waveshare_lcd_154` |
| Host | `E:\ai-coding-desk\host\desk_host.py` |

**禁止**烧 PaperColor（COM4，`44:1B:F6:C1:7E:C8`）或其它 ESP。Flash 模式用 **DIO**，不要 QIO。

## 物理键（面对屏幕 L→R）

**BOOT | PWR | PLUS** → 屏上顶栏：**发送 | 取消 | 讲话**

| 键 | 功能 |
|---|---|
| BOOT / 发送 | Enter（录音中忽略） |
| PWR / 取消 | 录音取消；运行中 Stop；空闲↑ |
| PLUS / 讲话 | 按住说话，松开注入文本（不回车） |

## TALK / DESK 页（当前 UI）

- 顶栏：三个橘黄圆角按钮，白字「发送 / 取消 / 讲话」（无 BOOT/PWR/PLUS 英文）
- **已删除**：语音输入标题、电池%、转写乱码行
- 主区：左侧大圆钮 **麦克风图标**（开始/结束录音），右侧大圆钮 **禁止图标**（取消/Stop）
- 录音中：中间显示秒数 `N.N`；麦克风光晕 + 图标蓝/白脉冲变色；顶条闪烁

图标字体：`firmware/src/fonts/font_icons.c`（FA solid `mic`/`ban`）。源 TTF 不入库（`.gitignore` 已忽略 `*.ttf`）。

## 烧录流程（可靠）

1. 停 host：结束所有 `desk_host.py`
2. COM8 @ 1200 触摸进下载 → 口跳到 COM7
3. esptool **4.5.1**（`tool-esptoolpy@1.40501.0`）DIO 16MB，`--before no_reset --after no_reset`
4. esptool **5.x** `--after watchdog-reset` 出下载模式 → 回到 COM8
5. 确认 MAC `28:84:85:56:ee:e0`
6. 起 host：`DESK_NO_TRAY=1`，`py -3 -u desk_host.py`（监听 COM8）

## Host / 额度

- Trae + 扣子（Coze）collector 已接；USAGE 品牌索引 7 = `coze`（非 MiniMax）
- **Claude Code 品牌**：DeepSeek 余额挂在 **Claude Code** logo/PLAN 上（标题 CLAUDE CODE、脚注 YUAN）；USAGE **不单独出** DeepSeek 瓦片。Host 仍分 `providers.claude` / `providers.deepseek` 采集
- 网页原型 `docs/desk154-live.html` 会拉 `127.0.0.1:8787/v1/status` 同步开关与余额
- 额度叮：水滴音 `play_ding()`，日志 `[BEEP] drop`
- Coze logo：改 `frames.rgb565` 后靠 `extra_script.py` 的 sha256 强制 relink `logos.S`

## 滑动导航

- DESK 左滑 → USAGE（不是 PACK）
- USAGE 页翻完 → PACK
- Logo 点进 PLAN；默认三行 **5H / 7D / 1M**（GLM 第三窗也是月度工具额度，标 1M，不再写 MCP）；Cursor 据实只显示 **AUTO / API**
- PLAN 任意滑回 USAGE

## 关键改动文件

| 路径 | 说明 |
|---|---|
| `firmware/src/ui.cpp` | DESK/TALK 布局、顶栏中文、双圆图标钮、录音计时+脉冲 |
| `firmware/src/fonts/font_icons.{h,c}` | 麦克风 / 禁止图标 |
| `firmware/src/fonts/font_idle_16.c` | 含「发送取消讲话」等汉字 |
| `firmware/src/beep.cpp` | 水滴叮 |
| `host/collectors/trae.py` / `coze.py` | 额度采集 |
| `firmware/extra_script.py` | logo/pack incbin hash |
| `docs/keys.md` | 按键说明 |

## 未决 / 注意

- 企业 Wi‑Fi（WPA2-Enterprise）设备连不上时，语音走 USB 串口 WAV → host SenseVoice
- 屏上转写中文依赖 `font_idle_*` 字库；缺字会方框/乱码（TALK 页已不再显示转写行）
- 交接文档：`docs/handoff.md`；进展已入库（见 git log）
- **Claude / DeepSeek 错位（已修）**：旧逻辑把 DeepSeek 余额挂到 Claude，且 PLAN 把 token-only Claude 改名为 DEEPSEEK。现已拆成 `claude`（OAuth）+ `deepseek`（余额）；PLAN 标题跟真实品牌，余额脚注 `YUAN x.xx`

## 快速自检

1. 顶栏三中文橘钮
2. 中间无电池/乱码；两大圆：麦 / 禁
3. 点麦 → 秒数出现 + 麦钮脉冲
4. 点禁或 PWR → 取消录音
5. host 日志 COM8，`[OK] poll`
