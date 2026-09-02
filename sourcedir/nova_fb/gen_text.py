#!/usr/bin/env python3
"""Generate the character mode demos for the nova_fb device.

Emits three SimH scripts, all running the SAME Nova program with different
data, because the interesting thing is the card's mode, not the program:

    demo/text80.ini     720x400, 9 dot cell -> 80x25, the MS-DOS VGA text mode
    demo/text30.ini     640x480, 8 dot cell -> 80x30, the mode 12h console
    demo/text_font.ini  720x400 with CHARPTR pointing at glyphs the program
                        loaded itself, overloading the built-in ROM

verify_frames.py imports the message layout from here and recomputes the
expected bitmap from src/nova_charrom.h, so the assertions never just compare
the simulator against itself.

THE PROGRAM is a two level loop over a "chunk" table: each chunk is a count, a
card address, and that many words; a zero count ends the table. Everything the
demo needs -- text cells, and for text_font a whole glyph table -- is display
memory, so one loop loads all of it and the differences between the three
demos are entirely in the data.

Before presenting, the program blocks on a console read (SKPDN 10 / DIA 0,10
-- device 10 is the Nova's TTI): the testlist decides, over the SIMH console,
when the mode change actually happens, rather than it happening the instant
the program is loaded. The byte's value is never inspected, only its arrival;
a single-character send can be swallowed by SIMH's once-a-second WRU (Ctrl-E)
poll, so send a short string (the existing test_sendnovacommand callers
already do -- "go" or similar), not a single character.
"""

import os
import sys

import gen_charrom                   # the shipped ROM, to derive a font from

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.join(HERE, "demo")

CELL_H = 16
CHAR_W = 8

# Cell word: code in bits 7-0, attributes above. Matches FBT_M_* in nova_fb.c.
REVERSE = 0o400
ULINE = 0o1000

# TCTL bits.
T_ENABLE = 0o1
T_CELL9 = 0o2
T_LINEGFX = 0o4

TEXTBUF = 0o4000                    # text cells live here in card memory
FONTBUF = 0o20000                   # ... and a custom glyph table here

# --- the screens ---------------------------------------------------------
# (row, col, text, attribute) -- attribute 0 is plain.

TEXT80 = [
    (1, 2, "NOVA FB - 80x25 VGA TEXT MODE", 0),
    (2, 2, "720x400, 9 dot cell, built-in ASCII ROM", 0),
    (4, 2, "reverse video:", 0),
    (4, 17, " SELECTED ", REVERSE),
    (5, 2, "underline:", 0),
    (5, 17, "FBDRAW.SR", ULINE),
    (7, 2, "ABCDEFGHIJKLMNOPQRSTUVWXYZ 0123456789", 0),
    (8, 2, "abcdefghijklmnopqrstuvwxyz !@#$%&*()", 0),
    (24, 2, "row 24, col 2 - the last row of 25", 0),
]

TEXT30 = [
    (1, 2, "NOVA FB - 80x30 CONSOLE", 0),
    (2, 2, "640x480, 8 dot cell, built-in ASCII ROM", 0),
    (4, 2, "same font, narrower cell, five more rows", 0),
    (29, 2, "row 29, col 2 - the last row of 30", 0),
]

TEXT_FONT = [
    (1, 2, "CUSTOM FONT VIA CHARPTR - THIS IS NOT THE ROM", 0),
    (3, 2, "every glyph here is the built-in one, thickened", 0),
    (4, 2, "by the program before it pointed CHARPTR at them", 0),
    (6, 2, "ABCDEFGHIJKLMNOPQRSTUVWXYZ 0123456789", 0),
]


def bolden(rom, codes):
    """A custom font derived from the ROM: every glyph one pixel thicker.

    The override demo has to be READABLE as well as different. An earlier
    version defined two glyphs (a solid block and a checkerboard) and left the
    other 254 blank, which is a correct demonstration that renders as a screen
    of stray boxes -- indistinguishable, to anyone watching the live window,
    from the run having crashed and cleared the screen.

    Thickening is the VGA bold rule, OR with the glyph shifted one pixel right.
    Derived from the shipped ROM rather than invented, so the frame proves the
    device used the PROGRAM'S table: the letters are legibly the same letters,
    visibly heavier, and nothing the ROM could have produced.

    Every character the layout uses gets a glyph, because in char mode an
    undefined code is not a fallback -- it is a blank cell.
    """
    out = {}
    for code in sorted(codes):
        rows = []
        for r in range(CELL_H):
            bits = (rom[code * CELL_H + r] >> 8) & 0o377
            rows.append((bits | (bits >> 1)) & 0o377)
        out[code] = rows
    return out


CUSTOM = bolden(gen_charrom.read_charrom(),
                {ord(ch) for _r, _c, text, _a in TEXT_FONT for ch in text})


def cells(layout, cols):
    """Layout -> {card address offset: cell word}, relative to TEXTBUF."""
    out = {}
    for row, col, text, attr in layout:
        for i, ch in enumerate(text):
            c = col + i
            if c >= cols:
                raise SystemExit("gen_text: %r overruns %d columns" % (text, cols))
            out[(row * cols) + c] = (ord(ch) & 0o377) | attr
    return out


def chunks_for(layout, cols, custom=None):
    """[(start_address, [words])] -- runs of consecutive cells, plus a font."""
    cell = cells(layout, cols)
    runs, run, start = [], [], None
    for addr in sorted(cell):
        if start is not None and addr == start + len(run):
            run.append(cell[addr])
            continue
        if run:
            runs.append((TEXTBUF + start, run))
        start, run = addr, [cell[addr]]
    if run:
        runs.append((TEXTBUF + start, run))

    if custom:
        for code, rows in sorted(custom.items()):
            runs.append((FONTBUF + (code * CELL_H), [(r & 0o377) << 8 for r in rows]))
    return runs


def program(lines):
    """The fixed loader. Page zero 50-60, program 100-137, chunks from 1000."""
    a = lines.append
    a("; --- page zero constants ---")
    a("d 50 0")                     # zero / first text register address
    a("d 51 20000")                 # ctl: word mode + AUTOINC
    a("d 52 2000")                  # ctl: text register port
    # 53/54/55 (TEXTPTR / CHARPTR / TCTL) are written by the caller.
    a("d 56 1000")                  # chunk table
    a("d 60 0")                     # inner counter (scratch)
    a("; --- phase 1: load the three text registers (text port) ---")
    a("d 100 20052")                # LDA 0,52    ctl = TEXT
    a("d 101 63042")                # DOC 0,42
    a("d 102 20050")                # LDA 0,50    register address 0
    a("d 103 61042")                # DOA 0,42
    a("d 104 24053")                # LDA 1,53    TEXTPTR
    a("d 105 66042")                # DOB 1,42    (port auto-increments)
    a("d 106 24054")                # LDA 1,54    CHARPTR
    a("d 107 66042")                # DOB 1,42
    a("d 110 24055")                # LDA 1,55    TCTL
    a("d 111 66042")                # DOB 1,42
    a("; --- phase 2: write every chunk into display memory (word mode) ---")
    a("d 112 20051")                # LDA 0,51    ctl = word + AUTOINC
    a("d 113 63042")                # DOC 0,42
    a("d 114 30056")                # LDA 2,56    AC2 = chunk table
    a("d 115 25000")                # outer: LDA 1,0,2   count
    a("d 116 125015")               # MOV# 1,1,SNR       skip if count != 0
    a("d 117 000133")               # JMP done
    a("d 120 44060")                # STA 1,60           counter = count
    a("d 121 151400")               # INC 2,2
    a("d 122 25000")                # LDA 1,0,2          card address
    a("d 123 65042")                # DOA 1,42
    a("d 124 151400")               # INC 2,2
    a("d 125 25000")                # inner: LDA 1,0,2   word
    a("d 126 66042")                # DOB 1,42
    a("d 127 151400")               # INC 2,2
    a("d 130 14060")                # DSZ 60
    a("d 131 000125")               # JMP inner
    a("d 132 000115")               # JMP outer
    a("; --- phase 2.5: wait for a command over the console (device 10, TTI) ---")
    a("; before presenting, so the testlist -- not this program -- decides")
    a("; when the mode change actually happens. Any byte satisfies the gate;")
    a("; its value is never inspected.")
    a("d 133 63610")                # done: SKPDN 10
    a("d 134 000133")               # JMP done       (spin until a char arrives)
    a("d 135 60410")                # DIA 0,10       (consume it, clears Done)
    a("; --- phase 3: present ---")
    a("d 136 60342")                # NIOP 42
    a("d 137 63077")                # HALT


def emit(path, width, height, prefix, layout, tctl, charptr, custom, comment):
    cellw = CHAR_W + 1 if (tctl & T_CELL9) else CHAR_W
    cols = width // cellw
    rows = height // CELL_H

    L = []
    a = L.append
    a("; %s" % comment)
    a("; GENERATED BY gen_text.py -- do not edit by hand.")
    a("; %dx%d, %d dot cell -> %d cols x %d rows." % (width, height, cellw, cols, rows))
    a("; Char mode GENERATES the frame from the text buffer, so nothing here")
    a("; writes pixels: the cells and (for the custom font) the glyphs are all")
    a("; that goes into display memory.")
    a("set fb width=%d" % width)
    a("set fb height=%d" % height)
    a("set fb prefix=%s" % prefix)
    a("; --- text registers ---")
    a("d 53 %o" % TEXTBUF)
    a("d 54 %o" % charptr)
    a("d 55 %o" % tctl)
    program(L)

    a("; --- chunk table: count, card address, words... ; 0 ends it ---")
    addr = 0o1000
    for start, words in chunks_for(layout, cols, custom):
        a("d %o %o" % (addr, len(words)))
        addr += 1
        a("d %o %o" % (addr, start))
        addr += 1
        for w in words:
            a("d %o %o" % (addr, w))
            addr += 1
    a("d %o 0" % addr)              # terminator
    # The chunk table is NOVA MAIN MEMORY (these are "d" commands), not card
    # display memory, so the ceiling is the machine's 32KW -- not the 4000 the
    # card's text buffer happens to sit at. A derived font is ~50 glyphs of 16
    # words and would trip a card-memory-sized limit for no reason.
    if addr >= 0o70000:
        raise SystemExit("gen_text: chunk table overruns main memory")

    a("go 100")
    a("e fb frame")
    a("e fb cols")
    a("e fb rows")
    a("quit")

    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")
    print("wrote %s (%d cols x %d rows, %d words of chunks)"
          % (path, cols, rows, addr - 0o1000))


def main():
    if not os.path.isdir(DEMO):
        os.makedirs(DEMO)
    emit(os.path.join(DEMO, "text80.ini"), 720, 400, "output/text80", TEXT80,
         T_ENABLE | T_CELL9 | T_LINEGFX, 0, None,
         "80x25 VGA text mode: 720x400, nine dot cell, built-in ROM.")
    emit(os.path.join(DEMO, "text30.ini"), 640, 480, "output/text30", TEXT30,
         T_ENABLE, 0, None,
         "80x30 console: 640x480, eight dot cell, built-in ROM.")
    emit(os.path.join(DEMO, "text_font.ini"), 720, 400, "output/text_font",
         TEXT_FONT, T_ENABLE | T_CELL9, FONTBUF, CUSTOM,
         "Custom font: CHARPTR points at glyphs the program loaded itself.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
