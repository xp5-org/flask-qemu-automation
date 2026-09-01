#!/usr/bin/env python3
"""Self-check for gen/malloctest.ini (built from src/malloctest.c).

Unlike fractal.c this program is deterministic and halts, so this can
recompute the exact expected final frame -- every title line, grid cell,
and log row -- by replaying the same sequence of fb_puts/mark_range/
log_line calls main() makes, then OCR-decoding the actual PNG (via the
shipped character ROM) and diffing strings instead of raw pixels.

The numbers baked in below (HEAP_WORDS effectively 1024, 28 probe chunks,
the aliasing addresses) were themselves detected by src/malloctest.c at
runtime, not assumed -- see that file's header comment. If a future
allocator change alters any of them, this script's replay disagrees with
the real PNG and the test fails loudly, which is the point.
"""
import glob
import os
import sys

NOVA_FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nova_fb")
sys.path.insert(0, NOVA_FB)
import verify_frames as V   # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

WIDTH = 640
HEIGHT = 480
COLS = 80
ROWS = 30
GRID_ROW0 = 3
GRID_ROWS = 16
LOG_ROW0 = 21
LOG_ROWS = 4

PROBE_CHUNK = 32
BYTES_PER_CELL = 2


def _cell_text(text, row, col0=2):
    """fb_puts's own truncate-at-COLS rule -- never wraps into the next row."""
    return text[: COLS - col0]


def build_expected():
    """Replay src/malloctest.c's main() call-by-call: returns
    {(row, col): char} for every text cell non-blank in the last frame."""
    cells = {}

    def put_line(row, text, col0=2):
        t = _cell_text(text, row, col0)
        for i, ch in enumerate(t):
            cells[(row, col0 + i)] = ch

    def mark_range(start, length, ch):
        off = start
        while off < start + length:
            cell = off // BYTES_PER_CELL
            if cell < GRID_ROWS * COLS:
                row = GRID_ROW0 + cell // COLS
                col = cell % COLS
                cells[(row, col)] = chr(ch)
            off += BYTES_PER_CELL

    log_row = [0]

    def log_line(text):
        row = LOG_ROW0 + log_row[0]
        for col in range(2, COLS):
            cells[(row, col)] = ' '
        put_line(row, text)
        log_row[0] = (log_row[0] + 1) % LOG_ROWS

    # --- main() itself ----------------------------------------------------
    put_line(0, "NOVA MALLOC TESTER")
    put_line(1, "probing this platform's allocator")

    # phase 1: free() does not reclaim
    log_line("phase1: free() then realloc same size")
    mark_range(0, 64, ord('F'))
    mark_range(64, 64, ord('1'))

    # phase 2: calloc overflow
    log_line("phase2: calloc(4096,4096) 16MB nominal")

    # phase 3: probe until exhausted (28 chunks of 32 bytes; 128 + 28*32
    # == 1024 == this runtime's actual HEAP_WORDS)
    used = 128
    count = 0
    while count < 28:
        ch = ord('.') + 1 + (count % 9)
        mark_range(used, PROBE_CHUNK, ch)
        used += PROBE_CHUNK
        count += 1
    log_line("phase3: exhausted after %d x %dB" % (count, PROBE_CHUNK))
    log_line("phase3: confirmed no memory expansion")

    # phase 4: wrap the bounds check, alias phase 1's p1
    heap_used_now = used   # 1024
    craft_size = (0 - heap_used_now) & 0xFFFF
    # printf/sprintf's %d reads the same 16-bit pattern as signed.
    craft_signed = craft_size - 0x10000 if craft_size >= 0x8000 else craft_size
    log_line("phase4: malloc(%d) [craft]" % craft_signed)
    mark_range(0, 64, ord('X'))
    log_line("phase4: heap ptr wrapped to START")

    # back in main(): final verdict line (ALL FINDINGS CONFIRMED, since
    # every phase above is expected to reproduce exactly)
    put_line(GRID_ROW0 - 1, "ALL FINDINGS CONFIRMED")

    return cells


def ocr_frame(path):
    """{(row, col): char} for every non-blank cell in a PNG, via the
    shipped character ROM, used here to recognize glyphs instead of
    render them."""
    rom = V.read_charrom()
    glyphs = {}
    for code in range(32, 127):
        g = tuple((rom[code * 16 + r] >> 8) & 0xFF for r in range(16))
        glyphs[g] = chr(code)

    w, h, rows = V.read_png(path)

    def cell_bits(row, col):
        out = []
        for scan in range(16):
            y = row * 16 + scan
            v = 0
            for k in range(8):
                x = col * 8 + k
                if (rows[y][x // 8] >> (7 - (x % 8))) & 1:
                    v |= 1 << (7 - k)
            out.append(v)
        return tuple(out)

    cells = {}
    for row in range(ROWS):
        for col in range(COLS):
            bits = cell_bits(row, col)
            if any(bits):
                cells[(row, col)] = glyphs.get(bits, "?")
    return cells, (w, h)


def main():
    ok = True
    print("malloctest.ini (from src/malloctest.c) -- title/grid/log OCR "
          "checked against a byte-for-byte replay of main()'s calls")

    frames = sorted(glob.glob(os.path.join(OUT, "malloctest*.png")))
    ok &= V.check("exactly 8 frames presented (deterministic)",
                  len(frames) == 8, "found %d: %s" % (len(frames), frames))
    if not frames:
        print("\nFAILURES PRESENT")
        return 1

    last = frames[-1]
    got, (w, h) = ocr_frame(last)
    ok &= V.check("geometry %dx%d" % (WIDTH, HEIGHT), (w, h) == (WIDTH, HEIGHT),
                  "got %dx%d" % (w, h))

    want = build_expected()
    # Blank cells matter too: an unexpected glyph where the replay says
    # nothing was written is exactly the bug this test exists to catch.
    all_cells = set(want) | set(got)
    bad = [c for c in all_cells if want.get(c, ' ') != got.get(c, ' ')]
    ok &= V.check("every text cell matches the replayed call sequence",
                  not bad, "%d cell(s) differ, e.g. %s" % (len(bad), bad[:5]))

    print("\n%s" % ("ALL CHECKS PASSED" if ok else "FAILURES PRESENT"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
