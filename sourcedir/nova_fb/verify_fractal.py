#!/usr/bin/env python3
"""Self-check for demo/fractal.ini.

fractal.ini never halts (see gen_fractal.py) -- it scrolls until something
external stops the simulator, exactly like modeswitch.ini -- so there is no
fixed frame count to assert against. Instead this globs whatever
output/fractal*.png exist when it is run (after the testlist has let it play
for a while and torn it down) and checks each one independently:

  frame 1        the title card, char mode + built-in ROM -- recomputed via
                 verify_frames._expected_text, same as every other text demo.
  frame N (>= 2) the AND-scroll redraw at phase t = N - 2: recomputes
                 SET (x,y) iff (x+t) AND y != 0 from scratch and diffs every
                 pixel, independent of the simulator.

Also asserts that MORE THAN ONE post-title frame exists, which is the
assertion that actually matters here: this demo's whole point is being in
motion, and a single frame proves a redraw happened, not that it kept
happening.
"""
import glob
import os
import re
import sys

import gen_fractal as G
import verify_frames as V

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

FRAME_RE = re.compile(r"fractal(\d{4})\.png$")


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
    print("fractal.ini -- title card + scrolling AND fractal (never halts, "
          "checks whatever frames the run produced)")

    nums = _frame_numbers()
    ok &= V.check("at least a title frame and one scroll frame exist",
                  len(nums) >= 2, "found %d frame(s): %s" % (len(nums), nums))
    if not ok:
        print("\nFAILURES PRESENT")
        return 1

    w, h, rows = V.read_png(os.path.join(OUT, "fractal%04d.png" % nums[0]))
    ok &= V.check("geometry %dx%d" % (G.WIDTH, G.HEIGHT),
                  (w, h) == (G.WIDTH, G.HEIGHT), "got %dx%d" % (w, h))
    want = V._expected_text(G.TITLE, G.WIDTH, G.HEIGHT, 8, linegfx=False,
                            custom=None)
    bad = sum(1 for y in range(h) for x in range(w)
              if ((rows[y][x // 8] >> (7 - (x % 8))) & 1)
              != (1 if (x, y) in want else 0))
    ok &= V.check("frame %d matches the recomputed title card" % nums[0],
                  bad == 0, "%d pixels differ" % bad)

    scroll_frames = nums[1:]
    ok &= V.check("more than one scroll frame exists (actually in motion)",
                  len(scroll_frames) >= 2,
                  "only %d scroll frame(s)" % len(scroll_frames))

    # Checking every frame the run happened to produce would be slow for a
    # long-running window; a handful spread across the run (first, middle,
    # last) is enough to catch a wrong formula or a stuck phase without
    # decoding hundreds of PNGs.
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

    # Two different scroll frames drawing the SAME pixels would mean t never
    # advanced -- a stuck phase counter looks identical to "working" if you
    # only check one frame's formula against itself.
    if len(scroll_frames) >= 2:
        first_w, first_h, first_rows = V.read_png(
            os.path.join(OUT, "fractal%04d.png" % scroll_frames[0]))
        last_w, last_h, last_rows = V.read_png(
            os.path.join(OUT, "fractal%04d.png" % scroll_frames[-1]))
        ok &= V.check("the scroll actually moved (first and last frame differ)",
                      [bytes(r) for r in first_rows] != [bytes(r) for r in last_rows])

    print("\n%s" % ("ALL CHECKS PASSED" if ok else "FAILURES PRESENT"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
