# Desk154 交接文档

更新于：2026-08-23

## 一句话

桌上的 1.54″ 圆屏：看各家 Coding Plan 额度、按住说话打进当前对话框、额度页摇三下抽 AI 签。密钥只在 Windows 主机。

## 设备（只这一块）

| 项 | 值 |
|---|---|
| 板子 | Waveshare ESP32-S3-Touch-LCD-1.54（SKU 33869） |
| MAC | `28:84:85:56:EE:E0` |
| 应用口（USB-JTAG CDC） | 通常 **COM8**（SER=`28848556EEE0`） |
| 下载口（ROM） | 通常 **COM7**（SER=`28:84:85:56:EE:E0`） |
| PIO env | `waveshare_lcd_154` |
| Flash | **DIO 16MB**（不要 QIO） |
| Host | `host/desk_host.py`（买家包：`Desk154.exe`） |

**禁止**烧 PaperColor（COM4）以及其它 ESP（常见坑：COM9 `28:84:85:76:2F:08`、COM11 `CC:8D:A2:E0:BF:88`）。

USB-JTAG 卡住（Win 错误 31 / COM8 消失）：拔 USB **和** 电池，先电池后 USB。不要发 `#DOWNLOAD`。

## 物理键（面对屏幕 L→R）

**BOOT | PWR | PLUS** → 屏上顶栏：**发送 | 取消 | 讲话**

| 键 | 短按 | 长按 / 按住 |
|---|---|---|
| BOOT | Enter（录音中忽略） | 下载绑带，固件不占用 |
| PWR | 录音=取消；Agent 跑着=Stop；空闲=#PWR 刷新 | **1.2 秒息屏**；继续按到 **3 秒，松开后 deep-sleep** |
| PLUS | 忽略（太短不当说话） | 按住说话，松开注入（不回车） |

唤醒（息屏）：点屏或任意键（第一下只亮屏）。**摇一摇不唤醒。**  
唤醒（关机）：只有再按 **PWR**。开机后若键还按着，这一下会被丢掉，避免立刻再睡。  
关机等 **松手** 才 `deep-sleep`（按着睡会被 ext0=LOW 立刻拍醒）。不拉低 `BAT_EN`。插着 USB 时关机后 host 可能掉线，再按 PWR 会回来。真拔电：拔 USB。

## 现在固件里有什么

- DESK：顶栏三中文钮 + 麦圆 + 方块结束（结束并发送，不是取消）
- USAGE：品牌额度环；点进 PLAN（5H / 7D / 1M；Cursor = AUTO / API）
- Settings：六壁纸 Wave / Ember / Ink / Phosphor / Night / Stone（NVS `wall_id`）
- 空闲：默认 5 分钟全黑（背光+RGB 灭）；NVS `idle_sec`，旧值 180 会迁成 300
- **AI 庙**：100 签，不放回洗牌；**只在 USAGE 页** 3.5 秒内连晃 3 下；其它页忽略（防口袋）
- 语音：没 Wi‑Fi 时 WAV 走 USB 串口；企业 WPA2-Enterprise 上不了板载 Wi‑Fi
- 注入：跟随当前焦点编码窗口，无设置里的「发到」
- 趴下（prone）：静音 / 关 RGB；翻回来恢复
- 彩蛋：DESK 长按方块 STOP → TOKEN 压缩机

## 烧录流程（可靠）

1. 停所有 `desk_host.py` / `Desk154.exe`
2. COM8 @ 1200 触摸进下载（常报 OSError 22/433）→ 口变成 COM7，序列号带冒号
3. `chip-id --before no_reset` 必须看到 `28:84:85:56:ee:e0`
4. esptool **4.5.1** DIO 16MB `--before no_reset --after no_reset` 写 bootloader + partitions + boot_app0 + firmware
5. esptool **5.x** `--before no-reset --after watchdog-reset` 出下载（不要 DTR hard-reset，会把屏弄黑）
6. COM8 回来后：`$env:DESK_NO_TRAY=1; py -3 -u desk_host.py`

打开串口：DTR true，RTS false；**不要脉冲 DTR**。

## Host / 买家包

- 采集：Claude、Cursor、Codex、GLM、Kimi、Trae、扣子；DeepSeek 余额挂在 Claude Code 砖上
- 打包：`host/pack_windows.ps1` → `host/dist/Desk154-Windows.zip`
- 向导：USB 配对、可选 Wi‑Fi、可选 SiliconFlow Key、开机自启
- 冻结数据：`%LocalAppData%\Desk154`
- 客户说明：`docs/setup-buyer.md`（客户不烧录、不 pip）

## 滑动导航

- DESK 左滑 → USAGE → 再滑 → Settings
- Settings 右滑或 ‹ 回上一页
- Logo 点进 PLAN；PLAN 任意滑回 USAGE
- PACK/TOKEN 仍靠 STOP 长按，USAGE 页不靠摇一摇进游戏

## Flash 占用

六壁纸 RGB565 @ 240×240 + 应用 ≈ 一半 16MB DIO（以 `pio run -e waveshare_lcd_154` 的 Checking size 为准）。

## 关键路径

| 路径 | 说明 |
|---|---|
| `firmware/src/ui.cpp` | 页面、壁纸、抽签浮层、5 分钟熄屏 |
| `firmware/src/buttons.cpp` | 三键；PWR 1.2 秒息屏，3 秒松手 `board_power_off()` |
| `firmware/src/display.cpp` | 熄屏 / 唤醒；触点吞掉，避免黑屏立刻被点亮 |
| `firmware/src/imu.cpp` | 抽签仅 USAGE；熄屏不唤醒 |
| `firmware/src/oracle_lots.cpp` | 100 条 AI 签 |
| `firmware/src/wave_img.*` + `wall_*.S` | 壁纸 |
| `host/desk_host.py` | 托盘 + 额度 + 串口 |
| `host/inject.py` | 跟随焦点注入 |
| `host/setup_gui.py` / `setup_wizard.py` | 买家向导 |
| `docs/setup-buyer.md` | 开箱卡片 |
| `docs/keys.md` | 按键与串口 |

## 未决 / 注意

- 企业 Wi‑Fi 连不上时语音走 USB WAV
- 屏上汉字依赖 `font_idle_*`；缺字会方框
- USB 插着时 deep-sleep 省电有限（线还在供电）；`BAT_EN` 不能闩低，否则 LCD 电轨会卡死
- GitHub Pages 演示：`docs/desk154-lab.html`

## 快速自检

1. 顶栏三中文橘钮；两大圆：麦 / 方块
2. 点麦 → 秒数 + 脉冲；PWR 或顶栏取消 → 丢录音
3. 额度页连晃 3 下出签；DESK 页晃不动签
4. PWR 按 1.2 秒息屏；按满 3 秒灯闪再松开关机；再按 PWR 开机。息屏可点屏唤醒，关机不行
5. host 盯 COM8，额度数字会变
