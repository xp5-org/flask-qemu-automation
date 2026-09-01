/* Rotating wireframe cube for the nova_fb card, at 640x480.
 *
 * modelled on ../owc_cuberotate/src/CUBE.H's math
 *
 * FIXED-POINT SCALING
 *
 *   FP_SHIFT = 6 (1.0 = 64). Cube coordinates and the sin/cos table are
 *   both at this scale, so every rotation multiply is at most 64*64=4096,
 *   well under the 32767 signed limit.
 *
 *   The perspective ratio (focal/(focal-z)) uses its own smaller scale
 *   (PERSP_SHIFT = 4, 1.0 = 16) so its division's numerator fits in 16
 *   bits before dividing. See project_cube()'s comment for the chain.
 *
 * the Nova's interval clock, device 014 ("RTC" in `show
 * devices`), ticks at 60Hz by default. NIOS 014 starts it; each tick the
 * device flips Busy->Done and re-arms itself regardless of the program, so
 * SKPDN 014 blocks until the next tick and a second NIOS 014 acknowledges
 * it and re-arms Busy without stopping the clock (that's NIOC, not used
 * here). Waiting one tick per frame is a free vsync limiter and a wall
 * clock: every 300 ticks (5s at 60Hz) this recomputes average ms/frame and
 * redraws it in the corner.
 *
 * The corner text is a hand-blitted 3x5 pixel font, not the card's char
 * ROM . CHARACTER mode generates the whole frame from the text buffer, so
 * it can't be overlaid on the bitmap the cube is drawn into.
 */

#define CTL_TEXT     02000
#define CTL_WORDAI   020000
#define CTL_PIXEL    010000
#define OP_CLEAR     020000
#define T_ENABLE     01

#define WIDTH  640
#define HEIGHT 480
#define TEXTBUF 046000     /* past the bitmap's 0-19199 words, see fractal.c */
#define COLS   80

static void fb_doc(unsigned v) { asm volatile("DOC %0,042\n\t" :: "r"(v)); }
static void fb_doa(unsigned v) { asm volatile("DOA %0,042\n\t" :: "r"(v)); }
static void fb_dob(unsigned v) { asm volatile("DOB %0,042\n\t" :: "r"(v)); }
static void fb_present(void)   { asm volatile("NIOP 042\n\t"); }

static void clk_start(void)    { asm volatile("NIOS 014\n\t"); }
/* SKPDN 014 / JMP wait: blocks until Done, same idiom eclipse_rt.c's
 * getchar() uses for TTI, pointed at the clock instead. */
static void clk_wait_tick(void) {
  asm volatile(
      "wait%=:\n\t"
      "SKPDN 014\n\t"
      "JMP wait%=\n\t"
      ::);
  clk_start();   /* ack this tick and re-arm Busy for the next one */
}

static void fb_putc(int row, int col, unsigned code) {
  fb_doa(TEXTBUF + row * COLS + col);
  fb_dob(code);
}

static void fb_puts(int row, int col, const char *s) {
  while (*s && col < COLS) {
    fb_putc(row, col, (unsigned)(unsigned char)*s);
    s++;
    col++;
  }
}

static void fb_init_textmode(void) {
  fb_doc(CTL_TEXT);
  fb_doa(0);
  fb_dob(TEXTBUF);
  fb_dob(0);
  fb_dob(T_ENABLE);
  fb_doc(0);
}

static void clear_bitmap(void) {
  int i;
  fb_doc(CTL_WORDAI);
  fb_doa(0);
  for (i = 0; i < (WIDTH / 16) * HEIGHT; i++)
    fb_dob(0);
}

/* --- pixel plot + Bresenham line, pixel mode ------------------------- */

static void plot(int x, int y) {
  /* Off-screen coordinates are clipped in hardware -- no bounds check
   * needed here. */
  fb_doa((unsigned)x);
  fb_dob((unsigned)y);
}

static void draw_line(int x0, int y0, int x1, int y1) {
  int dx, dy, sx, sy, err, e2;
  dx = x1 - x0;
  if (dx < 0)
    dx = -dx;
  sx = (x0 < x1) ? 1 : -1;
  dy = y1 - y0;
  if (dy > 0)
    dy = -dy;
  sy = (y0 < y1) ? 1 : -1;
  err = dx + dy;
  for (;;) {
    plot(x0, y0);
    if (x0 == x1 && y0 == y1)
      break;
    e2 = 2 * err;
    if (e2 >= dy) {
      err += dy;
      x0 += sx;
    }
    if (e2 <= dx) {
      err += dx;
      y0 += sy;
    }
  }
}

/* --- fixed point ------------------------------------------------------ */

#define FP_SHIFT 6              /* 1.0 == 64 */
#define FP_ONE   (1 << FP_SHIFT)

/* Both operands must already be at FP_SHIFT scale, |a|,|b| <= FP_ONE --
 * see the header comment for why that keeps a*b inside 16 bits. */
static int fmul(int a, int b) { return (a * b) >> FP_SHIFT; }

/* --- the cube -----------------------------------------------------------
 * Vertex/edge numbering kept in sync by hand with
 * ../owc_cuberotate/src/CUBE.H. Coordinates are FP_ONE (64) for 1,
 * -FP_ONE for -1. */

static const int CUBEV[8][3] = {
  {-FP_ONE,-FP_ONE,-FP_ONE}, { FP_ONE,-FP_ONE,-FP_ONE},
  { FP_ONE, FP_ONE,-FP_ONE}, {-FP_ONE, FP_ONE,-FP_ONE},
  {-FP_ONE,-FP_ONE, FP_ONE}, { FP_ONE,-FP_ONE, FP_ONE},
  { FP_ONE, FP_ONE, FP_ONE}, {-FP_ONE, FP_ONE, FP_ONE},
};
static const int CUBEE[12][2] = {
  {0,1},{1,2},{2,3},{3,0}, {4,5},{5,6},{6,7},{7,4}, {0,4},{1,5},{2,6},{3,7},
};

/* sin(2*pi*i/64) * 64, rounded -- computed offline in Python. */
#define TAB_N 64
static const int SINTAB[TAB_N] = {
     0,    6,   12,   19,   24,   30,   36,   41,   45,   49,   53,   56,   59,   61,   63,   64,
    64,   64,   63,   61,   59,   56,   53,   49,   45,   41,   36,   30,   24,   19,   12,    6,
     0,   -6,  -12,  -19,  -24,  -30,  -36,  -41,  -45,  -49,  -53,  -56,  -59,  -61,  -63,  -64,
   -64,  -64,  -63,  -61,  -59,  -56,  -53,  -49,  -45,  -41,  -36,  -30,  -24,  -19,  -12,   -6,
};

static int SIN(int i) { return SINTAB[i & (TAB_N - 1)]; }
static int COS(int i) { return SINTAB[(i + TAB_N / 4) & (TAB_N - 1)]; }

static int projx[8], projy[8];

/* PERSP_SHIFT is a separate, smaller fixed-point scale used only for the
 * perspective ratio focal/(focal-z2), so its division's numerator fits in
 * 16 bits (see the header comment). Rescaling z2 down by
 * FP_SHIFT-PERSP_SHIFT keeps every intermediate here well under 32767. */
#define PERSP_SHIFT 4
#define FOCAL_PERSP (4 << PERSP_SHIFT)   /* focal = 4.0 at PERSP_SHIFT scale */
#define SCALE_PX 90                       /* on-screen half-size, pixels */

static void project_cube(int ax, int ay) {
  int sax = SIN(ax), cax = COS(ax);
  int say = SIN(ay), cay = COS(ay);
  int cx = WIDTH / 2, cy = HEIGHT / 2;
  int i;
  for (i = 0; i < 8; i++) {
    int x = CUBEV[i][0], y = CUBEV[i][1], z = CUBEV[i][2];
    int y1 = fmul(y, cax) - fmul(z, sax);
    int z1 = fmul(y, sax) + fmul(z, cax);
    int x2 = fmul(x, cay) + fmul(z1, say);
    int z2 = fmul(z1, cay) - fmul(x, say);
    int z2_persp = z2 >> (FP_SHIFT - PERSP_SHIFT);
    /* Numerator scaled up by PERSP_SHIFT before dividing -- dividing two
     * already-scaled quantities directly collapses persp to 0 or 1 and
     * the cube projects to a few pixels wide. */
    int persp = (FOCAL_PERSP << PERSP_SHIFT) / (FOCAL_PERSP - z2_persp);
    int px = (x2 * SCALE_PX) >> FP_SHIFT;    /* pixel-scale, no persp yet */
    int py = (y1 * SCALE_PX) >> FP_SHIFT;
    projx[i] = cx + ((px * persp) >> PERSP_SHIFT);
    projy[i] = cy - ((py * persp) >> PERSP_SHIFT);
  }
}

static void draw_cube(void) {
  int i;
  for (i = 0; i < 12; i++)
    draw_line(projx[CUBEE[i][0]], projy[CUBEE[i][0]],
              projx[CUBEE[i][1]], projy[CUBEE[i][1]]);
}

/* --- tiny 3x5 bitmap font, hand-blitted (not the card's char ROM, see
 * header comment). Just enough glyphs for "T%04dMS". Each row's low 3
 * bits are one glyph row, bit 2 leftmost.
 *
 * Two parallel flat arrays instead of a struct { char c; unsigned char
 * rows[5]; } array -- an earlier version used that struct form and
 * reproducibly mis-rendered every glyph shifted by one row (a backend bug
 * in struct-array-of-arrays field access, confirmed with an isolated test
 * unrelated to the font data or drawing math). This form sidesteps it. */
static const char FONT_CHARS[13] = {
  '0','1','2','3','4','5','6','7','8','9','T','M','S'
};
static const unsigned char FONT_ROWS[13][5] = {
  {7,5,5,5,7}, {2,6,2,2,7}, {7,1,7,4,7},
  {7,1,7,1,7}, {5,5,7,1,1}, {7,4,7,1,7},
  {7,4,7,5,7}, {7,1,2,2,2}, {7,5,7,5,7},
  {7,5,7,1,7}, {7,2,2,2,2}, {5,7,5,5,5},
  {7,4,7,1,7},
};
#define FONT_N 13

/* col indexes this instead of shifting `bits` by a variable amount --
 * this backend only supports shifts by a compile-time constant. */
static const unsigned char COLMASK[3] = {4, 2, 1};

static void draw_char(int x0, int y0, char c, int scale) {
  int gi, row, col, px, py;
  for (gi = 0; gi < FONT_N; gi++) {
    if (FONT_CHARS[gi] != c)
      continue;
    for (row = 0; row < 5; row++) {
      unsigned bits = FONT_ROWS[gi][row];
      for (col = 0; col < 3; col++) {
        if (!(bits & COLMASK[col]))
          continue;
        for (py = 0; py < scale; py++)
          for (px = 0; px < scale; px++)
            plot(x0 + col * scale + px, y0 + row * scale + py);
      }
    }
    return;
  }
}

static void draw_string(int x0, int y0, const char *s, int scale) {
  int x = x0;
  while (*s) {
    draw_char(x, y0, *s, scale);
    x += (3 + 1) * scale;   /* glyph width + one column gap */
    s++;
  }
}

/* --- frametime corner: "T%04dMS", recomputed every 300 ticks (5s @ 60Hz) */

static char frametime_text[8] = "T0000MS";

static void format_frametime(int ms) {
  if (ms > 9999)
    ms = 9999;
  frametime_text[0] = 'T';
  frametime_text[1] = '0' + (ms / 1000) % 10;
  frametime_text[2] = '0' + (ms / 100) % 10;
  frametime_text[3] = '0' + (ms / 10) % 10;
  frametime_text[4] = '0' + ms % 10;
  frametime_text[5] = 'M';
  frametime_text[6] = 'S';
  frametime_text[7] = 0;
}

#define TICKS_PER_REPORT 300   /* 5 seconds at the RTC's default 60Hz */

void main(void) {
  int ax, ay, ticks, frames_since_report;

  fb_init_textmode();
  fb_puts(0, 2, "NOVA WIREFRAME CUBE");
  fb_puts(1, 2, "rotate + perspective project, fixed-point (no libm, no FPU)");
  fb_puts(2, 2, "RTC-paced (device 014, 60Hz) -- frametime bottom-right");
  fb_present();

  fb_doc(CTL_TEXT);
  fb_doa(2);
  fb_dob(0);      /* char mode off */

  fb_doc(CTL_PIXEL);
  clk_start();

  ax = 0;
  ay = 0;
  ticks = 0;
  frames_since_report = 0;

  for (;;) {
    clear_bitmap();
    fb_doc(CTL_PIXEL);
    project_cube(ax, ay);
    draw_cube();
    /* frametime_text is always 7 chars ("T0000MS"); each glyph is
     * (3+1)*scale px wide -- see draw_string. */
    draw_string(WIDTH - 7 * 4 * 4 - 4, HEIGHT - 5 * 4 - 4, frametime_text, 4);
    fb_present();

    ax += 1;
    ay += 1;
    frames_since_report++;

    clk_wait_tick();
    ticks++;
    if (ticks >= TICKS_PER_REPORT) {
      format_frametime(5000 / (frames_since_report ? frames_since_report : 1));
      ticks = 0;
      frames_since_report = 0;
    }
  }
}
