/* Title card (nova_fb char mode, built-in ROM), then a continuously
 * scrolling AND fractal: SET (x,y) iff (x+t) AND y != 0, redrawn every
 * frame with t advancing. Never halts. Same shape as sourcedir/nova_fb's
 * hand-assembled demo/fractal.ini, but compiled from real C through
 * cullyrichard's nova-llvm-backend (see ../cully_llvm/NOTES.txt).
 *
 * The nova_fb card (device 042, sourcedir/nova_fb/src/nova_fb.c) is
 * programmed I/O over the Nova's IOT bus, same idiom eclipse_rt.c's
 * putchar()/getchar() use for the console (device 010/011). fb_doc/
 * fb_doa/fb_dob/fb_present are DOC/DOA/DOB/NIOP pointed at device 042
 * instead. See sourcedir/nova_fb/BUILD.txt for register semantics.
 */

#define CTL_TEXT   02000    /* DOA/DOB address the text register port */
#define CTL_PIXEL  010000   /* DOA/DOB are X / Y+op instead of addr/data */
#define OP_CLEAR   020000   /* pixel op field (bits 14-13) = 1: CLEAR */
#define T_ENABLE   01       /* TCTL bit 0 */

/* 640x480: BUILD.txt's power-up default and the platform's minimum
 * resolution; the fractal loop is O(WIDTH*HEIGHT) with no hardware
 * multiply, so higher resolutions would visibly slow the scroll.
 *
 * TEXTBUF is past the card's bitmap (words 0-19199 at this resolution),
 * not inside it -- otherwise title characters would bleed into the
 * fractal as stray pixels. */
#define WIDTH      640
#define HEIGHT     480
#define TEXTBUF    046000
#define COLS       80       /* 640 / 8 dot cell */

static void fb_doc(unsigned v) { asm volatile("DOC %0,042\n\t" :: "r"(v)); }
static void fb_doa(unsigned v) { asm volatile("DOA %0,042\n\t" :: "r"(v)); }
static void fb_dob(unsigned v) { asm volatile("DOB %0,042\n\t" :: "r"(v)); }
static void fb_present(void)   { asm volatile("NIOP 042\n\t"); }

struct line {
  int row, col;
  const char *text;
};

/* Kept in sync BY HAND with verify_fractal.py's TITLE, which recomputes
 * this frame independently for the pixel-diff check. */
static const struct line TITLE[] = {
  {2, 3, "NOVA FB - AND FRACTAL SCROLL"},
  {4, 3, "SET (x,y) IF (x+t) AND y"},
  {6, 3, "built via nova-llvm-backend"},
  {7, 3, "not hand-assembled -- real C"},
  {13, 3, "watch it flow ... never halts"},
};
#define NLINES 5

static void draw_title(void) {
  int i, row, col;
  const char *s;
  unsigned addr;

  /* Select the text register port; TEXTPTR/CHARPTR/TCTL load one after
   * another because DOB auto-increments the register selector. */
  fb_doc(CTL_TEXT);
  fb_doa(0);
  fb_dob(TEXTBUF);   /* TEXTPTR */
  fb_dob(0);         /* CHARPTR = 0, the built-in ROM */
  fb_dob(T_ENABLE);  /* TCTL */

  /* Back to plain word mode to write the cells themselves. */
  fb_doc(0);
  for (i = 0; i < NLINES; i++) {
    row = TITLE[i].row;
    col = TITLE[i].col;
    s = TITLE[i].text;
    /* Stop at COLS instead of wrapping a too-long line into the next row. */
    while (*s && col < COLS) {
      addr = TEXTBUF + row * COLS + col;
      fb_doa(addr);
      fb_dob((unsigned)(unsigned char)*s);
      s++;
      col++;
    }
  }
  fb_present();      /* frame 1: the title card */

  /* Char mode off: select register 2 (TCTL) directly and clear it. */
  fb_doc(CTL_TEXT);
  fb_doa(2);
  fb_dob(0);
}

void main(void) {
  int x, y, t;

  draw_title();

  fb_doc(CTL_PIXEL);
  t = 0;
  for (;;) {
    /* Full redraw every frame: a pixel lit last frame that shouldn't be
     * lit now has to be actively CLEARed, which is what makes this scroll
     * instead of just accumulate. */
    for (y = 0; y < HEIGHT; y++) {
      for (x = 0; x < WIDTH; x++) {
        if ((x + t) & y) {
          fb_doa(x);
          fb_dob(y);              /* op = SET (0) */
        } else {
          fb_doa(x);
          fb_dob(OP_CLEAR | y);   /* op = CLEAR (1) */
        }
      }
    }
    fb_present();
    t++;
  }
}
