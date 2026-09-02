#!/usr/bin/env python3
"""Generate demo/fractal.ini -- a title screen (char mode, built-in ROM) then
a classic 8-bit-demo "AND fractal" (Sierpinski gasket) scrolling continuously
across the mono bitmap: FRAME_COUNT full redraws, each one recomputed with an
advancing phase, so the card is genuinely IN MOTION for the length of the
run rather than drawn once and left static.

WHY THE AND FRACTAL
--------------------
`SET pixel (x, y) IF x AND y != 0` is the one-line fractal every home-computer
BASIC demo from the 80s eventually typed in: it needs no multiply, no
trigonometry and no float, just a bitwise AND and a compare to zero -- exactly
what a Nova (no multiply instruction) can do at one pixel per ~10 instructions
in PIXEL mode (see BUILD.txt, PIXEL MODE). The result is the same Sierpinski
gasket you get from Pascal's triangle mod 2.

MAKING IT MOVE: `SET (x, y) IF (x + t) AND y`, t advancing by one every frame.
Sliding the AND test sideways instead of the pixel itself is what a machine
with no blitter and no multiply can do cheaply: every frame is a straight
redraw of the same nested loop with one extra ADD, no need to touch or shift
anything already drawn. The gasket appears to scroll left-to-right and
reknit itself every frame -- the "AND scroller" effect several 80s BASIC demos
used for exactly this reason.

THE PROGRAM, in two phases:
  1. Char mode, built-in ROM (CHARPTR=0): loads a text screen via the text
     register port + word/AUTOINC writes (same shape as gen_text.py's
     loader), presents it -- frame 1 is the title card.
  2. TCTL is cleared (char mode off) and CTL switched to PIXEL mode, then it
     NEVER HALTS: two nested counted loops sweep Y then X over 0..255,
     testing ((x + t) AND y) with one ALC instruction (skip field does the
     branch; nl=True means the result isn't stored, only tested) and issuing
     a SET or a CLEAR pixel op accordingly -- a full redraw, not just
     additions, which is what makes pixels that were lit turn back off as the
     phase slides past them. One present per frame, t incremented after, and
     the outer loop is unconditional -- same shape as modeswitch.ini, which
     also never halts. It runs, and scrolls, until something stops the
     simulator (test_terminate_all, or Ctrl-E/quit at a console). There is no
     frame count baked into the program to be "the end"; the testlist watches
     it run for a while and checks whatever frame happens to be live when it
     looks (see verify_live.py's technique), then tears it down.

Assembled with gen_modeswitch.Asm, the same small two-pass Nova assembler
that program uses -- this one has no subroutines, but the loop back-edges are
still easiest to get right with labels rather than hand-picked octal
displacements.
"""

import os
import sys

import gen_modeswitch                 # Asm -- the assembler
import gen_text                       # TEXTBUF, T_ENABLE, chunks_for

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.join(HERE, "demo")

FB_DEV = 0o42

CTL_TEXT = 0o2000                     # DOA/DOB address the text register port
CTL_WORD_AUTOINC = 0o20000            # word writes, auto-incrementing address
CTL_PIXEL = 0o10000                   # DOA/DOB are X / Y+op
OP_CLEAR = 0o20000                    # pixel op field (bits 14-13) = 1: CLEAR

# NOT gen_text.TEXTBUF (0o4000): that address is INSIDE this card's own
# 256x256 bitmap (word addresses 0-0o7777), so the title screen's character
# codes would sit right under the fractal and bleed through as stray pixels.
# 0o10000 is the first word address past the whole bitmap.
TEXTBUF = 0o10000
T_ENABLE = gen_text.T_ENABLE

WIDTH = HEIGHT = 256                  # 256x256 mono canvas, 32x16 text cells
COLS = WIDTH // gen_text.CHAR_W
PREFIX = "output/fractal"

CODE_ORG = 0o400
DATA_ORG = 0o1000

TITLE = [
    (2, 3, "NOVA FB - AND FRACTAL SCROLL", 0),
    (4, 3, "SET (x,y) IF (x+t) AND y", 0),
    (6, 3, "pascal's triangle mod 2,", 0),
    (7, 2, "re-knit every frame, t sliding", 0),
    (13, 3, "watch it flow ... never halts", 0),
]


def chunk_words_at(layout, cols, base):
    """Same shape as gen_modeswitch.chunk_words, but at an explicit base
    address instead of gen_text.TEXTBUF (see the TEXTBUF comment above)."""
    cell = gen_text.cells(layout, cols)
    runs, run, start = [], [], None
    for addr in sorted(cell):
        if start is not None and addr == start + len(run):
            run.append(cell[addr])
            continue
        if run:
            runs.append((base + start, run))
        start, run = addr, [cell[addr]]
    if run:
        runs.append((base + start, run))

    words = []
    for caddr, run in runs:
        words.append(len(run))
        words.append(caddr)
        words.extend(run)
    words.append(0)
    return words


def build(asm):
    # --- page zero: constants -------------------------------------------
    asm.pz("ZERO", 0)
    asm.pz("TWO", 2)
    asm.pz("K256", WIDTH)
    asm.pz("OPCLEAR", OP_CLEAR)
    asm.pz("CTLTEXT", CTL_TEXT)
    asm.pz("CTLWORDAI", CTL_WORD_AUTOINC)
    asm.pz("CTLPIXEL", CTL_PIXEL)
    asm.pz("TEXTBUFA", TEXTBUF)
    asm.pz("TENABLE", T_ENABLE)
    asm.pz("CHUNKP", ("sym", "CHUNKTAB"))
    # --- page zero: variables --------------------------------------------
    asm.pz("CNT", 0)
    asm.pz("TVAL", 0)                   # the scroll phase, persists across frames
    asm.pz("XVAL", 0)
    asm.pz("YVAL", 0)
    asm.pz("XCTR", 0)
    asm.pz("YCTR", 0)

    # =====================================================================
    asm.org(CODE_ORG)
    asm.label("START")

    # --- phase 1: char mode title screen, built-in ROM -------------------
    asm.lda(0, "CTLTEXT")
    asm.io("DOC", 0, FB_DEV)
    asm.lda(0, "ZERO")
    asm.io("DOA", 0, FB_DEV)            # select register 0 (TEXTPTR)
    asm.lda(1, "TEXTBUFA")
    asm.io("DOB", 1, FB_DEV)            # TEXTPTR, autoincs to reg 1
    asm.lda(1, "ZERO")
    asm.io("DOB", 1, FB_DEV)            # CHARPTR = 0, the built-in ROM
    asm.lda(1, "TENABLE")
    asm.io("DOB", 1, FB_DEV)            # TCTL = ENABLE (8 dot cell, no gfx)

    asm.lda(0, "CTLWORDAI")
    asm.io("DOC", 0, FB_DEV)
    asm.lda(2, "CHUNKP")
    asm.label("LCOUT")
    asm.lda(1, 0, index=2)              # count
    asm.alc("MOV", 1, 1, nl=True, skip="SNR")
    asm.jmp("LCDONE")
    asm.sta(1, "CNT")
    asm.alc("INC", 2, 2)
    asm.lda(1, 0, index=2)              # card address
    asm.io("DOA", 1, FB_DEV)
    asm.alc("INC", 2, 2)
    asm.label("LCIN")
    asm.lda(1, 0, index=2)
    asm.io("DOB", 1, FB_DEV)
    asm.alc("INC", 2, 2)
    asm.dsz("CNT")
    asm.jmp("LCIN")
    asm.jmp("LCOUT")
    asm.label("LCDONE")

    asm.io("NIO", 0, FB_DEV, "P")       # present frame 1: the title card

    # --- phase 2: switch off char mode, switch to pixel mode -------------
    asm.lda(0, "CTLTEXT")
    asm.io("DOC", 0, FB_DEV)
    asm.lda(0, "TWO")                   # select register 2 (TCTL)
    asm.io("DOA", 0, FB_DEV)
    asm.lda(1, "ZERO")
    asm.io("DOB", 1, FB_DEV)            # TCTL = 0, char mode off

    asm.lda(0, "CTLPIXEL")
    asm.io("DOC", 0, FB_DEV)

    asm.lda(0, "ZERO")
    asm.sta(0, "TVAL")

    # --- the AND-scroll: full redraws forever, phase advancing every frame -
    asm.label("OUTERFRAME")
    asm.lda(0, "ZERO")
    asm.sta(0, "YVAL")
    asm.lda(0, "K256")
    asm.sta(0, "YCTR")

    asm.label("OUTERY")
    asm.lda(0, "ZERO")
    asm.sta(0, "XVAL")
    asm.lda(0, "K256")
    asm.sta(0, "XCTR")

    asm.label("INNERX")
    asm.lda(0, "XVAL")
    asm.lda(2, "TVAL")
    asm.alc("ADD", 2, 0)                 # AC0 = TVAL + XVAL  (x + t)
    asm.lda(1, "YVAL")
    asm.alc("AND", 0, 1, nl=True, skip="SNR")   # skip DOCLR when (x+t) & y != 0
    asm.jmp("DOCLR")
    # --- SET path: (x+t) & y != 0 -----------------------------------------
    asm.lda(0, "XVAL")
    asm.io("DOA", 0, FB_DEV)
    asm.lda(1, "YVAL")
    asm.io("DOB", 1, FB_DEV)            # op = SET (0)
    asm.jmp("NEXTX")
    # --- CLEAR path: (x+t) & y == 0 -- must actively blank it, this is a ---
    # --- full redraw every frame, not just an accumulating one ------------
    asm.label("DOCLR")
    asm.lda(0, "XVAL")
    asm.io("DOA", 0, FB_DEV)
    asm.lda(2, "OPCLEAR")
    asm.lda(1, "YVAL")
    asm.alc("ADD", 2, 1)                 # AC1 = OPCLEAR + YVAL
    asm.io("DOB", 1, FB_DEV)             # op = CLEAR (1)
    asm.label("NEXTX")
    asm.lda(0, "XVAL")
    asm.alc("INC", 0, 0)
    asm.sta(0, "XVAL")
    asm.dsz("XCTR")
    asm.jmp("INNERX")

    asm.lda(0, "YVAL")
    asm.alc("INC", 0, 0)
    asm.sta(0, "YVAL")
    asm.dsz("YCTR")
    asm.jmp("OUTERY")

    asm.io("NIO", 0, FB_DEV, "P")       # one frame fully redrawn: present it
    asm.lda(0, "TVAL")
    asm.alc("INC", 0, 0)
    asm.sta(0, "TVAL")
    asm.jmp("OUTERFRAME")               # unconditional -- this never halts,
                                        # same as gen_modeswitch.py's program;
                                        # something external stops it.

    code_end = asm.pc

    # =====================================================================
    asm.org(DATA_ORG)
    asm.label("CHUNKTAB")
    asm.block(chunk_words_at(TITLE, COLS, TEXTBUF))

    if asm.pc >= 0o70000:
        raise SystemExit("gen_fractal: program overruns main memory")
    return code_end, asm.pc


def assemble():
    first = gen_modeswitch.Asm()
    build(first)
    second = gen_modeswitch.Asm(syms=first.defined)
    code_end, data_end = build(second)
    return second, code_end, data_end


def emit(path):
    asm, code_end, data_end = assemble()
    L = []
    a = L.append
    a("; Title card (char mode, built-in ROM) then a scrolling AND fractal:")
    a("; SET (x,y) iff (x+t) AND y != 0, redrawn every frame with t advancing")
    a("; -- continuous motion, not a static build-up. Like modeswitch.ini,")
    a("; this program NEVER HALTS: 'go' below will not return on its own,")
    a("; so nothing follows it in this script -- something external (the")
    a("; testlist's test_terminate_all, or Ctrl-E/quit at a console) stops")
    a("; the simulator.")
    a("set fb width=%d" % WIDTH)
    a("set fb height=%d" % HEIGHT)
    a("set fb prefix=%s" % PREFIX)
    for addr in sorted(asm.mem):
        a("d %o %o" % (addr, asm.mem[addr]))
    a("go %o" % asm.defined["START"])

    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")
    print("wrote %s (code %o-%o, data %o-%o, %d words deposited)"
          % (path, CODE_ORG, code_end - 1, DATA_ORG, data_end - 1, len(asm.mem)))


def main():
    if not os.path.isdir(DEMO):
        os.makedirs(DEMO)
    emit(os.path.join(DEMO, "fractal.ini"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
