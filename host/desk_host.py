"""Windows tray + FastAPI status hub. Secrets never leave this process except as numbers."""
from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from paths import (
    app_dir,
    autostart_off_flag,
    data_dir,
    frozen as app_frozen,
    host_log_path,
    paired_flag,
    secrets_dir,
)

ROOT = app_dir()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from collectors.claude import fetch_claude, fetch_deepseek
from collectors.codex import fetch_codex
from collectors.coze import fetch_coze
from collectors.cursor import fetch_cursor, parse_cursor_summary
from collectors.glm import fetch_glm
from collectors.kimi import fetch_kimi
from collectors.trae import fetch_trae
from collectors.agent import detect_cursor_agent

HOST_KEY_FILE = secrets_dir() / "host_key.txt"
SNAPSHOT = data_dir() / "data" / "snapshot.json"
DEFAULT_KEY = "desk-local"
POLL_SEC = 60

_lock = threading.Lock()
_state = {
    "ts": 0,
    "agent": {"state": "idle", "name": ""},
    "voice": {"last_text": "", "target": "auto"},
    "providers": {
        "claude": {"ok": False, "err": "init"},
        "deepseek": {"ok": False, "err": "init"},
        "codex": {"ok": False, "err": "init"},
        "cursor": {"ok": False, "err": "init"},
        "glm": {"ok": False, "err": "init"},
        "kimi": {"ok": False, "err": "init"},
        "trae": {"ok": False, "err": "init"},
        "coze": {"ok": False, "err": "init"},
    },
}


def host_key() -> str:
    if HOST_KEY_FILE.is_file():
        k = HOST_KEY_FILE.read_text(encoding="utf-8").strip()
        if k:
            return k
    return os.environ.get("DESK_HOST_KEY", DEFAULT_KEY)


def _check_key(key: str | None) -> None:
    if key != host_key():
        raise HTTPException(401, "bad key")


def save_snapshot() -> None:
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps(_state, ensure_ascii=False, indent=2), encoding="utf-8")


def load_snapshot() -> None:
    if SNAPSHOT.is_file():
        try:
            data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
            with _lock:
                _state.update(data)
        except Exception:
            pass


def refresh_once() -> None:
    with _lock:
        prev = json.loads(json.dumps(_state["providers"]))
    glm = fetch_glm(prev=prev.get("glm"))
    claude = fetch_claude(prev=prev.get("claude"))
    deepseek = fetch_deepseek(prev=prev.get("deepseek"))
    codex = fetch_codex(prev=prev.get("codex"))
    cursor = fetch_cursor(prev=prev.get("cursor"))
    kimi = fetch_kimi(prev=prev.get("kimi"))
    trae = fetch_trae(prev=prev.get("trae"))
    coze = fetch_coze(prev=prev.get("coze"))
    agent = detect_cursor_agent()
    with _lock:
        _state["ts"] = int(time.time())
        _state["agent"] = {"state": agent.get("state") or "idle", "name": agent.get("name") or ""}
        _state["providers"]["glm"] = glm
        _state["providers"]["claude"] = claude
        _state["providers"]["deepseek"] = deepseek
        _state["providers"]["codex"] = codex
        _state["providers"]["cursor"] = cursor
        _state["providers"]["kimi"] = kimi
        _state["providers"]["trae"] = trae
        _state["providers"]["coze"] = coze
        save_snapshot()


def poll_loop() -> None:
    while True:
        try:
            refresh_once()
        except Exception as exc:
            print("[host] poll error", exc)
        time.sleep(POLL_SEC)


app = FastAPI(title="AI Coding Desk")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/v1/status")
def status(key: str = Query(""), fresh: int = Query(0)):
    _check_key(key)
    if fresh:
        refresh_once()
    with _lock:
        return json.loads(json.dumps(_state))


@app.post("/v1/refresh")
def refresh_in(key: str = Query("")):
    _check_key(key)
    refresh_once()
    request_puck_poll()
    with _lock:
        return {"ok": True, "ts": _state["ts"]}


class CursorIn(BaseModel):
    autoPercentUsed: float | None = None
    apiPercentUsed: float | None = None
    auto_pct: int | None = None
    api_pct: int | None = None
    totalPercentUsed: float | None = None
    total_pct: int | None = None
    billingCycleEnd: int | str | None = None
    cycle_end: int | None = None


@app.post("/v1/cursor")
def cursor_in(body: CursorIn, key: str = Query("")):
    _check_key(key)
    with _lock:
        prev = _state["providers"].get("cursor") or {}
        parsed = parse_cursor_summary(body.model_dump(exclude_none=True), prev)
        _state["providers"]["cursor"] = parsed
        _state["ts"] = int(time.time())
        save_snapshot()
    return {"ok": True}


class AgentIn(BaseModel):
    state: str = "idle"
    name: str = ""


@app.post("/v1/agent")
def agent_in(body: AgentIn, key: str = Query("")):
    _check_key(key)
    with _lock:
        _state["agent"] = {"state": body.state, "name": body.name}
        _state["ts"] = int(time.time())
        save_snapshot()
    return {"ok": True}


@app.post("/v1/audio")
async def audio_in(
    request: Request,
    key: str = Query(""),
    target: str = Query("auto"),
    send: int = Query(0),
    focus: int = Query(1),
):
    _check_key(key)
    wav = await request.body()
    if len(wav) < 44:
        raise HTTPException(400, "wav too small")
    from asr import paste_text, transcribe_wav

    try:
        text = transcribe_wav(wav)
    except Exception as exc:
        raise HTTPException(502, str(exc)) from exc
    injected = paste_text(text, target="auto", press_enter=bool(send), steal_focus=bool(focus))
    kind = injected.get("kind") or "auto"
    with _lock:
        _state["voice"] = {"last_text": injected.get("text") or text, "target": kind, "fg": injected.get("fg", "")}
        _state["ts"] = int(time.time())
        save_snapshot()
    return {"ok": True, "text": injected.get("text") or text, "inject": injected}


class InjectIn(BaseModel):
    text: str
    target: str = "auto"
    send: bool = False
    focus: bool = False


@app.post("/v1/inject")
def inject_in(body: InjectIn, key: str = Query("")):
    """Type text into the focused coding dialog — same path as ASR, no microphone."""
    _check_key(key)
    from inject import inject_transcript

    injected = inject_transcript(body.text, target="auto", press_enter=body.send, steal_focus=body.focus)
    kind = injected.get("kind") or "auto"
    with _lock:
        _state["voice"] = {"last_text": injected.get("text") or "", "target": kind, "fg": injected.get("fg", "")}
        _state["ts"] = int(time.time())
        save_snapshot()
    return injected


_last_stop_ts = 0.0
_stop_lock = threading.Lock()


def _append_stop_log(line: str) -> None:
    try:
        p = data_dir() / "data" / "stop.log"
        p.parent.mkdir(exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(f"{int(time.time())} {line}\n")
    except Exception:
        pass


def request_stop(target: str | None = None) -> dict:
    """Cancel the focused Cursor app or coding CLI. Never steal focus."""
    global _last_stop_ts
    now = time.time()
    with _stop_lock:
        if now - _last_stop_ts < 0.5:
            _append_stop_log("skip debounce")
            return {"ok": True, "skipped": True}
        _last_stop_ts = now
    from inject import stop_generation

    with _lock:
        chosen = target or "auto"
    _append_stop_log(f"begin target={chosen}")
    result = stop_generation(chosen)
    _append_stop_log(f"done {result}")
    return result


@app.post("/v1/stop")
def stop_in(key: str = Query(""), target: str = Query("cursor")):
    _check_key(key)
    return request_stop(target)


def process_wav_bytes(wav: bytes, target: str = "auto") -> dict:
    from asr import paste_text, transcribe_wav

    text = transcribe_wav(wav)
    injected = paste_text(text, target="auto", press_enter=False, steal_focus=True)
    kind = injected.get("kind") or "auto"
    with _lock:
        _state["voice"] = {"last_text": injected.get("text") or text, "target": kind, "fg": injected.get("fg", "")}
        _state["ts"] = int(time.time())
        save_snapshot()
    _safe_print("[host] asr", injected.get("text") or text)
    return {"ok": True, "text": injected.get("text") or text, "inject": injected}


def find_desk_port() -> str | None:
    from desk_pair import find_desk_port as _find

    return _find(env_port=os.environ.get("DESK_SERIAL", "").strip() or None)


STOP_MARKERS = ("#STOP", "[HID] Esc", "[HID] stop")
ENTER_MARKERS = ("#ENTER host",)


def compact_status_json() -> str:
    """USB quota push. Must stay under firmware SERIAL_LINE_MAX (1024)."""
    with _lock:
        st = json.loads(json.dumps(_state))
    prov = st.get("providers") or {}

    def slim(p: dict, keys: tuple[str, ...]) -> dict:
        o = {"ok": bool(p.get("ok"))}
        err = p.get("err") or ""
        if err:
            o["err"] = str(err)[:12]
        for k in keys:
            if k in p and p[k] is not None:
                o[k] = p[k]
        return o

    doc = {
        "ts": int(st.get("ts") or 0),
        "agent": st.get("agent") or {"state": "idle", "name": ""},
        "providers": {
            "claude": slim(prov.get("claude") or {}, ("h5", "d7", "reset_h5", "reset_d7", "daily_tokens")),
            "deepseek": slim(prov.get("deepseek") or {}, ("daily_tokens",)),
            "codex": slim(prov.get("codex") or {}, ("h5", "d7", "reset_h5", "reset_d7")),
            "cursor": slim(prov.get("cursor") or {}, ("auto_pct", "api_pct", "total_pct", "cycle_end")),
            "glm": slim(prov.get("glm") or {}, ("h5", "d7", "mcp", "reset_h5", "reset_d7", "daily_tokens")),
            "kimi": slim(prov.get("kimi") or {}, ("h5", "d7", "reset_h5", "reset_d7")),
            "trae": slim(prov.get("trae") or {}, ("h5", "d7", "reset_h5", "reset_d7", "left", "cap")),
            "coze": slim(prov.get("coze") or {}, ("h5", "d7", "reset_h5", "reset_d7", "left", "cap")),
        },
    }
    return json.dumps(doc, separators=(",", ":"), ensure_ascii=True)


def quota_push_line() -> bytes:
    body = compact_status_json()
    line = "#QJ|" + body + "\n"
    if len(line) >= 1000:
        raise ValueError("qj too long %s" % len(line))
    return line.encode("ascii")


# USB quota (#QJ) is fallback only. Stay off until the puck says Wi-Fi failed.
_puck_need_usb = False
_kick_puck = False


def request_puck_poll() -> None:
    """Active refresh: ask the puck to GET /v1/status?fresh=1 over Wi-Fi."""
    global _kick_puck
    _kick_puck = True


def puck_needs_usb_quota() -> bool:
    return _puck_need_usb


def _note_puck_line(txt: str) -> None:
    global _puck_need_usb
    if txt.startswith("#NEEDQ") or "[NET] no wifi" in txt or " wifi=0" in txt:
        _puck_need_usb = True
        return
    if (
        " wifi=1" in txt
        or txt.startswith("[NET] glm")
        or txt.startswith("[NET] wifi ")
        or "[QJ] skip wifi" in txt
    ):
        _puck_need_usb = False


def _maybe_stop_from_line(txt: str) -> None:
    if not any(m in txt for m in STOP_MARKERS):
        return
    _append_stop_log(f"serial {txt}")
    threading.Thread(target=request_stop, daemon=True).start()


def _maybe_enter_from_line(txt: str) -> None:
    if not any(m in txt for m in ENTER_MARKERS):
        return
    def go():
        from inject import press_enter
        press_enter()
    threading.Thread(target=go, daemon=True).start()


def _safe_print(*parts) -> None:
    msg = " ".join(str(p) for p in parts)
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "backslashreplace").decode("ascii"))


def _on_dev_line(txt: str) -> None:
    """Handle a firmware log line. Must not raise — a GBK print crash
    was dropping the serial session, so BOOT Enter after ASR never landed."""
    _safe_print("[dev]", txt)
    _note_puck_line(txt)
    _maybe_stop_from_line(txt)
    _maybe_enter_from_line(txt)
    _maybe_pwr_from_line(txt)
    _maybe_undo_from_line(txt)


def _maybe_pwr_from_line(txt: str) -> None:
    if txt.strip() != "#PWR":
        return
    def go():
        from inject import focused_info, pwr_action, stop_generation, press_up, session_running
        from collectors.agent import detect_cursor_agent
        st = (detect_cursor_agent() or {}).get("state") or "idle"
        kind, fg, exe = focused_info()
        act = pwr_action(fg, st, exe=exe, running=session_running())
        _safe_print("[host] pwr", act, "kind", kind, "exe", exe, "agent", st, "run", int(session_running()), "fg", fg)
        if act == "stop":
            stop_generation("auto")
        elif act == "up":
            press_up()
        else:
            request_puck_poll()
    threading.Thread(target=go, daemon=True).start()


def _maybe_undo_from_line(txt: str) -> None:
    if txt.strip() != "#UNDO":
        return
    def go():
        from inject import handle_shake
        from collectors.agent import detect_cursor_agent
        st = (detect_cursor_agent() or {}).get("state") or "idle"
        r = handle_shake(agent_state=st)
        _safe_print("[host] shake", r.get("shake"), "skip", int(bool(r.get("skipped"))), "fg", r.get("fg", ""))
    threading.Thread(target=go, daemon=True).start()


def serial_watch_loop() -> None:
    import serial as pyserial
    from desk_pair import open_serial, serial_write
    global _kick_puck, _puck_need_usb

    while True:
        port = find_desk_port()
        if not port:
            time.sleep(3)
            continue
        print("[host] serial watch", port)
        try:
            # USB-JTAG (303A:1001): Windows RX needs DTR asserted. Never pulse DTR/RTS.
            time.sleep(2.5)
            port = find_desk_port() or port
            ser = open_serial(port)
            try:
                serial_write(ser, b"#STATUS\n")
                serial_write(ser, b"#WAKE\n")
                serial_write(ser, b"#POLL\n")
                serial_write(ser, f"#TIME {int(time.time())}\n".encode("ascii"))
            except Exception:
                pass
            last_qj = 0.0
            last_time = time.time()
            _puck_need_usb = False
            _kick_puck = False
            while True:
                now = time.time()
                if _kick_puck:
                    _kick_puck = False
                    try:
                        serial_write(ser, b"#POLL\n")
                    except Exception as exc:
                        print("[host] poll", exc)
                if now - last_qj >= 8:
                    last_qj = now
                    try:
                        serial_write(ser, quota_push_line())
                        print("[host] usb quota")
                    except Exception as exc:
                        print("[host] qj", exc)
                if now - last_time >= 60:
                    last_time = now
                    try:
                        serial_write(ser, f"#TIME {int(now)}\n".encode("ascii"))
                    except Exception:
                        pass
                line = ser.readline()
                if not line:
                    continue
                if not line.startswith(b"#WAVBEGIN"):
                    txt = line.decode("utf-8", "replace").strip()
                    if txt:
                        _on_dev_line(txt)
                    continue
                parts = line.decode("ascii", "replace").split()
                n = int(parts[1])
                data = bytearray()
                while len(data) < n:
                    chunk = ser.read(n - len(data))
                    if not chunk:
                        break
                    data.extend(chunk)
                rest = ser.read(32)
                print("[host] wav bytes", len(data), "expect", n)
                if len(data) < 44:
                    continue
                try:
                    out = process_wav_bytes(bytes(data[:n] if len(data) > n else data))
                    text = (out.get("text") or "").replace("\r", " ").replace("\n", " ")[:180]
                    if text:
                        serial_write(ser, ("#TEXT|" + text + "\n").encode("utf-8"))
                except Exception as exc:
                    _safe_print("[host] asr fail", exc)
                del rest
        except Exception as exc:
            _safe_print("[host] serial", exc)
            time.sleep(0.3)


def run_tray() -> None:
    try:
        import pystray
        from PIL import Image, ImageDraw
    except Exception:
        print("[host] pystray/PIL missing — API only")
        return

    img = Image.new("RGB", (64, 64), (17, 24, 39))
    d = ImageDraw.Draw(img)
    d.ellipse((8, 8, 56, 56), fill=(59, 130, 246))

    def on_refresh(icon, item):
        def go():
            refresh_once()
            request_puck_poll()
        threading.Thread(target=go, daemon=True).start()

    def on_quit(icon, item):
        icon.stop()
        os._exit(0)

    def on_pair_again(icon, item):
        try:
            paired_flag().unlink(missing_ok=True)
        except OSError:
            pass
        if app_frozen():
            cmd = 'cmd /c ping 127.0.0.1 -n 3 >nul & start "" "%s"' % sys.executable
        else:
            cmd = 'cmd /c ping 127.0.0.1 -n 3 >nul & start "" "%s" -u "%s"' % (
                sys.executable,
                ROOT / "desk_host.py",
            )
        subprocess.Popen(cmd, shell=True)
        icon.stop()
        os._exit(0)

    def on_open_data(icon, item):
        try:
            os.startfile(data_dir())  # type: ignore[attr-defined]
        except Exception:
            pass

    menu = pystray.Menu(
        pystray.MenuItem("刷新额度", on_refresh),
        pystray.MenuItem("重新配对", on_pair_again),
        pystray.MenuItem("打开数据文件夹", on_open_data),
        pystray.MenuItem("退出", on_quit),
    )
    pystray.Icon("desk154", img, "Desk154", menu).run()


def _acquire_instance() -> bool:
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateMutexW.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p)
    k32.CreateMutexW.restype = ctypes.c_void_p
    ctypes.set_last_error(0)
    k32.CreateMutexW(None, 1, "Global\\Desk154Host")
    return ctypes.get_last_error() != 183


def ensure_autostart() -> None:
    if os.environ.get("DESK_NO_AUTOSTART") == "1":
        return
    from setup_gui import apply_autostart

    apply_autostart(not autostart_off_flag().is_file())


def _redirect_frozen_log() -> None:
    if not app_frozen():
        return
    log = host_log_path()
    try:
        fh = open(log, "a", encoding="utf-8", buffering=1)
        sys.stdout = fh
        sys.stderr = fh
    except Exception:
        pass


def _maybe_wizard() -> None:
    if os.environ.get("DESK_SKIP_WIZARD") == "1" or os.environ.get("DESK_NO_TRAY") == "1":
        return
    force = "--pair" in sys.argv or os.environ.get("DESK_PAIR") == "1"
    if not force and paired_flag().is_file():
        return
    from setup_gui import run_wizard

    run_wizard()


def main() -> None:
    _redirect_frozen_log()
    if not _acquire_instance():
        print("[host] already running")
        return
    _maybe_wizard()
    ensure_autostart()
    secrets_dir().mkdir(exist_ok=True)
    (data_dir() / "data").mkdir(exist_ok=True)
    if not HOST_KEY_FILE.is_file():
        HOST_KEY_FILE.write_text(DEFAULT_KEY, encoding="utf-8")
    load_snapshot()
    threading.Thread(target=poll_loop, daemon=True).start()
    threading.Thread(target=refresh_once, daemon=True).start()
    threading.Thread(target=serial_watch_loop, daemon=True).start()
    def on_ble_wav(wav: bytes) -> None:
        process_wav_bytes(wav)

    if os.environ.get("DESK_BLE_AUDIO") == "1":
        try:
            from ble_audio import start_thread as start_ble_audio

            start_ble_audio(on_ble_wav, on_stop=request_stop)
        except Exception as exc:
            print("[host] ble audio not started", exc)
    else:
        print("[host] ble audio off (HID stay connected; Wi-Fi carries voice)")

    import uvicorn

    config = uvicorn.Config(app, host="0.0.0.0", port=int(os.environ.get("DESK_PORT", "8787")), log_level="info")
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()
    print("[host] http://0.0.0.0:8787  key=", host_key())
    if os.environ.get("DESK_NO_TRAY") == "1":
        while True:
            time.sleep(3600)
    run_tray()
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
