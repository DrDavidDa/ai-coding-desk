from fastapi.testclient import TestClient
import json

import desk_host


def test_healthz_and_status_key():
    c = TestClient(desk_host.app)
    assert c.get("/healthz").json()["ok"] is True
    assert c.get("/v1/status?key=wrong").status_code == 401
    r = c.get("/v1/status?key=" + desk_host.host_key())
    assert r.status_code == 200
    body = r.json()
    assert "providers" in body
    assert "glm" in body["providers"]
    assert "claude" in body["providers"]
    assert "codex" in body["providers"]
    assert "kimi" in body["providers"]
    assert "trae" in body["providers"]
    assert "coze" in body["providers"]


def test_inject_endpoint_empty_rejected_as_not_ok():
    c = TestClient(desk_host.app)
    r = c.post("/v1/inject?key=" + desk_host.host_key(), json={"text": "   "})
    assert r.status_code == 200
    assert r.json()["ok"] is False
    assert r.json()["err"] == "empty"


def test_audio_rejects_tiny_body():
    c = TestClient(desk_host.app)
    r = c.post("/v1/audio?key=" + desk_host.host_key(), content=b"RIFF")
    assert r.status_code == 400


def test_cursor_post_numbers_only():
    c = TestClient(desk_host.app)
    r = c.post(
        "/v1/cursor?key=" + desk_host.host_key(),
        json={"autoPercentUsed": 37, "apiPercentUsed": 80},
    )
    assert r.status_code == 200
    st = c.get("/v1/status?key=" + desk_host.host_key()).json()
    assert st["providers"]["cursor"]["auto_pct"] == 37
    assert st["providers"]["cursor"]["api_pct"] == 80


def test_refresh_endpoint():
    c = TestClient(desk_host.app)
    r = c.post("/v1/refresh?key=" + desk_host.host_key())
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_usb_quota_only_when_wifi_fails():
    desk_host._puck_need_usb = False
    desk_host._note_puck_line("use_wifi=1 ssid=Xiaomi_403A cfg_ok=1 host_ok=1 wifi=1 bat=71")
    assert desk_host.puck_needs_usb_quota() is False
    desk_host._note_puck_line("[NET] glm 5h=100 7d=80 mcp=24 host_ok=1")
    assert desk_host.puck_needs_usb_quota() is False
    desk_host._note_puck_line("#NEEDQ")
    assert desk_host.puck_needs_usb_quota() is True
    desk_host._note_puck_line("use_wifi=1 ssid=Xiaomi_403A cfg_ok=1 host_ok=0 wifi=0 bat=71")
    assert desk_host.puck_needs_usb_quota() is True
    desk_host._note_puck_line("[NET] wifi Xiaomi_403A ip 192.168.31.226")
    assert desk_host.puck_needs_usb_quota() is False
    desk_host._puck_need_usb = False


def test_quota_push_line_fits_serial():
    with desk_host._lock:
        desk_host._state["providers"]["glm"] = {"ok": True, "h5": 100, "d7": 80, "mcp": 24}
        desk_host._state["providers"]["cursor"] = {"ok": True, "auto_pct": 37, "api_pct": 80}
        desk_host._state["providers"]["kimi"] = {"ok": True, "h5": 15, "d7": 26}
        desk_host._state["providers"]["trae"] = {"ok": True, "h5": 27, "left": 363, "cap": 500, "reset_h5": 1788191999}
        desk_host._state["providers"]["coze"] = {"ok": True, "h5": 0, "left": 1000, "cap": 1000, "reset_h5": 1788191999}
    raw = desk_host.quota_push_line()
    assert raw.startswith(b"#QJ|{")
    assert raw.endswith(b"\n")
    assert len(raw) < 1000
    body = json.loads(raw[4:].decode("ascii"))
    assert body["providers"]["glm"]["h5"] == 100
    assert body["providers"]["cursor"]["auto_pct"] == 37
    assert body["providers"]["kimi"]["h5"] == 15
    assert body["providers"]["trae"]["h5"] == 27
    assert body["providers"]["trae"]["left"] == 363
    assert body["providers"]["coze"]["h5"] == 0
    assert body["providers"]["coze"]["cap"] == 1000


def test_on_dev_line_dispatches_enter_after_unicode_asr(monkeypatch):
    hits = []
    monkeypatch.setattr(desk_host, "_safe_print", lambda *a: None)
    monkeypatch.setattr(desk_host, "_note_puck_line", lambda t: None)
    monkeypatch.setattr(desk_host, "_maybe_stop_from_line", lambda t: None)
    monkeypatch.setattr(desk_host, "_maybe_pwr_from_line", lambda t: None)
    monkeypatch.setattr(desk_host, "_maybe_enter_from_line", lambda t: hits.append(t))
    desk_host._on_dev_line('asr {"text":"\U0001f614"}')
    desk_host._on_dev_line("#ENTER host")
    assert hits[-1] == "#ENTER host"
