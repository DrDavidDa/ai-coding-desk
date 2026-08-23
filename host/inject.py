"""Type transcribed text into the focused coding dialog.

Primary path: SendInput KEYEVENTF_UNICODE (Cursor Electron, Windows Terminal,
Win32 edits). Clipboard Ctrl+V is fallback only, with clipboard restore.
Does not steal focus by default — click the chat box, then PTT.
"""
from __future__ import annotations

import ctypes
import re
import time
from ctypes import wintypes

SENSEVOICE_TAG = re.compile(r"<\|[^>]+\|>")
SPACE_RUN = re.compile(r"[ \t]{2,}")

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008
VK_RETURN = 0x0D
VK_UP = 0x26
VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_MENU = 0x12
VK_ESCAPE = 0x1B
VK_BACK = 0x08
VK_SPACE = 0x20
VK_C = 0x43
VK_Z = 0x5A
VK_F24 = 0x87
VK_LSHIFT = 0xA0
VK_RSHIFT = 0xA1
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_LMENU = 0xA4
VK_RMENU = 0xA5
VK_V = 0x56
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
SW_RESTORE = 9
STOP_REPLAY_SEC = 180.0
_last_stop_at = 0.0
_last_stop_kind = ""
_last_inject = ""
_session_run = False
_last_coding_hwnd = None

TARGET_TITLES = {
    "cursor": ("cursor",),
    "claude": ("claude", "windows terminal", "wt -", "ubuntu", "powershell"),
    "codex": ("codex", "windows terminal", "wt -", "ubuntu", "powershell"),
}

CURSOR_EXES = frozenset({"cursor.exe"})
CLI_EXES = frozenset({
    "windowsterminal.exe",
    "wt.exe",
    "conhost.exe",
    "openconsole.exe",
    "wezterm-gui.exe",
    "wezterm.exe",
    "alacritty.exe",
    "powershell.exe",
    "pwsh.exe",
    "cmd.exe",
    "claude.exe",
    "codex.exe",
})
CLI_TITLE_NEEDLES = (
    "claude",
    "codex",
    "windows terminal",
    "wt -",
    "ubuntu",
    "debian",
    "powershell",
    "wsl",
    "wezterm",
)


def clean_transcript(text: str) -> str:
    if not text:
        return ""
    text = SENSEVOICE_TAG.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = SPACE_RUN.sub(" ", text).strip()
    return text


class MOUSEINPUT(ctypes.Structure):
    _fields_ = (
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    )


class KEYBDINPUT(ctypes.Structure):
    _fields_ = (
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    )


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = (
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    )


class _INPUTunion(ctypes.Union):
    _fields_ = (("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT))


class INPUT(ctypes.Structure):
    _fields_ = (("type", wintypes.DWORD), ("union", _INPUTunion))


user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
user32.SendInput.restype = wintypes.UINT
user32.MapVirtualKeyW.argtypes = (wintypes.UINT, wintypes.UINT)
user32.MapVirtualKeyW.restype = wintypes.UINT
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowTextW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
user32.GetWindowTextW.restype = ctypes.c_int
user32.SetForegroundWindow.argtypes = (wintypes.HWND,)
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.ShowWindow.argtypes = (wintypes.HWND, ctypes.c_int)
user32.ShowWindow.restype = wintypes.BOOL
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = (WNDENUMPROC, wintypes.LPARAM)
user32.EnumWindows.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = (wintypes.HWND,)
user32.IsWindowVisible.restype = wintypes.BOOL
user32.IsWindow.argtypes = (wintypes.HWND,)
user32.IsWindow.restype = wintypes.BOOL
user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.AttachThreadInput.argtypes = (wintypes.DWORD, wintypes.DWORD, wintypes.BOOL)
user32.AttachThreadInput.restype = wintypes.BOOL
user32.BringWindowToTop.argtypes = (wintypes.HWND,)
user32.BringWindowToTop.restype = wintypes.BOOL
user32.SwitchToThisWindow.argtypes = (wintypes.HWND, wintypes.BOOL)
user32.SwitchToThisWindow.restype = None
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = (
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
)
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
kernel32.CloseHandle.restype = wintypes.BOOL
user32.OpenClipboard.argtypes = (wintypes.HWND,)
user32.OpenClipboard.restype = wintypes.BOOL
user32.CloseClipboard.restype = wintypes.BOOL
user32.EmptyClipboard.restype = wintypes.BOOL
user32.GetClipboardData.argtypes = (wintypes.UINT,)
user32.GetClipboardData.restype = wintypes.HANDLE
user32.SetClipboardData.argtypes = (wintypes.UINT, wintypes.HANDLE)
user32.SetClipboardData.restype = wintypes.HANDLE
kernel32.GlobalAlloc.argtypes = (wintypes.UINT, ctypes.c_size_t)
kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
kernel32.GlobalLock.argtypes = (wintypes.HGLOBAL,)
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = (wintypes.HGLOBAL,)
kernel32.GlobalUnlock.restype = wintypes.BOOL
kernel32.GlobalSize.argtypes = (wintypes.HGLOBAL,)
kernel32.GlobalSize.restype = ctypes.c_size_t


def foreground_title() -> str:
    hwnd = user32.GetForegroundWindow()
    buf = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value or ""


def _enum_windows():
    hits = []

    @WNDENUMPROC
    def cb(hwnd, _lp):
        if not user32.IsWindowVisible(hwnd):
            return True
        buf = ctypes.create_unicode_buffer(512)
        if user32.GetWindowTextW(hwnd, buf, 512) and buf.value:
            hits.append((hwnd, buf.value))
        return True

    user32.EnumWindows(cb, 0)
    return hits


def score_title(title: str, target: str) -> int:
    t = (title or "").lower()
    if not t:
        return 0
    if target == "cursor":
        if "cursor agents" in t:
            return 100
        if "cursor" in t:
            return 80
        return 0
    needles = TARGET_TITLES.get(target, ())
    return 70 if any(n in t for n in needles) else 0


def classify_focus(title: str = "", exe: str = "") -> str:
    """What the puck should drive: Cursor app, a coding CLI, or ignore.

    Process name wins for Windows Terminal — its window title is often just
    a folder path, which used to make BOOT Enter skip.
    Cursor.exe stays Cursor even if a `claude` tab is inside it.
    """
    exe_l = (exe or "").replace("/", "\\").rsplit("\\", 1)[-1].lower()
    t = (title or "").lower()
    if exe_l in CURSOR_EXES or "cursor" in t:
        return "cursor"
    if exe_l in CLI_EXES:
        return "cli"
    if any(n in t for n in CLI_TITLE_NEEDLES):
        return "cli"
    return "other"


def focused_info() -> tuple[str, str, str]:
    hwnd = user32.GetForegroundWindow()
    buf = ctypes.create_unicode_buffer(512)
    title = ""
    if hwnd:
        user32.GetWindowTextW(hwnd, buf, 512)
        title = buf.value or ""
    exe = _process_basename(hwnd) if hwnd else ""
    return classify_focus(title, exe), title, exe


def _process_basename(hwnd) -> str:
    pid = wintypes.DWORD(0)
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return ""
    handle = kernel32.OpenProcess(0x1000, False, pid.value)
    if not handle:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(260)
        size = wintypes.DWORD(260)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            name = buf.value.replace("/", "\\")
            return name.rsplit("\\", 1)[-1].lower()
        return ""
    finally:
        kernel32.CloseHandle(handle)


def _hwnd_title(hwnd) -> str:
    if not hwnd:
        return ""
    buf = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value or ""


def _is_coding_hwnd(hwnd) -> bool:
    if not hwnd or not user32.IsWindow(hwnd):
        return False
    kind = classify_focus(_hwnd_title(hwnd), _process_basename(hwnd))
    return kind in ("cursor", "cli")


def remember_coding_hwnd(hwnd=None) -> None:
    global _last_coding_hwnd
    hwnd = hwnd or user32.GetForegroundWindow()
    if _is_coding_hwnd(hwnd):
        _last_coding_hwnd = hwnd


def _pick_hwnd(target: str):
    best = None
    best_score = 0
    fg = user32.GetForegroundWindow()
    for hwnd, name in _enum_windows():
        score = score_title(name, target)
        if target == "cursor" and _process_basename(hwnd) == "cursor.exe":
            score = max(score, 60)
        if hwnd == fg:
            score += 5
        if score > best_score:
            best_score = score
            best = hwnd
    return best if best_score > 0 else None


def _pick_coding_hwnd():
    """Current / last coding window. Prefer last used, then Cursor, then any CLI."""
    global _last_coding_hwnd
    if _is_coding_hwnd(_last_coding_hwnd):
        return _last_coding_hwnd
    fg = user32.GetForegroundWindow()
    best = None
    best_score = 0
    for hwnd, name in _enum_windows():
        kind = classify_focus(name, _process_basename(hwnd))
        if kind not in ("cursor", "cli"):
            continue
        score = 80 if kind == "cursor" else 50
        if hwnd == fg:
            score += 5
        if score > best_score:
            best_score = score
            best = hwnd
    if best:
        _last_coding_hwnd = best
    return best


def focus_hwnd(hwnd) -> bool:
    if not hwnd or not user32.IsWindow(hwnd):
        return False
    user32.ShowWindow(hwnd, SW_RESTORE)
    if user32.GetForegroundWindow() == hwnd:
        remember_coding_hwnd(hwnd)
        return True
    fg = user32.GetForegroundWindow()
    pid = wintypes.DWORD(0)
    fg_tid = user32.GetWindowThreadProcessId(fg, ctypes.byref(pid))
    cur = kernel32.GetCurrentThreadId()
    if fg_tid:
        user32.AttachThreadInput(cur, fg_tid, True)
    extra = ctypes.c_ulong(0)
    alt_down = INPUT(type=INPUT_KEYBOARD)
    alt_down.union.ki = KEYBDINPUT(VK_MENU, 0, 0, 0, ctypes.pointer(extra))
    _send_one(alt_down)
    user32.BringWindowToTop(hwnd)
    user32.SwitchToThisWindow(hwnd, True)
    user32.SetForegroundWindow(hwnd)
    alt_up = INPUT(type=INPUT_KEYBOARD)
    alt_up.union.ki = KEYBDINPUT(VK_MENU, 0, KEYEVENTF_KEYUP, 0, ctypes.pointer(extra))
    _send_one(alt_up)
    if fg_tid:
        user32.AttachThreadInput(cur, fg_tid, False)
    time.sleep(0.08)
    ok = user32.GetForegroundWindow() == hwnd
    if ok:
        remember_coding_hwnd(hwnd)
    return ok


def focus_target(target: str) -> bool:
    hwnd = _pick_hwnd(target)
    if not hwnd:
        return False
    return focus_hwnd(hwnd)


def focus_coding_window() -> bool:
    hwnd = _pick_coding_hwnd()
    if not hwnd:
        return False
    return focus_hwnd(hwnd)


def _host_log(*parts) -> None:
    msg = " ".join(str(p) for p in parts)
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))


def stop_allowed_for_title(title: str, target: str = "cursor") -> bool:
    """Stop keys only if that app is already in front. Never Alt-Tab to it."""
    return score_title(title or "", target) > 0


def _scan(vk: int) -> int:
    # F24 has no standard OEM scancode; MapVirtualKey often returns 0 and
    # Electron then ignores the event. 0x76 is the AT-set F24 scan.
    if vk == VK_F24:
        return 0x76
    return int(user32.MapVirtualKeyW(vk, 0) or 0)


def _vk_down(vk: int) -> int:
    extra = ctypes.c_ulong(0)
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.union.ki = KEYBDINPUT(vk, _scan(vk), 0, 0, ctypes.pointer(extra))
    return _send_one(inp)


def _vk_up(vk: int) -> int:
    extra = ctypes.c_ulong(0)
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.union.ki = KEYBDINPUT(vk, _scan(vk), KEYEVENTF_KEYUP, 0, ctypes.pointer(extra))
    return _send_one(inp)


def _attach_foreground(fn):
    """SendInput into the already-focused window without Alt-Tab."""
    fg = user32.GetForegroundWindow()
    pid = wintypes.DWORD(0)
    fg_tid = user32.GetWindowThreadProcessId(fg, ctypes.byref(pid))
    cur = kernel32.GetCurrentThreadId()
    attached = False
    if fg_tid and fg_tid != cur:
        attached = bool(user32.AttachThreadInput(cur, fg_tid, True))
    try:
        return fn()
    finally:
        if attached:
            user32.AttachThreadInput(cur, fg_tid, False)


def _chord(*vks: int) -> None:
    for v in vks:
        _vk_down(v)
    time.sleep(0.05)
    for v in reversed(vks):
        _vk_up(v)


def _release_modifiers() -> None:
    """Stop chords can leave Ctrl/Shift/Alt down; then BOOT Enter becomes Ctrl+Enter."""
    for vk in (
        VK_F24,
        VK_ESCAPE,
        VK_BACK,
        VK_CONTROL,
        VK_LCONTROL,
        VK_RCONTROL,
        VK_SHIFT,
        VK_LSHIFT,
        VK_RSHIFT,
        VK_MENU,
        VK_LMENU,
        VK_RMENU,
    ):
        _vk_up(vk)


def stop_generation(target: str = "auto") -> dict:
    """Cancel a running agent in the already-focused coding window.

    Cursor app: F24 + Ctrl+Shift+Backspace (composer.cancelComposerStep).
    CLI (Windows Terminal / claude): Ctrl+C.
    Do not steal focus. Do not send Esc — leftover Esc unfocuses Cursor chat.
    """
    kind, fg, exe = focused_info()
    if target in ("cursor", "claude", "codex") and kind not in ("cursor", "cli"):
        _host_log("[host] stop skip, not", target, "kind", kind, "exe", exe, "fg", fg)
        return {"ok": False, "skipped": True, "kind": kind, "exe": exe, "fg": fg}
    if kind not in ("cursor", "cli"):
        _host_log("[host] stop skip kind", kind, "exe", exe, "fg", fg)
        return {"ok": False, "skipped": True, "kind": kind, "exe": exe, "fg": fg}

    def fire():
        try:
            if kind == "cli":
                _chord(VK_CONTROL, VK_C)
            else:
                _send_vk(VK_F24)
                time.sleep(0.05)
                _chord(VK_CONTROL, VK_SHIFT, VK_BACK)
        finally:
            _release_modifiers()

    _attach_foreground(fire)
    global _last_stop_at, _last_stop_kind, _session_run
    _last_stop_at = time.time()
    _last_stop_kind = kind
    _session_run = False
    _host_log("[host] stop", kind, "exe", exe, "fg", fg)
    return {"ok": True, "skipped": False, "kind": kind, "exe": exe, "fg": fg}


def pwr_action(
    title: str,
    agent_state: str = "",
    target: str = "cursor",
    exe: str = "",
    running: bool = False,
) -> str:
    """PWR: Stop if a run is in flight. Idle coding window: Up. Other apps: sync."""
    kind = classify_focus(title, exe)
    if kind == "other":
        return "sync"
    if running or agent_state in ("working", "talk", "waiting"):
        return "stop"
    return "up"


def _enter_after_stop(kind: str) -> bool:
    return bool(
        _last_stop_kind == kind
        and _last_stop_at
        and (time.time() - _last_stop_at) < STOP_REPLAY_SEC
    )


def press_enter() -> dict:
    """BOOT Enter into the already-focused Cursor app or coding CLI.

    After Stop, the prompt is restored but Enter is often dead: Claude Code
    TUI is not armed, Cursor composer treats Enter as newline. Nudge / Ctrl+Enter.
    """
    kind, fg, exe = focused_info()
    if kind not in ("cursor", "cli"):
        _host_log("[host] enter skip kind", kind, "exe", exe, "fg", fg)
        return {"ok": False, "skipped": True, "kind": kind, "exe": exe, "fg": fg}
    after_stop = _enter_after_stop(kind)

    def fire():
        try:
            _release_modifiers()
            time.sleep(0.04)
            if kind == "cli" and after_stop:
                _send_vk(VK_SPACE)
                time.sleep(0.04)
                _send_vk(VK_BACK)
                time.sleep(0.04)
                _send_vk(VK_RETURN)
            elif kind == "cursor" and after_stop:
                _chord(VK_CONTROL, VK_RETURN)
            else:
                _send_vk(VK_RETURN)
        finally:
            _release_modifiers()

    _attach_foreground(fire)
    global _session_run
    _session_run = True
    _host_log("[host] enter", kind, "after_stop", int(after_stop), "exe", exe, "fg", fg)
    return {"ok": True, "skipped": False, "kind": kind, "exe": exe, "after_stop": after_stop, "fg": fg}


def session_running() -> bool:
    return bool(_session_run)


def press_up() -> dict:
    """Idle PWR: previous prompt / caret up. Not Stop, not n."""
    kind, fg, exe = focused_info()
    if kind not in ("cursor", "cli"):
        _host_log("[host] up skip kind", kind, "exe", exe, "fg", fg)
        return {"ok": False, "skipped": True, "kind": kind, "exe": exe, "fg": fg}

    def fire():
        try:
            _release_modifiers()
            _send_vk(VK_UP)
        finally:
            _release_modifiers()

    _attach_foreground(fire)
    _host_log("[host] up", kind, "exe", exe, "fg", fg)
    return {"ok": True, "skipped": False, "kind": kind, "exe": exe, "fg": fg}


def handle_shake(running: bool | None = None, agent_state: str = "") -> dict:
    """Shake: cancel a running agent, else undo the last inject."""
    if running is None:
        running = session_running()
    st = (agent_state or "").lower()
    if running or st in ("working", "waiting"):
        r = stop_generation("auto")
        r = dict(r)
        r["shake"] = "stop"
        return r
    r = undo_last_inject()
    r = dict(r)
    r["shake"] = "undo"
    return r


def undo_last_inject() -> dict:
    """Shake while idle: delete last inject, or Ctrl+Z if nothing stored."""
    global _last_inject
    kind, fg, exe = focused_info()
    text = _last_inject
    if kind not in ("cursor", "cli"):
        _host_log("[host] undo skip kind", kind, "len", len(text or ""), "fg", fg)
        return {"ok": False, "skipped": True, "kind": kind, "fg": fg}

    def fire():
        _release_modifiers()
        if text:
            for _ in text:
                _send_vk(VK_BACK)
                time.sleep(0.006)
        else:
            _chord(VK_CONTROL, VK_Z)
        _release_modifiers()

    _attach_foreground(fire)
    n = len(text)
    _last_inject = ""
    _host_log("[host] undo", n or "ctrl+z", "kind", kind, "fg", fg)
    return {"ok": True, "skipped": False, "n": n, "kind": kind, "fg": fg, "ctrl_z": n == 0}


def _send_one(inp: INPUT) -> int:
    return int(user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)))


def _send_unicode_unit(code: int) -> int:
    extra = ctypes.c_ulong(0)
    down = INPUT(type=INPUT_KEYBOARD)
    down.union.ki = KEYBDINPUT(0, code, KEYEVENTF_UNICODE, 0, ctypes.pointer(extra))
    up = INPUT(type=INPUT_KEYBOARD)
    up.union.ki = KEYBDINPUT(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, ctypes.pointer(extra))
    return _send_one(down) + _send_one(up)


def _send_unicode_char(code: int) -> int:
    if code > 0xFFFF:
        hi = 0xD800 + ((code - 0x10000) >> 10)
        lo = 0xDC00 + ((code - 0x10000) & 0x3FF)
        return _send_unicode_unit(hi) + _send_unicode_unit(lo)
    return _send_unicode_unit(code)


def _send_vk(vk: int, extra_flags: int = 0) -> int:
    extra = ctypes.c_ulong(0)
    scan = _scan(vk)
    down = INPUT(type=INPUT_KEYBOARD)
    down.union.ki = KEYBDINPUT(vk, scan, extra_flags, 0, ctypes.pointer(extra))
    up = INPUT(type=INPUT_KEYBOARD)
    up.union.ki = KEYBDINPUT(vk, scan, extra_flags | KEYEVENTF_KEYUP, 0, ctypes.pointer(extra))
    return _send_one(down) + _send_one(up)


def type_into_focus(text: str, press_enter: bool = False) -> int:
    def fire() -> int:
        sent = 0
        for ch in text:
            if ch == "\n":
                sent += _send_vk(VK_RETURN)
            else:
                sent += _send_unicode_char(ord(ch))
            time.sleep(0.003)
        if press_enter:
            time.sleep(0.05)
            sent += _send_vk(VK_RETURN)
        return sent

    return int(_attach_foreground(fire) or 0)


def _clipboard_get() -> str:
    if not user32.OpenClipboard(None):
        return ""
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return ""
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return ""
        try:
            size = kernel32.GlobalSize(handle)
            raw = ctypes.string_at(ptr, size)
            return raw.decode("utf-16-le", errors="ignore").rstrip("\x00")
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def _clipboard_set(text: str) -> bool:
    data = (text + "\x00").encode("utf-16-le")
    handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
    if not handle:
        return False
    ptr = kernel32.GlobalLock(handle)
    if not ptr:
        return False
    ctypes.memmove(ptr, data, len(data))
    kernel32.GlobalUnlock(handle)
    if not user32.OpenClipboard(None):
        return False
    try:
        user32.EmptyClipboard()
        return bool(user32.SetClipboardData(CF_UNICODETEXT, handle))
    finally:
        user32.CloseClipboard()


def _paste_via_clipboard(text: str) -> bool:
    prev = _clipboard_get()
    if not _clipboard_set(text):
        return False
    time.sleep(0.04)
    extra = ctypes.c_ulong(0)
    ctrl_down = INPUT(type=INPUT_KEYBOARD)
    ctrl_down.union.ki = KEYBDINPUT(VK_CONTROL, 0, 0, 0, ctypes.pointer(extra))
    v_down = INPUT(type=INPUT_KEYBOARD)
    v_down.union.ki = KEYBDINPUT(VK_V, 0, 0, 0, ctypes.pointer(extra))
    v_up = INPUT(type=INPUT_KEYBOARD)
    v_up.union.ki = KEYBDINPUT(VK_V, 0, KEYEVENTF_KEYUP, 0, ctypes.pointer(extra))
    ctrl_up = INPUT(type=INPUT_KEYBOARD)
    ctrl_up.union.ki = KEYBDINPUT(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0, ctypes.pointer(extra))
    ok = _send_one(ctrl_down) and _send_one(v_down) and _send_one(v_up) and _send_one(ctrl_up)
    time.sleep(0.12)
    if prev:
        _clipboard_set(prev)
    return bool(ok)


def inject_transcript(
    text: str,
    target: str = "auto",
    press_enter: bool = False,
    steal_focus: bool = False,
) -> dict:
    _ = (target, steal_focus)  # named target retired; follow the focused coding window
    cleaned = clean_transcript(text)
    if not cleaned:
        return {"ok": False, "err": "empty", "text": "", "method": ""}
    kind, _fg0, _exe0 = focused_info()
    fg_hwnd = user32.GetForegroundWindow()
    focused = True
    if kind in ("cursor", "cli"):
        remember_coding_hwnd(fg_hwnd)
    else:
        # Not in a coding app: restore the last one you used (or any coding window).
        focused = focus_coding_window()
        time.sleep(0.08)
    fg = foreground_title()
    sent = type_into_focus(cleaned, press_enter=press_enter)
    method = "sendinput"
    if sent <= 0:
        method = "clipboard"
        _paste_via_clipboard(cleaned)
        if press_enter:
            time.sleep(0.05)
            _attach_foreground(lambda: _send_vk(VK_RETURN))
    global _last_inject
    _last_inject = cleaned
    _host_log(
        "[host] inject",
        method,
        "sent",
        sent,
        "kind",
        classify_focus(fg),
        "fg",
        fg,
        "text",
        cleaned[:80],
    )
    return {
        "ok": True,
        "text": cleaned,
        "focused": focused,
        "fg": fg,
        "kind": classify_focus(fg),
        "target": "auto",
        "method": method,
        "sent": sent,
    }


if __name__ == "__main__":
    import sys

    msg = " ".join(sys.argv[1:]) or "desk inject ok"
    print(inject_transcript(msg))
