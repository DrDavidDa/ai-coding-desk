from desk_pair import build_config_lines, local_host_url, normalize_mac


def test_normalize_mac():
    assert normalize_mac("28:84:85:56:EE:E0") == "28848556EEE0"
    assert normalize_mac("28848556eee0") == "28848556EEE0"


def test_local_host_url_format():
    url = local_host_url(8787)
    assert url.startswith("http://")
    assert url.endswith(":8787")


def test_build_config_lines_wifi():
    lines = build_config_lines("http://192.168.1.2:8787", "test-key", ssid="Home", password="secret")
    assert "host_url=http://192.168.1.2:8787" in lines
    assert "host_key=test-key" in lines
    assert "wifi_ssid=Home" in lines
    assert "wifi_pass=secret" in lines
