# -*- coding: utf-8 -*-
"""First-run GUI for buyers: plug USB → optional Wi-Fi → 一键配对."""
from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from desk_pair import (  # noqa: E402
    DEFAULT_HOST_KEY,
    find_desk_port,
    local_host_url,
    probe_status,
    push_config,
)
from paths import (  # noqa: E402
    autostart_off_flag,
    launch_command,
    paired_flag,
    secrets_dir,
    startup_bat,
)


def apply_autostart(enabled: bool) -> None:
    flag = autostart_off_flag()
    bat = startup_bat()
    if not enabled:
        flag.write_text("1", encoding="utf-8")
        try:
            if bat.is_file():
                bat.unlink()
        except OSError:
            pass
        return
    if flag.is_file():
        flag.unlink()
    cwd, cmd = launch_command()
    body = "@echo off\r\nset PYTHONUNBUFFERED=1\r\ncd /d \"%s\"\r\n%s\r\n" % (cwd, cmd)
    try:
        bat.parent.mkdir(parents=True, exist_ok=True)
        bat.write_text(body, encoding="utf-8")
    except OSError:
        pass


def save_sf_key(key: str) -> None:
    key = (key or "").strip()
    path = secrets_dir() / "sf_api_key.txt"
    if not key:
        return
    path.write_text(key, encoding="utf-8")


def pair_now(ssid: str, password: str, host_key: str | None = None) -> tuple[bool, str]:
    """Push PC address (+ optional Wi-Fi) to the puck. Returns (ok, message)."""
    port = find_desk_port(env_port=os.environ.get("DESK_SERIAL"))
    if not port:
        return False, "没找到设备。请用盒子里的数据线插上电脑，等 5 秒再点配对。不要用「仅充电」的线。"
    url = local_host_url()
    key = (host_key or os.environ.get("DESK_HOST_KEY") or DEFAULT_HOST_KEY).strip()
    try:
        push_config(
            port,
            url,
            key,
            ssid=(ssid or "").strip(),
            password=password or "",
            extra_wifi=[],
        )
    except Exception as exc:
        return False, "配对失败：%s" % exc
    extra = ""
    try:
        raw = probe_status(port)
        if raw.strip():
            extra = " 设备已应答。"
    except Exception:
        extra = " 配置已写入，稍后会自己连上。"
    paired_flag().write_text(url + "\n", encoding="utf-8")
    return True, "配对成功。电脑地址 %s 已写入设备。%s" % (url, extra)


def run_wizard() -> bool:
    """Blocking GUI. True if paired (or already skipped with existing flag)."""
    result = {"ok": False}

    win = tk.Tk()
    win.title("Desk154 设置")
    win.geometry("520x560")
    win.resizable(False, False)

    pad = {"padx": 18, "pady": 6}
    ttk.Label(win, text="Desk154 电脑设置", font=("Microsoft YaHei UI", 16, "bold")).pack(anchor="w", **pad)
    ttk.Label(
        win,
        text="设备出厂已刷好。你只需要：插上 USB → 可选填家里 Wi-Fi → 一键配对。",
        wraplength=480,
        font=("Microsoft YaHei UI", 10),
    ).pack(anchor="w", padx=18, pady=(0, 8))

    box = ttk.LabelFrame(win, text="1. 设备")
    box.pack(fill="x", padx=18, pady=6)
    ttk.Label(box, text="用盒子里的 USB 线把 Desk154 插到这台电脑（不要用仅充电线）。", wraplength=460).pack(
        anchor="w", padx=10, pady=8
    )

    wifi = ttk.LabelFrame(win, text="2. 家里 Wi-Fi（可选，填了就可以拔掉线用）")
    wifi.pack(fill="x", padx=18, pady=6)
    ttk.Label(wifi, text="名称").grid(row=0, column=0, sticky="e", padx=8, pady=6)
    ssid_var = tk.StringVar()
    ttk.Entry(wifi, textvariable=ssid_var, width=36).grid(row=0, column=1, padx=8, pady=6)
    ttk.Label(wifi, text="密码").grid(row=1, column=0, sticky="e", padx=8, pady=6)
    pass_var = tk.StringVar()
    ttk.Entry(wifi, textvariable=pass_var, width=36, show="*").grid(row=1, column=1, padx=8, pady=6)

    voice = ttk.LabelFrame(win, text="3. 语音钥匙（可选，不填也能看额度）")
    voice.pack(fill="x", padx=18, pady=6)
    ttk.Label(voice, text="SiliconFlow API Key，说话转文字用。没有就先空着。", wraplength=440).grid(
        row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(6, 0)
    )
    sf_var = tk.StringVar()
    ttk.Entry(voice, textvariable=sf_var, width=44).grid(row=1, column=0, columnspan=2, padx=8, pady=8)

    auto_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(win, text="开机自动启动（推荐，插上设备就能用）", variable=auto_var).pack(anchor="w", padx=18, pady=8)

    status = tk.StringVar(value="插好线后点下面的按钮。")
    ttk.Label(win, textvariable=status, wraplength=480, foreground="#334155").pack(anchor="w", padx=18)

    btn = ttk.Button(win, text="一键配对")

    def on_pair() -> None:
        btn.state(["disabled"])
        status.set("正在找设备、写入电脑地址…")
        save_sf_key(sf_var.get())
        apply_autostart(bool(auto_var.get()))

        def work() -> None:
            ok, msg = pair_now(ssid_var.get(), pass_var.get())
            def done() -> None:
                status.set(msg)
                btn.state(["!disabled"])
                if ok:
                    result["ok"] = True
                    messagebox.showinfo("Desk154", msg + "\n\n接下来看右下角托盘图标。额度页连晃三下可以抽签。")
                    win.destroy()
                else:
                    messagebox.showerror("Desk154", msg)

            win.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    btn.configure(command=on_pair)
    btn.pack(pady=12, ipadx=18, ipady=6)

    ttk.Label(win, text="以后要重新配对：托盘图标 → 重新配对。", foreground="#64748b").pack(anchor="w", padx=18)

    win.protocol("WM_DELETE_WINDOW", win.destroy)
    win.mainloop()
    return bool(result["ok"])


if __name__ == "__main__":
    sys.exit(0 if run_wizard() else 1)
