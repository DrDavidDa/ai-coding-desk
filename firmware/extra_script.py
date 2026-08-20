"""Emit .S files with absolute .incbin paths for the ESP32 assembler."""
import hashlib
from pathlib import Path

Import("env")

root = Path(env["PROJECT_DIR"])


def emit_incbin(symbol: str, rel: str, out_name: str) -> None:
    bin_path = root / rel
    digest = hashlib.sha256(bin_path.read_bytes()).hexdigest()[:16]
    out = root / "src" / out_name
    # Hash must be in the .S file: SCons only watches logos.S, not the .incbin blob.
    out.write_text(
        f"    /* {rel} sha256={digest} */\n"
        '    .section .rodata,"a"\n'
        "    .align 4\n"
        f"    .global {symbol}\n"
        f"{symbol}:\n"
        f'    .incbin "{bin_path.as_posix()}"\n',
        encoding="utf-8",
    )
    env.Depends(str(env.subst(f"$BUILD_DIR/src/{out_name}.o")), str(bin_path))
    print(out_name, "->", bin_path, digest)


emit_incbin("pack_frames_map", "src/assets/pack/frames.rgb565", "pack_img.S")
emit_incbin("logo_frames_map", "src/assets/logos/frames.rgb565", "logos.S")

