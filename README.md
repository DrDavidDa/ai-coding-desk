<p align="center">
  <img src="docs/assets/desk154-banner.png" alt="Desk154 — AI Coding Desk" width="100%" />
</p>

<h1 align="center">别再为额度切网页了</h1>

<p align="center">
  <b>一块 1.54″ 触屏，把 Claude / Cursor / Codex / GLM 的剩余算力钉在桌上。</b><br/>
  按住说话 → 字直接打进 Cursor。密钥永远不进固件。
</p>

<p align="center">
  <a href="https://drdavidda.github.io/ai-coding-desk/desk154-lab.html"><strong>⚡ 0 硬件 · 实验版高级 UI</strong></a>
  &nbsp;·&nbsp;
  <a href="https://github.com/DrDavidDa/ai-coding-desk/stargazers">⭐ Star</a>
  &nbsp;·&nbsp;
  <a href="#-5-分钟上手">🚀 刷机</a>
  &nbsp;·&nbsp;
  <a href="docs/ops-landing.md">📖 怎么用</a>
</p>

<p align="center">
  <img alt="license" src="https://img.shields.io/badge/license-see_repo-lightgrey" />
  <img alt="platform" src="https://img.shields.io/badge/ESP32--S3-1.54%22_LCD-orange" />
  <img alt="stack" src="https://img.shields.io/badge/LVGL_8_+_Python_Host-black" />
  <img alt="demo" src="https://img.shields.io/badge/live_demo-GitHub_Pages-blue" />
</p>

---

## 先抄这段去发（可直接转）

> 我把 Claude / Cursor / Codex 的额度做成了一块桌上的小屏。  
> Logo 本身就是剩余额度环。按住说话，字打进 Cursor。  
> Cookie 不进板子。0 硬件也能玩原型：  
> https://drdavidda.github.io/ai-coding-desk/desk154-lab.html  
> Repo：https://github.com/DrDavidDa/ai-coding-desk

发完回来点个 Star —— 你的转发是这个项目活下去的理由。

---

## 30 秒懂它在骂谁

| 你现在这样 | Desk154 |
|---|---|
| 打开 4 个网页看额度 | **抬头一眼**就知道谁快没了 |
| 戴耳机找麦、切窗口说话 | **板载双麦**，按住就说 |
| 买个无屏宏键盘几百刀 | **微雪 1.54″ 彩屏**，自己刷，可改 |
| Token 写进固件被抄走 | **Secrets 只在 Windows Host** |

市售「AI 编程麦克垫」贵、无屏、闭源。  
Desk154：**开源 · 有屏 · 额度可见 · 语音可进对话框**。

---

## 一屏看懂（转发友好）

```text
┌──────── Desk154 ────────┐         ┌──── Windows Host ────┐
│ 240×240 触屏 USAGE/PLAN │ ◄─JSON─ │ 各家 Coding Plan 采集 │
│ 麦 → WAV                │ ─WAV──► │ SenseVoice 转写      │
│ 发送/取消/讲话 · BLE HID│ ─HID──► │ 字打进当前输入框     │
└─────────────────────────┘         └──────────────────────┘
         密钥 / Cookie / JWT  ←绝不进板子
```

**真机手感**
- 顶栏：**发送 | 取消 | 讲话**（不是 BOOT/PWR 英文）
- 两大圆：**麦克风 / 禁止**；录音秒数 + 脉冲
- USAGE：Logo 就是额度；点进 **5H / 7D / 1M**（Cursor = **AUTO / API**）
- Claude Code 走 DeepSeek：仍是 **Claude Code** 页，脚注 `YUAN x.xx`

---

## 🔥 先玩原型（今天就能传播）

不用板子。打开就滑、就点麦、就进 PLAN：

### 👉 [desk154-lab.html · 实验版高级 UI](https://drdavidda.github.io/ai-coding-desk/desk154-lab.html)

（[旧暖色原型](https://drdavidda.github.io/ai-coding-desk/desk154-live.html) 仍可对比。）

玩完把链接丢群里 / 小红书 / V2EX / Twitter。  
「截图 + 上面那段文案」= 完整传播包。

---

## ⚡ 5 分钟上手

<details>
<summary><b>1）Windows Host</b></summary>

```bat
cd host
py -3 -m pip install -r requirements.txt
set DESK_NO_TRAY=1
py -3 -u desk_host.py
```

`http://127.0.0.1:8787` · 密钥放 `host/secrets/`（已 gitignore）
</details>

<details>
<summary><b>2）固件 · Waveshare ESP32-S3-Touch-LCD-1.54（SKU 33869）</b></summary>

```bat
cd firmware
pio run -e waveshare_lcd_154
```

烧录口通常 COM8→1200 触摸→COM7，**DIO 16MB**。详见 [docs/handoff.md](docs/handoff.md)。  
**禁止**误刷其它 ESP。
</details>

<details>
<summary><b>3）零硬件</b></summary>

只开 [Lab Demo](https://drdavidda.github.io/ai-coding-desk/desk154-lab.html)。可与本机 Host 同步额度。
</details>

---

## 仓库地图

```
firmware/   ESP32 · LVGL · 触屏 / 麦 / 三键 / BLE
host/       额度采集 · SenseVoice · 注入
docs/       原型 · 硬件 · 落地用法
chrome-extension/  Cursor 辅助（可选）
```

---

## 安全一句话

**板子只显示数字。Token 死在 Host。**

---

## 硬件

Waveshare **ESP32-S3-Touch-LCD-1.54** · SKU **33869**  
[引脚与 BOM](docs/hardware.md) · [坐下怎么用](docs/ops-landing.md)

---

## 一起把它打爆

| 你能做的 | 为什么重要 |
|---|---|
| ⭐ Star | 排序与曝光 |
| 转发 Demo 链接 | 0 门槛种草 |
| Issue / PR 新厂商额度 | 生态变厚 |
| 晒桌面实拍 | 内容燃料 |

<p align="center">
  <b>桌上多一盏额度灯，少切一次网页。</b><br/><br/>
  <a href="https://github.com/DrDavidDa/ai-coding-desk">⭐ Star this repo</a>
  &nbsp;·&nbsp;
  <a href="https://drdavidda.github.io/ai-coding-desk/desk154-lab.html">▶ Play the lab demo</a>
</p>
