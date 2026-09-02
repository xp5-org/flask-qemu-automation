#!/usr/bin/env python3
"""Standalone correctness proof for fb_card.v, BEFORE it's wired into
nova_fb.c: drives the RTL over the exact bus protocol a real Nova IOT would
use (see src/fb_card.v's header comment for the register semantics), for two
small test frames -- one 8-dot-cell, one 9-dot-cell with LINEGFX -- and
writes the transaction script fb_card_tb.cpp replays.

Single source of truth with the checker: verify_fb_card.py imports FRAMES
from this file and calls verify_frames._expected_text (the SAME function
nova_fb's own tests use to recompute what char mode should draw) rather than
re-deriving the expected pixels, so a passing check here is proof the RTL
draws exactly what nova_fb.c's C model would have drawn for this content --
not a new, independently-written notion of "correct".
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_text

REVERSE, ULINE = gen_text.REVERSE, gen_text.ULINE
T_ENABLE, T_CELL9, T_LINEGFX = gen_text.T_ENABLE, gen_text.T_CELL9, gen_text.T_LINEGFX
TEXTBUF = gen_text.TEXTBUF

CTL_TEXT = 0o2000
CTL_WORD_AUTOINC = 0o20000

# reg_sel encoding fb_card.v expects: 0=NONE 1=A 2=B 3=C
SEL_NONE, SEL_A, SEL_B, SEL_C = 0, 1, 2, 3
PULSE_NONE, PULSE_S, PULSE_C, PULSE_P = 0, 1, 2, 3

# (name, width, height, cellw_flag, linegfx, layout)
#
# WIDTH/HEIGHT MUST match fb_card.v's module parameter defaults (720x400):
# they are Verilog parameters, not bus registers (same as the real card's
# WIDTH/HEIGHT -- see fb_card.v's header), and the Verilated model below is
# built once with no per-test overrides, so a test picking any other
# resolution would silently drive a card whose RTL is still scanning out at
# 720x400 -- exactly the geometry-mismatch bug this comment is here to
# prevent someone from reintroducing.
FRAMES = [
    ("frame_cell8", 720, 400, False, False, [
        (0, 0, "HELLO FPGA TEXT MODE", 0),
        (2, 0, "REVERSE", REVERSE),
        (4, 0, "UNDERLINE", ULINE),
        (6, 0, "abcXYZ 0123", 0),
    ]),
    ("frame_cell9_linegfx", 720, 400, True, True, [
        (0, 0, chr(0xC4) * 10, 0),   # box-drawing range 0xC0-0xDF: LINEGFX
        (2, 0, "CELL9 TEST", 0),     # repeats column 8 so lines join up
    ]),
]


def build_script(width, height, cellw_flag, linegfx, layout):
    """(cells, transactions) for one frame -- cells is {(row,col): word},
    transactions is the [(reg_sel, we, pulse, data), ...] bus script."""
    cellw = 9 if cellw_flag else gen_text.CHAR_W
    cols, rows = width // cellw, height // gen_text.CELL_H

    cells = {}
    for row, col, text, attr in layout:
        for i, ch in enumerate(text):
            c = col + i
            if c >= cols or row >= rows:
                continue
            cells[(row, c)] = (ord(ch) & 0xFF) | attr

    txns = []
    # 1. Word mode, autoinc: load the text buffer at TEXTBUF.
    txns.append((SEL_C, 1, PULSE_NONE, CTL_WORD_AUTOINC))
    txns.append((SEL_A, 1, PULSE_NONE, TEXTBUF))
    for row in range(rows):
        for col in range(cols):
            txns.append((SEL_B, 1, PULSE_NONE, cells.get((row, col), 0)))

    # 2. Text register port: TEXTPTR, CHARPTR=0 (ROM), TCTL.
    tctl = T_ENABLE | (T_CELL9 if cellw_flag else 0) | (T_LINEGFX if linegfx else 0)
    txns.append((SEL_C, 1, PULSE_NONE, CTL_TEXT))
    txns.append((SEL_A, 1, PULSE_NONE, 0))
    txns.append((SEL_B, 1, PULSE_NONE, TEXTBUF))
    txns.append((SEL_B, 1, PULSE_NONE, 0))
    txns.append((SEL_B, 1, PULSE_NONE, tctl))

    # 3. Present.
    txns.append((SEL_NONE, 0, PULSE_P, 0))
    return cells, txns


def write_script(path, txns):
    with open(path, "w") as f:
        for reg_sel, we, pulse, data in txns:
            f.write("%d %d %d %d\n" % (reg_sel, we, pulse, data & 0xFFFF))


def main():
    outdir = os.path.join(HERE, "output")
    os.makedirs(outdir, exist_ok=True)
    for name, width, height, cellw_flag, linegfx, layout in FRAMES:
        _cells, txns = build_script(width, height, cellw_flag, linegfx, layout)
        script_path = os.path.join(outdir, name + ".script")
        write_script(script_path, txns)
        print("wrote %s (%d transactions, %dx%d)"
              % (script_path, len(txns), width, height))


if __name__ == "__main__":
    main()
