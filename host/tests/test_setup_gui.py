from setup_gui import pair_now, save_sf_key
from paths import secrets_dir


def test_pair_now_without_device():
    ok, msg = pair_now("", "")
    assert ok is False
    assert "没找到设备" in msg


def test_save_sf_key_writes_asr_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DESK_DATA_DIR", str(tmp_path))
    save_sf_key(" sk-test ")
    written = (secrets_dir() / "sf_api_key.txt").read_text(encoding="utf-8")
    assert written == "sk-test"
