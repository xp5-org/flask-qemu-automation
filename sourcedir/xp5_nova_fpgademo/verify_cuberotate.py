#!/usr/bin/env python3
"""Self-check for gen/cuberotate.ini (built from src/cuberotate.c).

Like fractal.c this program never halts, so there's no fixed frame count.
But ax/ay advance by exactly 1 every frame with no wall-clock dependency,
so this recomputes the cube's projection with the same 16-bit fixed-point
arithmetic as src/cuberotate.c (mirrored here by hand) and diffs every
pixel outside the frametime corner.

The frametime corner is the one non-deterministic part -- it reports real
elapsed wall-clock time between two RTC ticks -- so it's OCR'd with the
same 3x5 font and accepted as long as it reads "T0000MS" or a plausible
"TddddMS", not asserted to a specific number.
"""
import glob
import os
import re
import sys

NOVA_FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nova_fb")
sys.path.insert(0, NOVA_FB)
import verify_frames as V   # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
FRAME_RE = re.compile(r"cuberotate(\d{4})\.png$")

WIDTH, HEIGHT = 640, 480

TITLE = [
    (0, 2, "NOVA WIREFRAME CUBE", 0),
    (1, 2, "rotate + perspective project, fixed-point (no libm, no FPU)", 0),
    (2, 2, "RTC-paced (device 014, 60Hz) -- frametime bottom-right", 0),
]

# --- the same fixed-point model as src/cuberotate.c, mirrored by hand ---

FP_SHIFT = 6
FP_ONE = 1 << FP_SHIFT
TAB_N = 64
import math   # noqa: E402
SINTAB = [round(math.sin(2 * math.pi * i / TAB_N) * FP_ONE) for i in range(TAB_N)]


def SIN(i):
    return SINTAB[i & (TAB_N - 1)]


def COS(i):
    return SINTAB[(i + TAB_N // 4) & (TAB_N - 1)]


def fmul(a, b):
    """Mirrors src/cuberotate.c's `(a * b) >> FP_SHIFT`: a plain arithmetic
    right shift, which floors toward -infinity for a negative product --
    not the same as C's `/` (truncates toward zero). Python's `>>` already
    floors the same way. An earlier version used `/` instead and matched
    at ax=ay=0 but diverged by hundreds of pixels once operands went
    negative."""
    return (a * b) >> FP_SHIFT


CUBEV = [
    (-FP_ONE, -FP_ONE, -FP_ONE), (FP_ONE, -FP_ONE, -FP_ONE),
    (FP_ONE, FP_ONE, -FP_ONE), (-FP_ONE, FP_ONE, -FP_ONE),
    (-FP_ONE, -FP_ONE, FP_ONE), (FP_ONE, -FP_ONE, FP_ONE),
    (FP_ONE, FP_ONE, FP_ONE), (-FP_ONE, FP_ONE, FP_ONE),
]
CUBEE = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4),
         (0, 4), (1, 5), (2, 6), (3, 7)]

PERSP_SHIFT = 4
FOCAL_PERSP = 4 << PERSP_SHIFT
SCALE_PX = 90


def project_cube(ax, ay):
    sax, cax = SIN(ax), COS(ax)
    say, cay = SIN(ay), COS(ay)
    cx, cy = WIDTH // 2, HEIGHT // 2
    out = []
    for x, y, z in CUBEV:
        y1 = fmul(y, cax) - fmul(z, sax)
        z1 = fmul(y, sax) + fmul(z, cax)
        x2 = fmul(x, cay) + fmul(z1, say)
        z2 = fmul(z1, cay) - fmul(x, say)
        z2_persp = z2 >> (FP_SHIFT - PERSP_SHIFT)
        persp = (FOCAL_PERSP << PERSP_SHIFT) // (FOCAL_PERSP - z2_persp)
        px = (x2 * SCALE_PX) >> FP_SHIFT
        py = (y1 * SCALE_PX) >> FP_SHIFT
        out.append((cx + ((px * persp) >> PERSP_SHIFT),
                    cy - ((py * persp) >> PERSP_SHIFT)))
    return out


def bresenham(x0, y0, x1, y1):
    pts = []
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
    return pts


def expected_cube_pixels(ax, ay):
    proj = project_cube(ax, ay)
    lit = set()
    for a, b in CUBEE:
        for x, y in bresenham(proj[a][0], proj[a][1], proj[b][0], proj[b][1]):
            if 0 <= x < WIDTH and 0 <= y < HEIGHT:   # hardware clips off-screen
                lit.add((x, y))
    return lit


# --- frametime corner: OCR only, no exact-value assertion (see module doc) --

FONT_CHARS = "0123456789TMS"
FONT_ROWS = {
    '0': [7,5,5,5,7], '1': [2,6,2,2,7], '2': [7,1,7,4,7],
    '3': [7,1,7,1,7], '4': [5,5,7,1,1], '5': [7,4,7,1,7],
    '6': [7,4,7,5,7], '7': [7,1,2,2,2], '8': [7,5,7,5,7],
    '9': [7,5,7,1,7], 'T': [7,2,2,2,2], 'M': [5,7,5,5,5],
    'S': [7,4,7,1,7],
}
COLMASK = [4, 2, 1]
CORNER_X0 = WIDTH - 7 * 4 * 4 - 4
CORNER_Y0 = HEIGHT - 5 * 4 - 4
CORNER_X1 = CORNER_X0 + 7 * 16
CORNER_Y1 = CORNER_Y0 + 5 * 4


def _cell_on(rows, x0, y0, w, h):
    return any((rows[y][x // 8] >> (7 - (x % 8))) & 1
               for y in range(y0, y0 + h) for x in range(x0, x0 + w)
               if 0 <= x < len(rows[0]) * 8 and 0 <= y < len(rows))


def read_frametime(rows):
    """Decode the corner via the same 3x5 font src/cuberotate.c draws with
    (S and 5 share a bit pattern, but S only ever appears in the fixed
    last position, so it's unambiguous here). Returns the 7-char string,
    with '?' for any cell that doesn't match a known glyph."""
    out = []
    for ci in range(7):
        gx = CORNER_X0 + ci * 16
        pattern = []
        for row in range(5):
            bits = 0
            for col in range(3):
                if _cell_on(rows, gx + col * 4, CORNER_Y0 + row * 4, 4, 4):
                    bits |= COLMASK[col]
            pattern.append(bits)
        ch = '?'
        for c, want in FONT_ROWS.items():
            if want == pattern:
                ch = c
                break
        out.append(ch)
    # Position 6 is always 'S', never '5' -- resolve the shared pattern by
    # context instead of leaving it ambiguous.
    if out[6] == '5':
        out[6] = 'S'
    return "".join(out)


def _frame_numbers():
    nums = []
    for path in glob.glob(os.path.join(OUT, "cuberotate*.png")):
        m = FRAME_RE.search(path)
        if m:
            nums.append(int(m.group(1)))
    return sorted(nums)


def main():
    ok = True
    print("cuberotate.ini -- title + rotating wireframe cube (never halts, "
          "checks whatever frames the run produced)")

    nums = _frame_numbers()
    ok &= V.check("at least a title frame and one cube frame exist",
                  len(nums) >= 2, "found %d frame(s)" % len(nums))
    if not ok:
        print("\nFAILURES PRESENT")
        return 1

    w, h, rows = V.read_png(os.path.join(OUT, "cuberotate%04d.png" % nums[0]))
    ok &= V.check("geometry %dx%d" % (WIDTH, HEIGHT), (w, h) == (WIDTH, HEIGHT),
                  "got %dx%d" % (w, h))
    want_title = V._expected_text(TITLE, WIDTH, HEIGHT, 8, linegfx=False,
                                  custom=None)
    bad = sum(1 for y in range(h) for x in range(w)
              if ((rows[y][x // 8] >> (7 - (x % 8))) & 1)
              != (1 if (x, y) in want_title else 0))
    ok &= V.check("frame %d matches the recomputed title card" % nums[0],
                  bad == 0, "%d pixels differ" % bad)

    cube_frames = nums[1:]
    ok &= V.check("more than one cube frame exists (actually rotating)",
                  len(cube_frames) >= 2,
                  "only %d cube frame(s)" % len(cube_frames))

    # A handful spread across the run, like verify_fractal.py -- decoding
    # every frame would be slow and adds nothing past the first few.
    sample = sorted({cube_frames[0], cube_frames[len(cube_frames) // 2],
                     cube_frames[-1]})
    for n in sample:
        ax = ay = n - nums[0] - 1   # both advance by 1 every frame, from 0
        want = expected_cube_pixels(ax, ay)
        w, h, rows = V.read_png(os.path.join(OUT, "cuberotate%04d.png" % n))
        bad = 0
        for y in range(h):
            for x in range(w):
                if CORNER_X0 <= x < CORNER_X1 and CORNER_Y0 <= y < CORNER_Y1:
                    continue   # frametime corner: checked separately below
                got = (rows[y][x // 8] >> (7 - (x % 8))) & 1
                if got != (1 if (x, y) in want else 0):
                    bad += 1
        ok &= V.check("frame %d wireframe matches the recomputed projection "
                      "at ax=ay=%d" % (n, ax), bad == 0,
                      "%d pixels differ (outside the frametime corner)" % bad)

        text = read_frametime(rows)
        plausible = text == "T0000MS" or (
            text[0] == 'T' and text[1:5].isdigit() and text[5:7] == "MS")
        ok &= V.check("frame %d frametime corner reads a plausible value (%r)"
                      % (n, text), plausible)

    if len(cube_frames) >= 2:
        _, _, first_rows = V.read_png(
            os.path.join(OUT, "cuberotate%04d.png" % cube_frames[0]))
        _, _, last_rows = V.read_png(
            os.path.join(OUT, "cuberotate%04d.png" % cube_frames[-1]))
        ok &= V.check("the cube actually moved (first and last frame differ)",
                      [bytes(r) for r in first_rows] != [bytes(r) for r in last_rows])

    print("\n%s" % ("ALL CHECKS PASSED" if ok else "FAILURES PRESENT"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
