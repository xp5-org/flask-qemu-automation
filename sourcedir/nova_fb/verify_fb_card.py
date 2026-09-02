#!/usr/bin/env python3
"""Check fb_card_tb.cpp's captured frames against verify_frames._expected_text
-- the SAME recompute nova_fb's own C-model tests use -- so a pass here is
proof the RTL draws exactly what the C model it's replacing would have.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_text
import gen_fb_card_test as T
import verify_frames as VF

OUT = os.path.join(HERE, "output")


def read_mono(path):
    with open(path, "rb") as f:
        data = f.read()
    w, h = struct.unpack("<II", data[:8])
    stride = (w + 7) // 8
    body = data[8:]
    rows = [body[r * stride:(r + 1) * stride] for r in range(h)]
    return w, h, rows


def bit(rows, x, y):
    return (rows[y][x // 8] >> (7 - x % 8)) & 1


def check(name, cond, detail=""):
    print("  %-4s %s%s" % ("ok" if cond else "FAIL", name,
                           "" if cond else "  <- " + detail))
    return cond


def main():
    ok = True
    for name, width, height, cellw_flag, linegfx, layout in T.FRAMES:
        cellw = 9 if cellw_flag else gen_text.CHAR_W
        print("%s -- %dx%d, %d dot cell, linegfx=%s"
              % (name, width, height, cellw, linegfx))
        path = os.path.join(OUT, name + ".mono")
        w, h, rows = read_mono(path)
        ok &= check("geometry %dx%d" % (width, height), (w, h) == (width, height),
                    "got %dx%d" % (w, h))
        if (w, h) != (width, height):
            continue

        want = VF._expected_text(layout, width, height, cellw, linegfx=linegfx)
        bad = 0
        for y in range(h):
            for x in range(w):
                got = bit(rows, x, y)
                if got != (1 if (x, y) in want else 0):
                    bad += 1
        ok &= check("every pixel matches verify_frames._expected_text",
                    bad == 0, "%d pixels differ" % bad)

    print("\n%s" % ("ALL CHECKS PASSED" if ok else "FAILURES PRESENT"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
