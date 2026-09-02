#!/usr/bin/env python3
"""Proof that fb_bridge.cpp's plumbing (not just fb_card.v's RTL, already
proven by verify_fb_card.py) is correct: builds a full 65536-word fb_back[]
just like nova_fb.c would have after real DOB writes, and a binary input file
fb_bridge_test.cpp reads to call fb_bridge_render_text() directly -- the same
C function nova_fb.c calls at present-time.

Reuses gen_fb_card_test.FRAMES[0] (the cell8 layout) as the single source of
truth for both the input content and (via verify_frames._expected_text) the
expected output, same as verify_fb_card.py.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_fb_card_test as T

FB_WORDS = 65536


def main():
    name, width, height, cellw_flag, linegfx, layout = T.FRAMES[0]
    cellw = 9 if cellw_flag else 8
    cols, rows = width // cellw, height // 16
    textptr = 0o4000  # TEXTBUF, matches gen_text.TEXTBUF

    disp = [0] * FB_WORDS
    for row, col, text, attr in layout:
        for i, ch in enumerate(text):
            c = col + i
            if c >= cols or row >= rows:
                continue
            disp[(textptr + row * cols + c) % FB_WORDS] = (ord(ch) & 0xFF) | attr

    out_path = os.path.join(HERE, "output", "bridge_test_input.bin")
    with open(out_path, "wb") as f:
        f.write(struct.pack("<IIIHHH", FB_WORDS, width, height, textptr, 0, 1))  # tctl=T_ENABLE
        f.write(struct.pack("<%dH" % FB_WORDS, *disp))
    print("wrote %s" % out_path)


if __name__ == "__main__":
    main()
