#!/usr/bin/env python3
"""Generate demo/modeswitch.ini -- ONE Nova program, three character modes.

WHY THIS EXISTS
---------------
gen_text.py emits three SimH scripts, each loading its own copy of the same
loader with different data. That was a proof of concept: it demonstrated the
card's character mode, but it demonstrated it three times, from three
separately-loaded programs, with the mode chosen before anything ran. Nothing
in it ever switched a mode.

This is the merged version: ONE program, loaded once, that owns all three
modes and switches between them at runtime in response to a character typed at
the console. It never halts. That makes the card's output a display a person
is sitting in front of rather than a batch of stills -- which is the point of
the live sink and the pygame monitor.

    1   80x25, nine dot cell, built-in ROM, line graphics
    2   90x25, eight dot cell, built-in ROM
    3   80x25, nine dot cell, the program's OWN font (CHARPTR)

Type the digit and RETURN at the console; the program echoes, switches TCTL /
CHARPTR, repaints the text buffer and presents. Every present is a new frame:
a new output/modeswitch####.png AND a new frame in the live sink, so a mode
switch is visible in the window the moment RETURN is pressed.

ONE RESOLUTION, DELIBERATELY. The card is set to 720x400 for the whole run and
the program never changes it, because it CANNOT: WIDTH and HEIGHT are card
settings (SET FB WIDTH/HEIGHT), not registers on the text port -- see
FBT_R_TEXTPTR/CHARPTR/CTL in src/nova_fb.c, which is the whole register set a
program can reach. So the three modes here differ in exactly what a program
can actually change: cell width, line graphics, and the font. Mode 2 is
therefore 90x25 (720 / 8) rather than gen_text's 80x30, which needed a 640x480
card. COLS = WIDTH / cell width and ROWS = HEIGHT / 16 as always.

THE PROGRAM is assembled here, by the small two-pass assembler below, instead
of being hand-written as octal `d` lines. gen_text.py's loader was ~30
instructions with no subroutines and hand-assembling it was reasonable; this
one has console I/O, string output, a command parser and four subroutines, and
hand-picking PC-relative displacements for that is how you get a demo that
halts on a typo. The output is still nothing but `d` deposits.
"""

import os
import sys

import gen_charrom
import gen_text                       # cell/chunk packing and the ROM-derived font

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.join(HERE, "demo")

FB_DEV = 0o42                         # framebuffer card
TTI_DEV = 0o10                        # console in
TTO_DEV = 0o11                        # console out
CPU_DEV = 0o77

CTL_TEXT = 0o2000                     # DOA/DOB address the text register port
CTL_WORD_AUTOINC = 0o20000            # word writes, auto-incrementing address

T_ENABLE = gen_text.T_ENABLE
T_CELL9 = gen_text.T_CELL9
T_LINEGFX = gen_text.T_LINEGFX

TEXTBUF = gen_text.TEXTBUF            # 04000, card display memory
FONTBUF = gen_text.FONTBUF            # 020000

WIDTH = 720
HEIGHT = 400
PREFIX = "output/modeswitch"

CODE_ORG = 0o400                      # page zero is variables; code starts here
DATA_ORG = 0o2000                     # messages, mode table, chunk tables

REVERSE = gen_text.REVERSE
ULINE = gen_text.ULINE

# --- the three screens ---------------------------------------------------
# Each says which mode it is and what to press next, because the screen is now
# the thing a person is looking at while they drive the program.

MODE1 = [
    (1, 2, "NOVA FB - MODE 1 - 80x25, NINE DOT CELL", 0),
    (2, 2, "720x400, built-in ASCII ROM, line graphics on", 0),
    (4, 2, "reverse video:", 0),
    (4, 17, " SELECTED ", REVERSE),
    (5, 2, "underline:", 0),
    (5, 17, "FBDRAW.SR", ULINE),
    (7, 2, "ABCDEFGHIJKLMNOPQRSTUVWXYZ 0123456789", 0),
    (8, 2, "abcdefghijklmnopqrstuvwxyz !@#$%&*()", 0),
    (10, 2, "press 2 or 3 then RETURN at the terminal", 0),
    (24, 2, "row 24, col 2 - the last row of 25", 0),
]

MODE2 = [
    (1, 2, "NOVA FB - MODE 2 - 90x25, EIGHT DOT CELL", 0),
    (2, 2, "same 720x400 card, same ROM - only the cell width changed", 0),
    (4, 2, "eighty columns of digits, and ten columns still to spare:", 0),
    (5, 2, "0123456789" * 8, 0),
    (7, 2, "reverse video:", 0),
    (7, 17, " SELECTED ", REVERSE),
    (10, 2, "press 1 or 3 then RETURN at the terminal", 0),
    (24, 2, "row 24, col 2 - the last row of 25", 0),
]

MODE3 = [
    (1, 2, "MODE 3 - CUSTOM FONT VIA CHARPTR - NOT THE ROM", 0),
    (3, 2, "every glyph here is the built-in one, thickened", 0),
    (4, 2, "by the program before it pointed CHARPTR at them", 0),
    (6, 2, "ABCDEFGHIJKLMNOPQRSTUVWXYZ 0123456789", 0),
    (8, 2, "press 1 or 2 then RETURN at the terminal", 0),
]

CUSTOM = gen_text.bolden(gen_charrom.read_charrom(),
                         {ord(ch) for _r, _c, t, _a in MODE3 for ch in t})

# (label, layout, cols, rows, tctl, charptr, custom font or None)
MODES = [
    ("MODE1", MODE1, WIDTH // 9, HEIGHT // gen_text.CELL_H,
     T_ENABLE | T_CELL9 | T_LINEGFX, 0, None),
    ("MODE2", MODE2, WIDTH // 8, HEIGHT // gen_text.CELL_H,
     T_ENABLE, 0, None),
    ("MODE3", MODE3, WIDTH // 9, HEIGHT // gen_text.CELL_H,
     T_ENABLE | T_CELL9, FONTBUF, CUSTOM),
]


# =========================================================================
# A two pass Nova assembler, just enough for this program.
# =========================================================================

_ALC_FUNC = {"COM": 0, "NEG": 1, "MOV": 2, "INC": 3,
             "ADC": 4, "SUB": 5, "ADD": 6, "AND": 7}
_ALC_SH = {"": 0, "L": 1, "R": 2, "S": 3}
_ALC_CY = {"": 0, "Z": 1, "O": 2, "C": 3}
_ALC_SKIP = {"": 0, "SKP": 1, "SZC": 2, "SNC": 3,
             "SZR": 4, "SNR": 5, "SEZ": 6, "SBN": 7}
_MEM_OP = {"JMP": 0o000000, "JSR": 0o004000, "ISZ": 0o010000,
           "DSZ": 0o014000, "LDA": 0o020000, "STA": 0o040000}
_IO_FUNC = {"NIO": 0, "DIA": 1, "DOA": 2, "DIB": 3,
            "DOB": 4, "DIC": 5, "DOC": 6, "SKP": 7}
_IO_CTRL = {"": 0, "S": 1, "C": 2, "P": 3}


class Asm(object):
    """Emits {address: word}. Run it twice: the first pass collects symbol
    addresses (every reference reads 0 and every instruction is still exactly
    one word, so addresses do not move), the second pass assembles for real.

    Page zero doubles as the register file on a Nova -- an 8 bit displacement
    reaches 0-0377 from anywhere -- so every variable and constant is a page
    zero word handed out by .pz(). Code lives above it and jumps within itself
    PC-relative, which is checked here rather than discovered at run time.
    """

    def __init__(self, syms=None):
        self.syms = syms or {}
        self.defined = {}
        self.mem = {}
        self.pc = CODE_ORG
        self._pz_next = 0o40
        self._pz = {}

    # --- placement -------------------------------------------------------
    def org(self, addr):
        self.pc = addr

    def label(self, name):
        if name in self.defined:
            raise SystemExit("gen_modeswitch: duplicate label %s" % name)
        self.defined[name] = self.pc
        return self.pc

    def ref(self, name):
        """Address of a label. 0 on the first pass, which is why nothing may
        change SIZE based on a reference."""
        return self.syms.get(name, 0)

    def emit(self, word):
        if self.pc in self.mem:
            raise SystemExit("gen_modeswitch: overlap at %o" % self.pc)
        self.mem[self.pc] = word & 0o177777
        self.pc += 1

    def block(self, words):
        for w in words:
            self.emit(w)

    def pz(self, name, value=0):
        """Allocate (once) a page zero word. `value` may be ('sym', label)."""
        if name not in self._pz:
            addr = self._pz_next
            self._pz_next += 1
            if addr > 0o377:
                raise SystemExit("gen_modeswitch: page zero full")
            self._pz[name] = addr
            self.defined[name] = addr
        addr = self._pz[name]
        if isinstance(value, tuple) and value[0] == "sym":
            self.mem[addr] = self.ref(value[1]) & 0o177777
        else:
            self.mem[addr] = value & 0o177777
        return addr

    # --- instructions ----------------------------------------------------
    def _mem(self, op, ac, target, ind=False, index=None):
        addr = self.ref(target) if isinstance(target, str) else target
        pc = self.pc
        if index is None:
            if 0 <= addr <= 0o377:
                index, disp = 0, addr
            else:
                d = addr - pc
                if not (-128 <= d <= 127):
                    raise SystemExit(
                        "gen_modeswitch: %s %s out of PC-relative reach "
                        "(%o from %o) -- go indirect through a page zero word"
                        % (op, target, addr, pc))
                index, disp = 1, d & 0o377
        else:
            disp = addr & 0o377
        word = (_MEM_OP[op] | ((ac & 3) << 11 if op in ("LDA", "STA") else 0)
                | (0o2000 if ind else 0) | ((index & 3) << 8) | (disp & 0o377))
        self.emit(word)

    def lda(self, ac, target, ind=False, index=None):
        self._mem("LDA", ac, target, ind, index)

    def sta(self, ac, target, ind=False, index=None):
        self._mem("STA", ac, target, ind, index)

    def jmp(self, target, ind=False, index=None):
        self._mem("JMP", 0, target, ind, index)

    def jsr(self, target, ind=False, index=None):
        self._mem("JSR", 0, target, ind, index)

    def dsz(self, target, ind=False, index=None):
        self._mem("DSZ", 0, target, ind, index)

    def isz(self, target, ind=False, index=None):
        self._mem("ISZ", 0, target, ind, index)

    def ret(self):
        """JMP 0,3 -- JSR left the return address in AC3."""
        self._mem("JMP", 0, 0, index=3)

    def alc(self, func, acs, acd, sh="", cy="", nl=False, skip=""):
        self.emit(0o100000 | ((acs & 3) << 13) | ((acd & 3) << 11)
                  | (_ALC_FUNC[func] << 8) | (_ALC_SH[sh] << 6)
                  | (_ALC_CY[cy] << 4) | (0o10 if nl else 0)
                  | _ALC_SKIP[skip])

    def io(self, func, ac, dev, ctrl=""):
        self.emit(0o60000 | ((ac & 3) << 11) | (_IO_FUNC[func] << 8)
                  | (_IO_CTRL[ctrl] << 6) | (dev & 0o77))

    def skpdn(self, dev):
        self.io("SKP", 0, dev, "C")

    def halt(self):
        self.io("DOC", 0, CPU_DEV)


# =========================================================================
# The program
# =========================================================================

BANNER = (
    "\r\nnova_fb character mode -- one program, three modes\r\n"
    "  1   80x25, nine dot cell, built-in ROM, line graphics\r\n"
    "  2   90x25, eight dot cell, built-in ROM\r\n"
    "  3   80x25, nine dot cell, the program's own font\r\n"
    "type a digit then RETURN; the card presents a frame each time\r\n"
)
PROMPT = "\r\nmode> "
OKMSG = "presenting mode "
HELPMSG = "expected 1, 2 or 3\r\n"


def _msg_words(text):
    return [ord(c) & 0o377 for c in text] + [0]


def chunk_words(layout, cols, custom=None):
    """The mode's screen as a count/address/words... table, 0 terminated.

    Same shape gen_text.py's loader consumed, and for the same reason: the
    text cells and (for mode 3) the glyph table are both just display memory,
    so one loop loads either.
    """
    words = []
    for start, run in gen_text.chunks_for(layout, cols, custom):
        words.append(len(run))
        words.append(start)
        words.extend(run)
    words.append(0)
    return words


def build(asm):
    # --- page zero: constants ------------------------------------------
    asm.pz("ZERO", 0)
    asm.pz("KNEG1", 0o177777)
    asm.pz("CTLTEXT", CTL_TEXT)
    asm.pz("CTLWORD", CTL_WORD_AUTOINC)
    asm.pz("TEXTBUFA", TEXTBUF)
    asm.pz("BLANKC", 0)                     # an undefined code is a blank cell
    asm.pz("MASK177", 0o177)                # console chars arrive 7 bit + junk
    asm.pz("CCR", 0o15)
    asm.pz("CLF", 0o12)
    asm.pz("C1", 0o61)
    asm.pz("C2", 0o62)
    asm.pz("C3", 0o63)
    asm.pz("MODETABP", ("sym", "MODETAB"))
    asm.pz("MSGBANNP", ("sym", "MSGBANN"))
    asm.pz("MSGPROMP", ("sym", "MSGPROM"))
    asm.pz("MSGOKP", ("sym", "MSGOK"))
    asm.pz("MSGHELPP", ("sym", "MSGHELP"))
    # --- page zero: variables ------------------------------------------
    asm.pz("MODEIDX", 0)                    # 0..2, the mode on screen
    asm.pz("PEND", 0o177777)                # digit typed but not entered yet
    asm.pz("TCTLV", 0)
    asm.pz("CHARPTV", 0)
    asm.pz("NCLEAR", 0)
    asm.pz("CHUNKP", 0)
    asm.pz("CNT", 0)
    asm.pz("PUTSR", 0)                      # saved AC3, one per subroutine
    asm.pz("CLRR", 0)
    asm.pz("LCR", 0)
    asm.pz("SHOWR", 0)

    # =================================================================
    asm.org(CODE_ORG)
    asm.label("START")
    asm.lda(2, "MSGBANNP")
    asm.jsr("PUTS")
    asm.lda(0, "ZERO")
    asm.sta(0, "MODEIDX")
    asm.lda(0, "KNEG1")
    asm.sta(0, "PEND")
    asm.jsr("SHOWMODE")                     # mode 1 is on screen before any key

    asm.label("PROMPT")
    asm.lda(2, "MSGPROMP")
    asm.jsr("PUTS")

    # --- the console loop ----------------------------------------------
    # Reads one character at a time and never blocks the card: nothing else is
    # running, so a spin on SKPDN is the whole scheduler.
    asm.label("READ")
    asm.skpdn(TTI_DEV)
    asm.jmp("READ")
    asm.io("DIA", 0, TTI_DEV, "C")          # DIAC: read AND clear Done, or the
                                            # next SKPDN sees this same char
    asm.lda(1, "MASK177")
    asm.alc("AND", 1, 0)

    asm.lda(1, "CCR")                       # RETURN?
    asm.alc("SUB", 1, 0, nl=True, skip="SZR")
    asm.jmp("NOTCR")
    asm.jmp("DOCR")
    asm.label("NOTCR")
    asm.lda(1, "CLF")                       # ... or a bare LF, same thing
    asm.alc("SUB", 1, 0, nl=True, skip="SZR")
    asm.jmp("NOTLF")
    asm.jmp("DOCR")

    asm.label("NOTLF")
    asm.jsr("PUTC")                         # echo -- SIMH's console does not
    asm.lda(1, "C1")
    asm.alc("SUB", 1, 0, nl=True, skip="SZR")
    asm.jmp("NOT1")
    asm.jmp("SET0")
    asm.label("NOT1")
    asm.lda(1, "C2")
    asm.alc("SUB", 1, 0, nl=True, skip="SZR")
    asm.jmp("NOT2")
    asm.jmp("SET1")
    asm.label("NOT2")
    asm.lda(1, "C3")
    asm.alc("SUB", 1, 0, nl=True, skip="SZR")
    asm.jmp("READ")                         # anything else: echoed, ignored
    asm.jmp("SET2")

    asm.label("SET0")
    asm.lda(0, "ZERO")
    asm.jmp("SETPEND")
    asm.label("SET1")
    asm.lda(0, "ZERO")
    asm.alc("INC", 0, 0)
    asm.jmp("SETPEND")
    asm.label("SET2")
    asm.lda(0, "ZERO")
    asm.alc("INC", 0, 0)
    asm.alc("INC", 0, 0)
    asm.label("SETPEND")
    asm.sta(0, "PEND")
    asm.jmp("READ")

    # --- RETURN: act on the digit --------------------------------------
    asm.label("DOCR")
    asm.lda(0, "CCR")
    asm.jsr("PUTC")
    asm.lda(0, "CLF")
    asm.jsr("PUTC")
    asm.lda(0, "PEND")
    asm.lda(1, "KNEG1")
    asm.alc("SUB", 1, 0, nl=True, skip="SZR")
    asm.jmp("APPLY")
    asm.jmp("BADIN")

    asm.label("APPLY")
    asm.sta(0, "MODEIDX")                   # SUB# did not load, AC0 is PEND
    asm.jsr("SHOWMODE")
    asm.lda(2, "MSGOKP")
    asm.jsr("PUTS")
    asm.lda(0, "MODEIDX")
    asm.lda(1, "C1")
    asm.alc("ADD", 1, 0)
    asm.jsr("PUTC")
    asm.lda(0, "CCR")
    asm.jsr("PUTC")
    asm.lda(0, "CLF")
    asm.jsr("PUTC")
    asm.jmp("RESETP")

    asm.label("BADIN")
    asm.lda(2, "MSGHELPP")
    asm.jsr("PUTS")

    asm.label("RESETP")
    asm.lda(0, "KNEG1")
    asm.sta(0, "PEND")
    asm.jmp("PROMPT")

    # --- PUTC: AC0 -> console ------------------------------------------
    asm.label("PUTC")
    asm.io("DOA", 0, TTO_DEV, "S")          # DOAS: sets Busy, clears Done, so
                                            # the wait below cannot see a stale
                                            # Done from the previous character
    asm.label("PUTCW")
    asm.skpdn(TTO_DEV)
    asm.jmp("PUTCW")
    asm.ret()

    # --- PUTS: AC2 -> a 0 terminated word-per-character string ---------
    asm.label("PUTS")
    asm.sta(3, "PUTSR")
    asm.label("PUTS0")
    asm.lda(0, 0, index=2)
    asm.alc("MOV", 0, 0, nl=True, skip="SNR")
    asm.jmp("PUTS1")
    asm.jsr("PUTC")
    asm.alc("INC", 2, 2)
    asm.jmp("PUTS0")
    asm.label("PUTS1")
    asm.lda(3, "PUTSR")
    asm.ret()

    # --- CLEARBUF: NCLEAR blank cells at TEXTBUF ------------------------
    # Char mode generates the frame from the whole buffer, so a switch from a
    # 90 column screen to an 80 column one would otherwise leave the old
    # screen's tail cells lit at the new geometry.
    asm.label("CLEARBUF")
    asm.sta(3, "CLRR")
    asm.lda(0, "CTLWORD")
    asm.io("DOC", 0, FB_DEV)
    asm.lda(1, "TEXTBUFA")
    asm.io("DOA", 1, FB_DEV)
    asm.lda(0, "NCLEAR")
    asm.sta(0, "CNT")
    asm.lda(1, "BLANKC")
    asm.label("CLR0")
    asm.io("DOB", 1, FB_DEV)
    asm.dsz("CNT")
    asm.jmp("CLR0")
    asm.lda(3, "CLRR")
    asm.ret()

    # --- LOADCHUNKS: CHUNKP -> display memory ---------------------------
    asm.label("LOADCH")
    asm.sta(3, "LCR")
    asm.lda(0, "CTLWORD")
    asm.io("DOC", 0, FB_DEV)
    asm.lda(2, "CHUNKP")
    asm.label("LCOUT")
    asm.lda(1, 0, index=2)                  # count
    asm.alc("MOV", 1, 1, nl=True, skip="SNR")
    asm.jmp("LCDONE")
    asm.sta(1, "CNT")
    asm.alc("INC", 2, 2)
    asm.lda(1, 0, index=2)                  # card address
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
    asm.lda(3, "LCR")
    asm.ret()

    # --- SETREGS: the three text registers, one DOA and three DOBs ------
    asm.label("SETREGS")
    asm.lda(0, "CTLTEXT")
    asm.io("DOC", 0, FB_DEV)
    asm.lda(0, "ZERO")
    asm.io("DOA", 0, FB_DEV)                # select register 0; DOB autoincs
    asm.lda(1, "TEXTBUFA")
    asm.io("DOB", 1, FB_DEV)
    asm.lda(1, "CHARPTV")
    asm.io("DOB", 1, FB_DEV)
    asm.lda(1, "TCTLV")
    asm.io("DOB", 1, FB_DEV)
    asm.ret()

    # --- SHOWMODE: MODEIDX -> a presented frame -------------------------
    asm.label("SHOWMODE")
    asm.sta(3, "SHOWR")
    asm.lda(0, "MODEIDX")
    asm.alc("MOV", 0, 0, sh="L", cy="Z")    # * 4: four words per table entry
    asm.alc("MOV", 0, 0, sh="L", cy="Z")    # (Z zeroes carry first -- MOVL
                                            # rotates carry IN at bit 0)
    asm.lda(1, "MODETABP")
    asm.alc("ADD", 1, 0)
    asm.alc("MOV", 0, 2)
    asm.lda(0, 0, index=2)
    asm.sta(0, "TCTLV")
    asm.lda(0, 1, index=2)
    asm.sta(0, "CHARPTV")
    asm.lda(0, 2, index=2)
    asm.sta(0, "NCLEAR")
    asm.lda(0, 3, index=2)
    asm.sta(0, "CHUNKP")
    asm.jsr("CLEARBUF")
    asm.jsr("LOADCH")
    asm.jsr("SETREGS")
    asm.io("NIO", 0, FB_DEV, "P")           # NIOP: present
    asm.lda(3, "SHOWR")
    asm.ret()

    code_end = asm.pc

    # =================================================================
    asm.org(DATA_ORG)
    asm.label("MSGBANN")
    asm.block(_msg_words(BANNER))
    asm.label("MSGPROM")
    asm.block(_msg_words(PROMPT))
    asm.label("MSGOK")
    asm.block(_msg_words(OKMSG))
    asm.label("MSGHELP")
    asm.block(_msg_words(HELPMSG))

    asm.label("MODETAB")
    for i, (name, _layout, cols, rows, tctl, charptr, _custom) in enumerate(MODES):
        asm.emit(tctl)
        asm.emit(charptr)
        asm.emit(cols * rows)
        asm.emit(asm.ref("CHUNK%d" % i))

    for i, (name, layout, cols, _rows, _tctl, _cp, custom) in enumerate(MODES):
        asm.label("CHUNK%d" % i)
        asm.block(chunk_words(layout, cols, custom))

    if asm.pc >= 0o70000:
        raise SystemExit("gen_modeswitch: program overruns main memory")
    return code_end, asm.pc


def assemble():
    first = Asm()
    build(first)
    second = Asm(syms=first.defined)
    code_end, data_end = build(second)
    return second, code_end, data_end


def emit(path):
    asm, code_end, data_end = assemble()
    L = []
    a = L.append
    a("; ONE Nova program, three character modes, switched from the console.")
    a("; GENERATED BY gen_modeswitch.py -- do not edit by hand.")
    a("; %dx%d card; mode 1/3 are 9 dot -> %d cols, mode 2 is 8 dot -> %d cols,"
      % (WIDTH, HEIGHT, WIDTH // 9, WIDTH // 8))
    a("; %d rows throughout (HEIGHT / %d)." % (HEIGHT // gen_text.CELL_H,
                                               gen_text.CELL_H))
    a("; The program does NOT halt: it waits on the console (device %o) and"
      % TTI_DEV)
    a("; presents a new frame for every 1/2/3 followed by RETURN.")
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
    emit(os.path.join(DEMO, "modeswitch.ini"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
