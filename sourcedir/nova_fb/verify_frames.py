#!/usr/bin/env python3
"""Self-check for the nova_fb device demos.

Decodes the PNGs written by demo/*.ini with the stdlib only (no PIL in the test
container) and asserts the exact bit pattern each demo should produce.
Run run_demos.sh first, or just run that script -- it calls this at the end.
"""
import os
import struct
import sys
import zlib

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


import gen_charrom                                    # the shipped font
import gen_text                                       # the demo layouts
import gen_modeswitch                                 # the merged program's modes


def read_charrom():
    """The card's built-in font, straight out of the generated header."""
    return gen_charrom.read_charrom()


def read_png(path):
    """Return (width, height, [rowbytes]) for a non-interlaced 1-bit gray PNG."""
    data = open(path, "rb").read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("%s: not a PNG" % path)
    i, idat, hdr = 8, b"", None
    while i < len(data):
        ln = struct.unpack(">I", data[i:i + 4])[0]
        typ = data[i + 4:i + 8]
        if typ == b"IHDR":
            hdr = struct.unpack(">IIBB", data[i + 8:i + 18])
        elif typ == b"IDAT":
            idat += data[i + 8:i + 8 + ln]
        i += 12 + ln
    w, h, depth, ctype = hdr
    if (depth, ctype) != (1, 0):
        raise ValueError("%s: expected 1-bit grayscale, got depth=%d type=%d"
                         % (path, depth, ctype))
    raw = zlib.decompress(idat)
    stride = (w * depth + 7) // 8
    rows = []
    for r in range(h):
        if raw[r * (stride + 1)] != 0:
            raise ValueError("%s: unexpected PNG row filter" % path)
        rows.append(raw[r * (stride + 1) + 1:(r + 1) * (stride + 1)])
    return w, h, rows


def check(name, cond, detail=""):
    print("  %-4s %s%s" % ("ok" if cond else "FAIL", name,
                           "" if cond else "  <- " + detail))
    return cond


def main(groups=None):
    """Run all check groups, or only the named ones.

    The flask testlist drives individual demos through the harness and then
    verifies just those, e.g. "verify_frames.py cursor".
    """
    ok = True
    want = set(groups or [])

    def run(group):
        return (not want) or (group in want)

    if run("stripes"):
        ok &= _stripes()
    if run("toprow"):
        ok &= _toprow()
    if run("full"):
        ok &= _full()
    if run("bank"):
        ok &= _bank()
    if run("autoinc"):
        ok &= _autoinc()
    if run("pixels"):
        ok &= _pixels()
    if run("pixel_ops"):
        ok &= _pixel_ops()
    if run("cursor"):
        ok &= _cursor()
    if run("cursor_xor"):
        ok &= _cursor_xor()
    if run("rdos"):
        ok &= _rdos()
    if run("text80"):
        ok &= _text("text80", 720, 400, 9, gen_text.TEXT80, linegfx=True)
    if run("text30"):
        ok &= _text("text30", 640, 480, 8, gen_text.TEXT30)
    if run("text_font"):
        ok &= _text("text_font", 720, 400, 9, gen_text.TEXT_FONT,
                    custom=gen_text.CUSTOM)
    if run("modeswitch"):
        ok &= _modeswitch()

    unknown = want - KNOWN_GROUPS
    if unknown:
        print("  FAIL unknown check group(s): %s" % ", ".join(sorted(unknown)))
        ok = False

    print("\n%s" % ("ALL CHECKS PASSED" if ok else "FAILURES PRESENT"))
    return 0 if ok else 1


KNOWN_GROUPS = {"stripes", "toprow", "full", "bank", "autoinc", "pixels",
                "pixel_ops", "cursor", "cursor_xor", "rdos",
                "text80", "text30", "text_font", "modeswitch"}


def _stripes():
    ok = True
    print("stripes256.ini -- 256x256, every word 0125252 (0xAAAA)")
    w, h, rows = read_png(os.path.join(OUT, "stripes0001.png"))
    ok &= check("geometry 256x256", (w, h) == (256, 256), "got %dx%d" % (w, h))
    ok &= check("stride 32 bytes", len(rows[0]) == 32, "got %d" % len(rows[0]))
    ok &= check("all rows are 0xAA (MSB=leftmost pixel)",
                all(all(b == 0xAA for b in r) for r in rows))

    return ok


def _toprow():
    ok = True
    print("toprow.ini -- one row written, rest untouched")
    w, h, rows = read_png(os.path.join(OUT, "toprow0001.png"))
    ok &= check("row 0 all white", all(b == 0xFF for b in rows[0]))
    ok &= check("rows 1..255 all black",
                all(all(b == 0x00 for b in r) for r in rows[1:]))
    return ok


def _full():
    ok = True
    print("full1024.ini -- full 1Mbit, 65536 words")
    w, h, rows = read_png(os.path.join(OUT, "full0001.png"))
    ok &= check("geometry 1024x1024", (w, h) == (1024, 1024),
                "got %dx%d" % (w, h))
    ok &= check("stride 128 bytes", len(rows[0]) == 128,
                "got %d" % len(rows[0]))
    ok &= check("all 1024 rows are 0xAA",
                all(all(b == 0xAA for b in r) for r in rows))

    return ok


def _bank():
    ok = True
    print("bus8_bank.ini -- 8-bit mode, A16 bank bit set")
    w, h, rows = read_png(os.path.join(OUT, "bank0001.png"))
    lit = [y for y, r in enumerate(rows) if any(r)]
    ok &= check("only row 512 lit (word 32768 = upper half)", lit == [512],
                "lit rows = %s" % lit)
    return ok


def _autoinc():
    ok = True
    print("stripes256_autoinc.ini -- AUTOINC produces the identical image")
    _, _, plain = read_png(os.path.join(OUT, "stripes0001.png"))
    _, _, auto = read_png(os.path.join(OUT, "stripes_autoinc0001.png"))
    ok &= check("byte-identical to explicit-address version",
                [bytes(r) for r in plain] == [bytes(r) for r in auto])
    return ok


def bit(rws, x, y):
    return (rws[y][x // 8] >> (7 - x % 8)) & 1


def _pixels():
    ok = True
    print("pixels.ini -- pixel mode, 256px diagonal")
    w, h, rows = read_png(os.path.join(OUT, "pixels0001.png"))
    ok &= check("pixel (i,i) set for all i in 0..255",
                all(bit(rows, i, i) == 1 for i in range(256)))
    ok &= check("exactly 256 pixels lit (nothing else touched)",
                sum(bin(b).count("1") for r in rows for b in r) == 256)
    return ok


def _pixel_ops():
    ok = True
    print("pixel_ops.ini -- SET then CLEAR then XOR on row 0")
    w, h, rows = read_png(os.path.join(OUT, "pixel_ops0001.png"))
    ok &= check("px 0-15 lit (XOR toggled them back on)",
                all(bit(rows, x, 0) == 1 for x in range(0, 16)))
    ok &= check("px 16-31 clear (CLEAR won)",
                all(bit(rows, x, 0) == 0 for x in range(16, 32)))
    ok &= check("px 32-63 lit (SET survived)",
                all(bit(rows, x, 0) == 1 for x in range(32, 64)))
    ok &= check("px 64+ clear",
                all(bit(rows, x, 0) == 0 for x in range(64, 256)))
    ok &= check("rows 1..255 untouched",
                all(all(b == 0 for b in r) for r in rows[1:]))

    return ok


# ---- sprite cursor: 32x32 arrow from four 16x16 units -----------------------

def _composite(name, combine, label):
    """Recompute the expected frame independently of the simulator and diff."""
    import gen_cursor as G
    good = True
    for frame, (cx, cy) in ((1, G.POS1), (2, G.POS2)):
        w, h, rws = read_png(os.path.join(OUT, "%s%04d.png" % (name, frame)))
        bad = 0
        for y in range(h):
            for x in range(w):
                bg = 1 if x % 2 == 0 else 0
                exp = combine(bg, G.pixel(x - cx, y - cy))
                if bit(rws, x, y) != exp:
                    bad += 1
        good &= check("frame %d, cursor at %s: %s" % (frame, (cx, cy), label),
                      bad == 0, "%d mismatched pixels" % bad)
    return good


def _cursor():
    import gen_cursor as G
    ok = True
    print("cursor.ini -- 4 sprite units, SET op")
    ok &= _composite("cursor", lambda bg, a: 1 if (bg or a) else 0,
                     "matches background OR arrow")
    w, h, rows = read_png(os.path.join(OUT, "cursor0001.png"))
    lit = sum(bin(b).count("1") for r in rows for b in r)
    base = (256 * 256) // 2                      # striped background
    ok &= check("frame 1 adds exactly 162 pixels over the stripes",
                lit - base == 162, "added %d" % (lit - base))

    print("  -- overlay must not damage the framebuffer --")
    _, _, f2 = read_png(os.path.join(OUT, "cursor0002.png"))
    cx, cy = G.POS1
    clean = all(bit(f2, x, y) == (1 if x % 2 == 0 else 0)
                for y in range(cy, cy + 32) for x in range(cx, cx + 32))
    ok &= check("frame 1's cursor site is pure background in frame 2", clean)
    return ok


def _cursor_xor():
    print("cursor_xor.ini -- XOR op, visible over any background")
    return _composite("cursor_xor", lambda bg, a: bg ^ a,
                      "matches background XOR arrow")


def _rdos():
    """FBDRAW.SV, assembled and linked under RDOS, then run as a real program."""
    import gen_rdos_src as R
    ok = True
    print("rdos variant -- rectangle + XOR cursor drawn by an RDOS program")
    w, h, rows = read_png(os.path.join(OUT, "rdos0001.png"))
    ok &= check("geometry 256x256", (w, h) == (256, 256), "got %dx%d" % (w, h))

    bad = 0
    for y in range(h):
        for x in range(w):
            exp = (1 if R.in_rect(x, y) else 0) ^ R.pixel(x - R.CUR_X,
                                                          y - R.CUR_Y)
            if bit(rows, x, y) != exp:
                bad += 1
    ok &= check("every pixel matches rectangle XOR cursor", bad == 0,
                "%d mismatched pixels" % bad)

    # The cursor straddles the rectangle's SE corner, so it must be visible
    # BOTH ways round: knocked out of the white fill, and lit on black.
    inside = [(x, y) for y in range(R.CUR_Y, R.CUR_Y + 16)
              for x in range(R.CUR_X, R.CUR_X + 16)
              if R.in_rect(x, y) and R.pixel(x - R.CUR_X, y - R.CUR_Y)]
    outside = [(x, y) for y in range(R.CUR_Y, R.CUR_Y + 16)
               for x in range(R.CUR_X, R.CUR_X + 16)
               if not R.in_rect(x, y) and R.pixel(x - R.CUR_X, y - R.CUR_Y)]
    ok &= check("cursor straddles the rectangle edge (%d px on white, %d on black)"
                % (len(inside), len(outside)),
                len(inside) > 0 and len(outside) > 0)
    ok &= check("XOR knocks the cursor out of the white fill",
                all(bit(rows, x, y) == 0 for x, y in inside))
    ok &= check("XOR lights the cursor on the black background",
                all(bit(rows, x, y) == 1 for x, y in outside))
    return ok


# The frames modeswitch.ini presents, in order: mode 1 on start-up, then one
# per digit the testlist (or the person at the terminal) enters. Frame 4 is
# mode 1 again, which is the assertion that a mode switch RESTORES a mode
# rather than leaving something of the wider screen behind.
MODESWITCH_FRAMES = [(1, 0), (2, 1), (3, 2), (4, 0)]


def _modeswitch():
    ok = True
    for frame, idx in MODESWITCH_FRAMES:
        _n, layout, _cols, _rows, tctl, _charptr, custom = gen_modeswitch.MODES[idx]
        cellw = gen_text.CHAR_W + 1 if (tctl & gen_text.T_CELL9) else gen_text.CHAR_W
        ok &= _text("modeswitch", gen_modeswitch.WIDTH, gen_modeswitch.HEIGHT,
                    cellw, layout, linegfx=bool(tctl & gen_text.T_LINEGFX),
                    custom=custom, frame=frame,
                    label="modeswitch.ini frame %d -- mode %d" % (frame, idx + 1))
    return ok


def _expected_text(layout, width, height, cellw, linegfx=False, custom=None):
    """Recompute the frame char mode should have generated.

    Independent of the device: the glyphs come from the shipped ROM header (or
    the demo's own custom table), the layout from gen_text, and the cell
    geometry from the VGA rule -- COLS = WIDTH / cell width, ROWS = HEIGHT / 16.
    """
    rom = read_charrom()
    cols, rows_n = width // cellw, height // gen_text.CELL_H
    lit = set()

    for row, col, text, attr in layout:
        for i, ch in enumerate(text):
            c, code = col + i, ord(ch)
            if c >= cols or row >= rows_n:
                continue
            for scan in range(gen_text.CELL_H):
                if custom is not None:
                    glyph = ((custom.get(code, [0] * 16)[scan] & 0xFF) << 8)
                else:
                    glyph = rom[code * gen_text.CELL_H + scan]
                bits = (glyph >> 8) & 0xFF
                ninth = 0
                if cellw > gen_text.CHAR_W and linegfx and 0xC0 <= code <= 0xDF:
                    ninth = bits & 1
                if (attr & gen_text.ULINE) and scan == gen_text.CELL_H - 1:
                    bits, ninth = 0xFF, 1
                if attr & gen_text.REVERSE:
                    bits, ninth = (~bits) & 0xFF, 0 if ninth else 1
                y = row * gen_text.CELL_H + scan
                for k in range(cellw):
                    on = ninth if k >= gen_text.CHAR_W else (bits >> (7 - k)) & 1
                    if on:
                        x = c * cellw + k
                        if x < width and y < height:
                            lit.add((x, y))
    return lit


def _text(name, width, height, cellw, layout, linegfx=False, custom=None,
          frame=1, label=None):
    """Assert one PNG against a frame recomputed from the layout and the ROM.

    `frame` is which present to look at. The one-demo-per-run scripts only ever
    wrote a first frame; modeswitch.ini is a single program that presents once
    per mode switch, so its Nth mode is its Nth PNG.
    """
    ok = True
    cols, rows_n = width // cellw, height // gen_text.CELL_H
    print("%s -- %dx%d, %d dot cell -> %dx%d text"
          % (label or (name + ".ini"), width, height, cellw, cols, rows_n))
    w, h, rows = read_png(os.path.join(OUT, "%s%04d.png" % (name, frame)))
    ok &= check("geometry %dx%d" % (width, height), (w, h) == (width, height),
                "got %dx%d" % (w, h))
    if (w, h) != (width, height):
        return ok

    want = _expected_text(layout, width, height, cellw, linegfx, custom)
    bad = 0
    for y in range(h):
        for x in range(w):
            got = (rows[y][x // 8] >> (7 - (x % 8))) & 1
            if got != (1 if (x, y) in want else 0):
                bad += 1
    ok &= check("every pixel matches the recomputed text frame", bad == 0,
                "%d pixels differ" % bad)

    # Char mode GENERATES the frame, so anything outside the text is proof the
    # generator cleared rather than composited over a stale bitmap.
    ok &= check("nothing lit outside the glyphs", bad == 0)

    for row, col, text, attr in layout:
        if attr & gen_text.REVERSE:
            # A reverse cell is mostly ink: its background must be lit.
            x, y = col * cellw, row * gen_text.CELL_H
            ok &= check("reverse cell at row %d is inverted" % row,
                        (rows[y][x // 8] >> (7 - (x % 8))) & 1 == 1)
        if attr & gen_text.ULINE:
            y = row * gen_text.CELL_H + gen_text.CELL_H - 1
            run = all((rows[y][(col * cellw + k) // 8] >>
                       (7 - ((col * cellw + k) % 8))) & 1
                      for k in range(gen_text.CHAR_W))
            ok &= check("underline runs the full cell on row %d" % row, run)

    if custom is not None:
        # The whole point of CHARPTR. The pixel diff above already recomputed
        # the frame USING the custom table, so it would pass just as happily if
        # the custom glyphs were identical to the ROM's -- a vacuous test. So
        # pick a character whose custom glyph actually differs from the ROM's,
        # and assert the frame shows the custom one and NOT what the ROM would
        # have drawn.
        rom = read_charrom()
        target = None
        for r, c, text, _attr in layout:
            for i, ch in enumerate(text):
                code = ord(ch)
                if code not in custom:
                    continue
                romrows = [(rom[code * gen_text.CELL_H + k] >> 8) & 0xFF
                           for k in range(gen_text.CELL_H)]
                if [b & 0xFF for b in custom[code]] != romrows:
                    target = (r, c + i, code, romrows, custom[code])
                    break
            if target:
                break
        ok &= check("the custom font differs from the ROM at all",
                    target is not None,
                    "every custom glyph is identical to the ROM's")
        if target:
            row, col, code, romrows, custrows = target
            drawn = []
            for scan in range(gen_text.CELL_H):
                y = row * gen_text.CELL_H + scan
                v = 0
                for k in range(gen_text.CHAR_W):
                    x = col * cellw + k
                    if (rows[y][x // 8] >> (7 - (x % 8))) & 1:
                        v |= 1 << (7 - k)
                drawn.append(v)
            ok &= check("%r drawn from the program's glyphs" % chr(code),
                        drawn == [b & 0xFF for b in custrows])
            ok &= check("%r is NOT the ROM's glyph" % chr(code),
                        drawn != romrows)
    return ok


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
