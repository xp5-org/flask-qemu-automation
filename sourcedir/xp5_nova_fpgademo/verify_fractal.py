#!/usr/bin/env python3
"""Self-check for gen/fractal.ini (built from src/fractal.c).

This program never halts, so there's no fixed frame count to assert
against. Instead this globs whatever output/fractal*.png exist and checks
each one independently:

  frame 1        the title card, char mode + built-in ROM -- recomputed via
                 nova_fb's verify_frames._expected_text.
  frame N (>= 2) the AND-scroll redraw at phase t = N - 2: recomputes
                 SET (x,y) iff (x+t) AND y != 0 from scratch and diffs
                 every pixel, independent of the simulator.

TITLE below is kept in sync by hand with src/fractal.c's TITLE array.
"""
import glob
import os
import re
import sys

NOVA_FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nova_fb")
sys.path.insert(0, NOVA_FB)
import verify_frames as V   # noqa: E402 -- read_png / _expected_text / check

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

FRAME_RE = re.compile(r"fractal(\d{4})\.png$")

WIDTH = 640
HEIGHT = 480

# Mirrors src/fractal.c's TITLE[] -- see that file if this drifts.
TITLE = [
    (2, 3, "NOVA FB - AND FRACTAL SCROLL", 0),
    (4, 3, "SET (x,y) IF (x+t) AND y", 0),
    (6, 3, "built via nova-llvm-backend", 0),
    (7, 3, "not hand-assembled -- real C", 0),
    (13, 3, "watch it flow ... never halts", 0),
]


def _fractal_bit(x, y, t):
    return 1 if ((x + t) & y) != 0 else 0


def _frame_numbers():
    nums = []
    for path in glob.glob(os.path.join(OUT, "fractal*.png")):
        m = FRAME_RE.search(path)
        if m:
            nums.append(int(m.group(1)))
    return sorted(nums)


def main():
    ok = True
    print("fractal.ini (from src/fractal.c) -- title card + scrolling AND "
          "fractal (never halts, checks whatever frames the run produced)")

    nums = _frame_numbers()
    ok &= V.check("at least a title frame and one scroll frame exist",
                  len(nums) >= 2, "found %d frame(s): %s" % (len(nums), nums))
    if not ok:
        print("\nFAILURES PRESENT")
        return 1

    w, h, rows = V.read_png(os.path.join(OUT, "fractal%04d.png" % nums[0]))
    ok &= V.check("geometry %dx%d" % (WIDTH, HEIGHT),
                  (w, h) == (WIDTH, HEIGHT), "got %dx%d" % (w, h))
    want = V._expected_text(TITLE, WIDTH, HEIGHT, 8, linegfx=False, custom=None)
    bad = sum(1 for y in range(h) for x in range(w)
              if ((rows[y][x // 8] >> (7 - (x % 8))) & 1)
              != (1 if (x, y) in want else 0))
    ok &= V.check("frame %d matches the recomputed title card" % nums[0],
                  bad == 0, "%d pixels differ" % bad)

    scroll_frames = nums[1:]
    ok &= V.check("more than one scroll frame exists (actually in motion)",
                  len(scroll_frames) >= 2,
                  "only %d scroll frame(s)" % len(scroll_frames))

    sample = sorted({scroll_frames[0], scroll_frames[len(scroll_frames) // 2],
                     scroll_frames[-1]})
    for n in sample:
        t = n - nums[0] - 1
        w, h, rows = V.read_png(os.path.join(OUT, "fractal%04d.png" % n))
        bad = 0
        for y in range(h):
            for x in range(w):
                got = (rows[y][x // 8] >> (7 - (x % 8))) & 1
                if got != _fractal_bit(x, y, t):
                    bad += 1
        ok &= V.check("frame %d matches the AND-scroll at phase t=%d" % (n, t),
                      bad == 0, "%d pixels differ" % bad)

    if len(scroll_frames) >= 2:
        _, _, first_rows = V.read_png(
            os.path.join(OUT, "fractal%04d.png" % scroll_frames[0]))
        _, _, last_rows = V.read_png(
            os.path.join(OUT, "fractal%04d.png" % scroll_frames[-1]))
        ok &= V.check("the scroll actually moved (first and last frame differ)",
                      [bytes(r) for r in first_rows] != [bytes(r) for r in last_rows])

    print("\n%s" % ("ALL CHECKS PASSED" if ok else "FAILURES PRESENT"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
