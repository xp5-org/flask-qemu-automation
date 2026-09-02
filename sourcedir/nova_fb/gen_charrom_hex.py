#!/usr/bin/env python3
"""Emit src/nova_charrom.hex -- fb_card.v's built-in font ROM, as a Verilog
$readmemh file (one 4-hex-digit word per line, 4096 lines).

Same single-source-of-truth discipline as verilator_vga/gen_font.py: this
reads the ALREADY-GENERATED src/nova_charrom.h via gen_charrom.read_charrom()
rather than re-rasterizing the font, so the RTL ROM and the C model's ROM are
provably the same 4096 words -- the whole point of swapping the C rendering
path for RTL is that the two must draw identically. Re-run this only after
gen_charrom.py has been re-run.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "src", "nova_charrom.hex")

sys.path.insert(0, HERE)
import gen_charrom


def main():
    words = gen_charrom.read_charrom()
    with open(OUT, "w") as f:
        for w in words:
            f.write("%04x\n" % (w & 0xFFFF))
    print("wrote %s (%d words)" % (OUT, len(words)))


if __name__ == "__main__":
    main()
