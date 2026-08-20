"""Flash Desk154 only when the COM port actually opens. Never COM4/COM6."""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import serial
from serial.tools import list_ports

MAC = "28848556EEE0"
SKIP = {"COM4", "COM6"}
BUILD = Path(r"E:\ai-coding-desk\firmware\.pio\build\waveshare_lcd_154")
BOOT0 = Path(
    r"E:\platformio\packages\framework-arduinoespressif32\tools\partitions\boot_app0.bin"
)
LOG = Path(r"E:\ai-coding-desk\firmware\.pio\flash_try.txt")


def desk_port() -> str | None:
    for x in list_ports.comports():
        if (x.device or "").upper() in SKIP:
            continue
        if MAC in (x.hwid or "").upper().replace(":", ""):
            return x.device
    return None


def in_rom(dev: str) -> bool:
    try:
        r = subprocess.run(
            [
                sys.executable,
                "-m",
                "esptool",
                "--chip",
                "esp32s3",
                "--port",
                dev,
                "--baud",
                "115200",
                "--before",
                "no-reset",
                "--connect-attempts",
                "1",
                "--after",
                "no-reset",
                "chip-id",
            ],
            capture_output=True,
            timeout=8,
        )
    except subprocess.TimeoutExpired:
        return False
    text = ((r.stdout or b"") + (r.stderr or b"")).decode("utf-8", "replace")
    return r.returncode == 0 and "Chip is ESP32-S3" in text


def port_alive(dev: str) -> bool:
    ser = serial.Serial()
    ser.port = dev
    ser.baudrate = 115200
    ser.timeout = 0.2
    ser.dtr = False
    ser.rts = False
    try:
        ser.open()
        ser.dtr = False
        ser.rts = False
        ser.close()
        return True
    except Exception:
        try:
            ser.close()
        except Exception:
            pass
        return False


def main() -> int:
    deadline = time.time() + 360
    print("WAIT_DOWNLOAD left-cap BOOT held, then unplug and replug", flush=True)
    last_app = None
    while time.time() < deadline:
        p = desk_port()
        if not p:
            last_app = None
            print("NO_PORT", time.strftime("%H:%M:%S"), flush=True)
            time.sleep(0.5)
            continue
        if not port_alive(p):
            print("GHOST", p, time.strftime("%H:%M:%S"), flush=True)
            time.sleep(0.8)
            continue
        if last_app == p:
            time.sleep(0.4)
            continue
        if not in_rom(p):
            last_app = p
            print("APP_MODE", p, "do not keep probing; wait for BOOT+replug", flush=True)
            continue
        print("FLASH", p, time.strftime("%H:%M:%S"), flush=True)
        argv = [
            sys.executable,
            "-m",
            "esptool",
            "--chip",
            "esp32s3",
            "--port",
            p,
            "--baud",
            "460800",
            "--before",
            "no-reset",
            "--connect-attempts",
            "3",
            "--after",
            "no-reset",
            "write-flash",
            "-z",
            "--flash-mode",
            "dio",
            "--flash-freq",
            "80m",
            "--flash-size",
            "16MB",
            "0x0",
            str(BUILD / "bootloader.bin"),
            "0x8000",
            str(BUILD / "partitions.bin"),
            "0xe000",
            str(BOOT0),
            "0x10000",
            str(BUILD / "firmware.bin"),
        ]
        r = subprocess.run(argv, capture_output=True)
        LOG.write_bytes((r.stdout or b"") + (r.stderr or b""))
        text = ((r.stdout or b"") + (r.stderr or b"")).decode("utf-8", "replace")
        hashes = text.count("Hash of data verified")
        app = "0x00010000" in text and "Wrote " in text and hashes >= 3
        print("rc", r.returncode, "hash", hashes, "app", app, flush=True)
        if hashes >= 3 or app:
            print("FLASH_OK", flush=True)
            return 0
        time.sleep(1.2)
    print("FLASH_TIMEOUT", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
