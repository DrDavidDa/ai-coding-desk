"""Emit .S files with absolute .incbin paths for the ESP32 assembler."""

import hashlib

from pathlib import Path



Import("env")



root = Path(env["PROJECT_DIR"])





def emit_incbin(symbol: str, rel: str, out_name: str) -> None:

    bin_path = root / rel

    digest = hashlib.sha256(bin_path.read_bytes()).hexdigest()[:16]

    out = root / "src" / out_name

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



WALL_BLOBS = [

    ("wave_bg_map", "src/assets/wave/wave.rgb565", "wave_img.S"),

    ("wall_ember_map", "src/assets/wave/ember.rgb565", "wall_ember.S"),

    ("wall_ink_map", "src/assets/wave/ink.rgb565", "wall_ink.S"),

    ("wall_phosphor_map", "src/assets/wave/phosphor.rgb565", "wall_phosphor.S"),

    ("wall_night_map", "src/assets/wave/night.rgb565", "wall_night.S"),

    ("wall_stone_map", "src/assets/wave/stone.rgb565", "wall_stone.S"),

]

for sym, rel, out in WALL_BLOBS:
    emit_incbin(sym, rel, out)

# Do NOT open the upload port after flash — on ESP32-S3 USB-JTAG that
# re-straps GPIO0 into download mode and leaves the LCD black.

