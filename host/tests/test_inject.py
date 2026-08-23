from inject import (
    classify_focus,
    clean_transcript,
    press_enter,
    press_up,
    pwr_action,
    score_title,
    stop_allowed_for_title,
    stop_generation,
    handle_shake,
    undo_last_inject,
)
import time


def test_strips_sensevoice_tags():
    raw = "<|zh|><|NEUTRAL|><|Speech|><|withitn|>把登录改成 JWT"
    assert clean_transcript(raw) == "把登录改成 JWT"


def test_collapses_spaces_and_empty():
    assert clean_transcript("  foo   bar  ") == "foo bar"
    assert clean_transcript("") == ""
    assert clean_transcript("<|en|>") == ""


def test_score_prefers_cursor_agents():
    assert score_title("Cursor Agents", "cursor") > score_title("README.md — ai-coding-desk — Cursor", "cursor")
    assert score_title("Cursor Agents", "cursor") > score_title("Windows Terminal", "cursor")
    assert score_title("Windows Terminal", "claude") > 0
    assert score_title("", "cursor") == 0


def test_classify_cursor_app_vs_cli():
    assert classify_focus("Cursor Agents", "cursor.exe") == "cursor"
    assert classify_focus("README.md — ai-coding-desk — Cursor") == "cursor"
    assert classify_focus(r"E:\ai-coding-desk", "WindowsTerminal.exe") == "cli"
    assert classify_focus("随便一个路径", "windowsterminal.exe") == "cli"
    assert classify_focus("claude") == "cli"
    assert classify_focus("Windows Terminal") == "cli"
    assert classify_focus("微信", "wechat.exe") == "other"
    assert classify_focus("Google Chrome", "chrome.exe") == "other"


def test_stop_only_when_cursor_already_focused():
    assert stop_allowed_for_title("Cursor Agents")
    assert stop_allowed_for_title("README.md — ai-coding-desk — Cursor")
    assert not stop_allowed_for_title("微信")
    assert not stop_allowed_for_title("Google Chrome")
    assert not stop_allowed_for_title("WorkBuddy")
    assert not stop_allowed_for_title("")


def test_stop_generation_does_not_steal_focus(monkeypatch):
    stolen = []
    chords = []
    monkeypatch.setattr("inject.focus_target", lambda t: stolen.append(t) or True)
    monkeypatch.setattr("inject.focused_info", lambda: ("other", "微信", "wechat.exe"))
    monkeypatch.setattr("inject._chord", lambda *a: chords.append(a))
    monkeypatch.setattr("inject._send_vk", lambda *a, **k: 0)
    r = stop_generation("cursor")
    assert stolen == []
    assert chords == []
    assert r.get("skipped") is True


def test_stop_generation_sends_f24_and_cancel_chords(monkeypatch):
    chords = []
    vks = []
    monkeypatch.setattr("inject.focus_target", lambda t: (_ for _ in ()).throw(RuntimeError("no steal")))
    monkeypatch.setattr("inject.focused_info", lambda: ("cursor", "Cursor Agents", "cursor.exe"))
    monkeypatch.setattr("inject._attach_foreground", lambda fn: fn())
    monkeypatch.setattr("inject._chord", lambda *a: chords.append(a))
    monkeypatch.setattr("inject._send_vk", lambda vk, *a, **k: vks.append(vk) or 0)
    monkeypatch.setattr("inject._release_modifiers", lambda: None)
    r = stop_generation("cursor")
    assert r.get("skipped") is False
    assert vks == [0x87]  # F24
    assert len(chords) == 1
    assert chords[0] == (0x11, 0x10, 0x08)  # Ctrl+Shift+Backspace


def test_stop_cli_sends_ctrl_c_not_f24(monkeypatch):
    chords = []
    vks = []
    monkeypatch.setattr("inject.focused_info", lambda: ("cli", r"E:\ai-coding-desk", "windowsterminal.exe"))
    monkeypatch.setattr("inject._attach_foreground", lambda fn: fn())
    monkeypatch.setattr("inject._chord", lambda *a: chords.append(a))
    monkeypatch.setattr("inject._send_vk", lambda vk, *a, **k: vks.append(vk) or 0)
    monkeypatch.setattr("inject._release_modifiers", lambda: None)
    r = stop_generation("cursor")
    assert r.get("skipped") is False
    assert vks == []
    assert chords == [(0x11, 0x43)]  # Ctrl+C


def test_press_enter_skips_other_apps(monkeypatch):
    sent = []
    monkeypatch.setattr("inject.focused_info", lambda: ("other", "微信", "wechat.exe"))
    monkeypatch.setattr("inject._send_vk", lambda vk, *a, **k: sent.append(vk) or 0)
    r = press_enter()
    assert r.get("skipped") is True
    assert sent == []


def test_press_enter_cli_path_title(monkeypatch):
    sent = []
    monkeypatch.setattr("inject._last_stop_at", 0.0)
    monkeypatch.setattr("inject._last_stop_kind", "")
    monkeypatch.setattr("inject.focused_info", lambda: ("cli", r"E:\ai-coding-desk", "windowsterminal.exe"))
    monkeypatch.setattr("inject._attach_foreground", lambda fn: fn())
    monkeypatch.setattr("inject._release_modifiers", lambda: None)
    monkeypatch.setattr("inject._send_vk", lambda vk, *a, **k: sent.append(vk) or 0)
    r = press_enter()
    assert r.get("skipped") is False
    assert r.get("after_stop") is False
    assert sent == [0x0D]


def test_press_enter_cli_after_stop_nudges_input(monkeypatch):
    sent = []
    monkeypatch.setattr("inject._last_stop_at", time.time())
    monkeypatch.setattr("inject._last_stop_kind", "cli")
    monkeypatch.setattr("inject.focused_info", lambda: ("cli", r"E:\ai-coding-desk", "windowsterminal.exe"))
    monkeypatch.setattr("inject._attach_foreground", lambda fn: fn())
    monkeypatch.setattr("inject._release_modifiers", lambda: None)
    monkeypatch.setattr("inject._send_vk", lambda vk, *a, **k: sent.append(vk) or 0)
    r = press_enter()
    assert r.get("after_stop") is True
    assert sent == [0x20, 0x08, 0x0D]  # space, backspace, enter


def test_press_enter_cursor_after_stop_is_ctrl_enter(monkeypatch):
    chords = []
    sent = []
    monkeypatch.setattr("inject._last_stop_at", time.time())
    monkeypatch.setattr("inject._last_stop_kind", "cursor")
    monkeypatch.setattr("inject.focused_info", lambda: ("cursor", "Cursor Agents", "cursor.exe"))
    monkeypatch.setattr("inject._attach_foreground", lambda fn: fn())
    monkeypatch.setattr("inject._release_modifiers", lambda: None)
    monkeypatch.setattr("inject._chord", lambda *a: chords.append(a))
    monkeypatch.setattr("inject._send_vk", lambda vk, *a, **k: sent.append(vk) or 0)
    r = press_enter()
    assert r.get("after_stop") is True
    assert sent == []
    assert chords == [(0x11, 0x0D)]  # Ctrl+Enter


def test_press_up_cli(monkeypatch):
    sent = []
    monkeypatch.setattr("inject.focused_info", lambda: ("cli", r"E:\proj", "windowsterminal.exe"))
    monkeypatch.setattr("inject._attach_foreground", lambda fn: fn())
    monkeypatch.setattr("inject._release_modifiers", lambda: None)
    monkeypatch.setattr("inject._send_vk", lambda vk, *a, **k: sent.append(vk) or 0)
    r = press_up()
    assert r.get("skipped") is False
    assert sent == [0x26]


def test_shake_running_is_stop(monkeypatch):
    monkeypatch.setattr("inject.stop_generation", lambda target="auto": {"ok": True, "skipped": False, "kind": "cursor"})
    monkeypatch.setattr("inject.undo_last_inject", lambda: {"ok": True, "skipped": False, "kind": "cursor"})
    r = handle_shake(running=True, agent_state="idle")
    assert r["shake"] == "stop"


def test_shake_agent_working_is_stop(monkeypatch):
    monkeypatch.setattr("inject.stop_generation", lambda target="auto": {"ok": True, "skipped": False})
    monkeypatch.setattr("inject.undo_last_inject", lambda: {"ok": True, "skipped": False})
    r = handle_shake(running=False, agent_state="working")
    assert r["shake"] == "stop"


def test_shake_idle_is_undo(monkeypatch):
    monkeypatch.setattr("inject.stop_generation", lambda target="auto": {"ok": True, "skipped": False})
    monkeypatch.setattr("inject.undo_last_inject", lambda: {"ok": True, "skipped": False, "kind": "cli"})
    r = handle_shake(running=False, agent_state="idle")
    assert r["shake"] == "undo"


def test_undo_empty_sends_ctrl_z(monkeypatch):
    import inject as inj
    inj._last_inject = ""
    chords = []
    monkeypatch.setattr("inject.focused_info", lambda: ("cursor", "Cursor Agents", "cursor.exe"))
    monkeypatch.setattr("inject._attach_foreground", lambda fn: fn())
    monkeypatch.setattr("inject._release_modifiers", lambda: None)
    monkeypatch.setattr("inject._chord", lambda *vks: chords.append(vks))
    r = undo_last_inject()
    assert r.get("skipped") is False
    assert r.get("ctrl_z") is True
    assert chords == [(0x11, 0x5A)]


def test_undo_backspaces_last_inject(monkeypatch):
    import inject as inj
    inj._last_inject = "ab"
    sent = []
    monkeypatch.setattr("inject.focused_info", lambda: ("cli", "x", "windowsterminal.exe"))
    monkeypatch.setattr("inject._attach_foreground", lambda fn: fn())
    monkeypatch.setattr("inject._release_modifiers", lambda: None)
    monkeypatch.setattr("inject._send_vk", lambda vk, *a, **k: sent.append(vk) or 0)
    r = undo_last_inject()
    assert r.get("skipped") is False
    assert sent == [0x08, 0x08]
    assert inj._last_inject == ""


def test_pwr_cursor_running_is_stop():
    assert pwr_action("Cursor Agents", "working") == "stop"
    assert pwr_action("Cursor Agents", "idle", running=True) == "stop"


def test_pwr_idle_coding_is_up():
    assert pwr_action("Cursor Agents", "idle") == "up"
    assert pwr_action(r"E:\ai-coding-desk", exe="WindowsTerminal.exe") == "up"
    assert pwr_action("claude") == "up"


def test_pwr_other_app_is_sync():
    assert pwr_action("微信", "working") == "sync"
    assert pwr_action("Google Chrome") == "sync"


def test_inject_stays_on_focused_coding_window(monkeypatch):
    import inject as inj

    remembered = []
    monkeypatch.setattr(inj, "focused_info", lambda: ("cursor", "Cursor Agents", "cursor.exe"))
    monkeypatch.setattr(inj.user32, "GetForegroundWindow", lambda: 111)
    monkeypatch.setattr(inj, "remember_coding_hwnd", lambda hwnd=None: remembered.append(hwnd))
    monkeypatch.setattr(inj, "focus_coding_window", lambda: (_ for _ in ()).throw(RuntimeError("no steal")))
    monkeypatch.setattr(inj, "foreground_title", lambda: "Cursor Agents")
    monkeypatch.setattr(inj, "type_into_focus", lambda text, press_enter=False: 4)
    r = inj.inject_transcript("把登录改成 JWT", target="claude")
    assert remembered == [111]
    assert r["ok"] is True
    assert r["target"] == "auto"
    assert r["kind"] == "cursor"
    assert r["method"] == "sendinput"
    assert r["text"] == "把登录改成 JWT"


def test_inject_restores_last_coding_window_when_other_app_focused(monkeypatch):
    import inject as inj

    stolen = []
    monkeypatch.setattr(inj, "focused_info", lambda: ("other", "微信", "wechat.exe"))
    monkeypatch.setattr(inj.user32, "GetForegroundWindow", lambda: 222)
    monkeypatch.setattr(inj, "remember_coding_hwnd", lambda hwnd=None: None)
    monkeypatch.setattr(inj, "focus_coding_window", lambda: stolen.append("coding") or True)
    monkeypatch.setattr(inj, "foreground_title", lambda: "Cursor Agents")
    monkeypatch.setattr(inj, "type_into_focus", lambda text, press_enter=False: 3)
    monkeypatch.setattr(inj.time, "sleep", lambda *_a, **_k: None)
    r = inj.inject_transcript("hello", target="cursor")
    assert stolen == ["coding"]
    assert r["ok"] is True
    assert r["focused"] is True
    assert r["target"] == "auto"
    assert r["kind"] == "cursor"


def test_pick_coding_hwnd_prefers_last_used(monkeypatch):
    import inject as inj

    inj._last_coding_hwnd = 42
    monkeypatch.setattr(inj, "_is_coding_hwnd", lambda hwnd: hwnd == 42)
    monkeypatch.setattr(inj, "_enum_windows", lambda: [(99, "Cursor Agents")])
    assert inj._pick_coding_hwnd() == 42
