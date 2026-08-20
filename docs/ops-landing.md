# 实际落地方案：语音 coding、三键、触屏、剩余算力

本文写的是 **你坐下写代码时设备怎么用**，不是架构口号。
当前仓库里：额度屏 / BLE 键盘 / RGB 已能编译；**板载麦 → PC 转写** 按本文落地（固件 `voice.cpp` + 主机 `/v1/audio`）。

---

## 0. 先记住一条分工

| 谁 | 只做什么 | 绝不做什么 |
|---|---|---|
| 设备 | 收音、按键、触控、显示额度、RGB、把 PCM/按键发出去 | 不做中文 ASR、不跑大模型 |
| Windows 托盘 `desk_host.py` | 转写、粘贴到当前输入框、拉四家额度 | 不把 Cookie/JWT 写进设备 |

ESP32-S3 算力不够做可靠的「语音编程 ASR」。PaperColor 已经验证过同一套路：设备只录音，**SiliconFlow SenseVoice** 在云端转写。本项目把转写从设备挪到 PC，避免设备 TLS 卡死（PaperColor 8.3 / ASR 坑）。

---

## 1. 语音 coding：两种模式（触屏 Voice 页切换）

### 模式 A — 板载麦收录（默认，Cursor / Codex / 任意输入框）

这才是「在设备上说话、字出现在 coding 对话框」。**注入不用 Ctrl+V**（终端 / IME / Electron 经常吃掉粘贴）。

```
按住 PLUS
  → 喇叭 PA 关闭（与麦共用时钟，PaperColor 同款）
  → ES7210 立体声 16 kHz，只保留左声道（MIC1 PGA=0x1B；MIC2 静音）
  → 丢掉开头几块 DMA 垃圾，PCM 进 PSRAM（最长约 12 秒）
  → 松开 PLUS
  → 静音门限：平均幅度太低则不上报
  → 后台任务打 WAV 头，WiFi POST 到电脑 http://<PC>:8787/v1/audio
  → 托盘 SenseVoice 转写（sf_api_key.txt，剥掉 <|zh|> 等标签）
  → Unicode SendInput 把字打进「当前焦点」对话框（失败才剪贴板 Ctrl+V）
```

**你怎么用：** 先把光标点在 Cursor Chat / Composer / Codex 终端输入框 → 按住 PLUS 说话 → 松手 → 字出现在光标处。然后 BOOT 短按 = Enter 发送。

录音 / 上传期间：不停额度轮询、Voice 页显示 REC→ASR、RGB 跟 agent_state。LVGL 继续跑，HTTP 在独立 FreeRTOS 任务里。

失败策略：转写失败保留上次成功文本，屏上 `ERR`，不要把额度环打成 0。

不抢焦点：默认不 SetForegroundWindow。你必须先点进对话框。需要主机把 Cursor 拉到前台时加 `?focus=1`。

### 模式 B — HID 热键（给 Claude Code 原声语音）

Claude Code 终端自己听 **电脑麦克风**，热键默认是 **按住 Space**。设备不录音，只当键盘：

```
按住 PLUS → BLE 按住 Space → Claude Code 开始听（用 PC 麦）
松开 PLUS → 松开 Space → CC 结束听写并作为 prompt
```

**Windows：** 设置 → 蓝牙 → 配对 `Desk154`。Claude Code 窗口保持焦点。

Cursor 没有「按住 Space 听写」这套，**写 Cursor 请用模式 A**。

### 模式怎么切

触屏 **Voice 页** 两个按钮：`板载麦` / `HID热键`。写入 NVS，掉电保留。串口也可：

```
#CFGLINE|voice_mode=device
#CFGLINE|voice_mode=hid
#CFGDONE
```

---

## 2. 三个实体键：写代码时到底按什么

外壳顶边从左到右（面对屏幕）：**BOOT | PWR | PLUS**（以微雪丝印为准；固件按 GPIO 绑，不按你猜的左右）。

| 键 | GPIO | 短按（<0.18 s） | 按住 | 长按 |
|---|---|---|---|---|
| **PLUS** | 4 | 模式 A：忽略（太短不录音）；模式 B：点一下 Space（toggle 听写） | **语音 PTT**（核心） | — |
| **BOOT** | 0 | **Enter / 确认 / 发送** | — | >0.6 s **Esc / 打断 Agent** |
| **PWR** | 5 | **切页**（额度 → Voice → Session） | — | 3 s 关机 |

### 映射到三个工具（这是「真正能用」的部分）

**Cursor（模式 A）**

| 你想做的事 | 操作 |
|---|---|
| 对着 Agent 说话 | 点进 Chat/Composer 输入框 → 按住 PLUS → 松手等字出现 |
| 发送 | BOOT 短按（Enter） |
| 停掉正在跑的 Agent | BOOT 长按（Esc） |
| 看额度 | PWR 短按切到 Cursor 页 |

**Claude Code 终端（模式 B）**

| 你想做的事 | 操作 |
|---|---|
| 语音 prompt | 焦点在 CC → 按住 PLUS = 按住 Space |
| 确认 Yes / 选默认项 | BOOT 短按 = Enter |
| 拒绝 / 打断 | BOOT 长按 = Esc；触屏 No = 键入 `n` |
| 切 Plan/普通模式 | 触屏 Voice 页「Mode」键 = `Shift+Tab`（见下） |

**Codex CLI（模式 A）**

与 Cursor 相同：板载麦转写粘贴 + Enter 发送 + Esc 打断。

### 为什么不做成「三个键三个软件」

三键太少。软件目标改由 **触屏 Voice 页的 Cursor / Claude / Codex 三选一** 决定粘贴后是否自动补一个 Enter，以及 HID 额外键：

| 触屏目标 | PLUS（麦） | BOOT 短 | BOOT 长 | 触屏 Mode 键 |
|---|---|---|---|---|
| Cursor | 录音→粘贴 | Enter | Esc | 无 |
| Claude | HID Space 或录音粘贴 | Enter | Esc | Shift+Tab（切换 plan） |
| Codex | 录音→粘贴 | Enter | Esc | 无 |

目标只影响「松手后要不要自动 Enter」和 HID 附加键，**不改变三颗实体键的手感**：永远是「说话 / 确认 / 切页」。

---

## 3. 触摸屏专门功能（240×240，一页一件事）

左右滑或 PWR 切页，顺序：

1. **Claude 额度** — 大环 5h，细字 7d + 重置时刻  
2. **Codex 额度** — 同上  
3. **Cursor 额度** — auto% / api%  
4. **GLM 额度** — 5h 环 + 7d/MCP + 今日 token + 搜索/网页次数（PaperColor 缩小版）  
5. **Voice** — 本页才是语音控制面  
6. **Session** — Agent 蓝/橙/绿/红、Wi-Fi、主机、电池  

每页底栏三颗虚拟键（手指比实体键更适合「点一下」）：

| 触屏 | 发给 PC | 用在 |
|---|---|---|
| **Yes** | Enter | 确认 diff / 发送 |
| **No** | `n` | Claude Code 「No」 |
| **Esc** | Esc | 取消 / 停 Agent |

**Voice 页专有：**

- 大状态：IDLE / REC / ASR / DONE  
- `板载麦` | `HID热键`  
- `Cursor` | `Claude` | `Codex`（当前目标高亮）  
- `Mode`：仅 Claude 目标时发 Shift+Tab  
- 上一句转写（主机带回 `voice.last_text`，最多两行）

不要在额度页上堆录音按钮——240×240 会不可读。

---

## 4. PC 转文字：主机具体怎么做

选定路线（必须走通的核心）：

| 步骤 | 在哪 | 做什么 |
|---|---|---|
| 1 收音 | 设备 ES7210 | 立体声→左声道 WAV，POST 局域网 |
| 2 转写 | PC `asr.py` | SiliconFlow SenseVoice，剥标签 |
| 3 注入 | PC `inject.py` | `SendInput KEYEVENTF_UNICODE` 打进焦点对话框 |
| 4 发送 | 设备 BOOT | BLE HID Enter（默认不自动发送，避免误发） |

`host/asr.py` 顺序：

1. 读 `host/secrets/sf_api_key.txt`（没有则回退 PaperColor 工程里那份）  
2. POST `http://api.siliconflow.cn/v1/audio/transcriptions`  
   model = `FunAudioLLM/SenseVoiceSmall`  
3. `inject.py` 把文本逐字 SendInput 到当前前台窗口  
4. SendInput 失败才剪贴板 Ctrl+V，并尽量恢复原剪贴板  
5. 若请求带 `send=1` 再补一个 Enter（默认关）

不经过设备直连 SiliconFlow（设备 TLS 到 SF 会挂）。

无麦自测注入（先点进 Cursor 对话框，3 秒内切回）：

```bat
cd /d E:\ai-coding-desk\host
py -3 inject.py 把登录改成 JWT
```

或主机已启动时：`POST /v1/inject` `{"text":"把登录改成 JWT","target":"cursor"}`

---

## 5. 剩余内存 / CPU 还能接什么

编译实测（未含长时间录音时）：片内 RAM **36%**（118 KB / 320 KB），Flash **23%**（1.5 MB / 6.5 MB），**8 MB PSRAM 几乎空着**。双核 240 MHz：LVGL + Wi-Fi + BLE HID 仍有余量。

### 现在就该接（占用量小、写代码每天用）

| 功能 | 资源 | 说明 |
|---|---|---|
| 板载麦 12 s PCM | PSRAM ~384 KB | 本文模式 A |
| IMU 摇一摇静音/取消录音 | I2C 已接 QMI8658 | 几乎 0 RAM |
| 超限蜂鸣（ES8311 短 beep） | 与录音互斥 | 90% 红灯之外再给耳朵 |
| TF 每日额度 CSV | 已有卡槽 | PaperColor 同款趋势 |
| 触屏 3 个常用 prompt | UI 一页 | 如 `fix tests` / `commit` / `explain` → 粘贴 |

### 第二期（有余量，但不要和录音抢 I2S）

| 功能 | 注意 |
|---|---|
| ESP-SR 唤醒词「小彩」 | Flash +200 KB，可；唤醒后仍走模式 A 录音，**不要**上完整小智双工 |
| USB 串口传 WAV | Wi-Fi 不行时的兜底；注意 CDC 493 B 分块 |
| Agent 等待时屏幕闪橙 + 灯 | 主机 `/v1/agent` 已有，差的是 Cursor/CC hook 去 POST |

### 不要接（会把主功能挤死）

- 固件里跑 Whisper / 本地 LLM  
- 同一固件混编完整小智（I2S 麦+喇叭全双工 + 另一套云端协议，和 PTT 录音抢总线）  
- 四家额度同屏、浏览器、摄像头  

片内 RAM 再吃到 70% 就停加功能。PSRAM 可以继续给音频和 UI 图。

---

## 6. 你明天的最小使用路径

1. 烧录固件，Windows 配对蓝牙 `Desk154`  
2. `py -3 host\desk_host.py`，复制 `sf_api_key.txt` + `zhipu_token.txt` 到 `host\secrets\`  
3. 设备连同一 Wi-Fi，或 `#CFGLINE|host_url=http://192.168.x.x:8787`  
4. 打开 Cursor，光标放在 Chat，Voice 页选 **板载麦 + Cursor**  
5. 按住 PLUS 说「把登录改成 JWT」→ 松手 → 字出现 → BOOT 发送  
6. 写 Claude Code 时切 **HID热键 + Claude**，按住 PLUS = 原声语音  

灯：说话中彩虹；Agent 忙蓝；等你确认橙闪；额度 ≥90% 红闪。
