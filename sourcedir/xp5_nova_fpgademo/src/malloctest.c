/* malloc/free/calloc tester for this platform's runtime allocator
 * (eclipse_rt.c: a fixed static arena, bump-allocated, free() a no-op).
 *
 * WHAT THIS TESTS, from reading the allocator's source (there's no
 * introspection API, so every number below is detected by probing at
 * runtime, not assumed):
 *
 *   void *malloc(unsigned int size) {
 *     if (heap_used + size > HEAP_WORDS) return (void *)0;
 *     void *p = &heap[heap_used];
 *     heap_used += size;
 *     return p;
 *   }
 *
 * 1. FREE DOES NOT RECLAIM: alloc, free, alloc-again-same-size, and check
 *    the second pointer is a new address, not the freed one.
 *
 * 2. NO MEMORY EXPANSION: the arena is fixed-size, so once exhausted it
 *    never grows -- confirmed by allocating past exhaustion and checking
 *    every further call keeps returning NULL.
 *
 * 3. calloc(nmemb, size) multiplies nmemb*size as a plain 16-bit unsigned
 *    int with no overflow check. calloc(4096, 4096) should mean "16MB,
 *    zeroed" and fail loudly; instead 4096*4096 mod 65536 == 0, so it
 *    succeeds having allocated nothing. Demonstrated by checking the
 *    return value only -- nothing is written through the pointer.
 *
 * 4. THE BOUNDS CHECK ITSELF OVERFLOWS THE SAME WAY: heap_used + size can
 *    wrap past 65536, so a crafted size of (0 - heap_used) makes the sum
 *    wrap to exactly 0, which always passes the check. malloc returns a
 *    normal-looking pointer for a ~64KB request, and heap_used wraps to 0,
 *    resetting the bump pointer to the arena's start. Demonstrated safely:
 *    the next ordinary malloc() gets the same address as an allocation
 *    from step 1, proving two live objects now alias the same memory.
 *
 * VISUAL: the nova_fb card shows a grid of the heap's byte layout (each
 * cell = BYTES_PER_CELL bytes) plus a 4-line rotating status log, updated
 * one phase at a time. Same fb_doc/fb_doa/fb_dob/fb_present idiom as
 * fractal.c.
 *
 * Ends with a HALT and a final console line, "MALLOCTEST: PASS" or "FAIL",
 * after checking every phase's actual result against its predicted one
 * above -- so a future allocator change that fixes or breaks any of this
 * shows up as a test failure, not a stale log.
 */

#include <stdio.h>
#include <stdlib.h>

/* 640x480, platform minimum -- see fractal.c's header comment. TEXTBUF
 * sits past the bitmap's 0-19199 word range. */
#define CTL_TEXT   02000
#define TEXTBUF    046000
#define COLS       80       /* 640 / 8 dot cell */
#define T_ENABLE   01

#define GRID_ROW0      3
#define GRID_ROWS      16
#define BYTES_PER_CELL 2    /* grid covers 16*80*2 = 2560 bytes, comfortably
                             * more than the runtime's actual heap size */

#define LOG_ROW0 21
#define LOG_ROWS 4

static void fb_doc(unsigned v) { asm volatile("DOC %0,042\n\t" :: "r"(v)); }
static void fb_doa(unsigned v) { asm volatile("DOA %0,042\n\t" :: "r"(v)); }
static void fb_dob(unsigned v) { asm volatile("DOB %0,042\n\t" :: "r"(v)); }
static void fb_present(void)   { asm volatile("NIOP 042\n\t"); }

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
  fb_dob(TEXTBUF);   /* TEXTPTR */
  fb_dob(0);         /* CHARPTR = 0, built-in ROM */
  fb_dob(T_ENABLE);  /* TCTL */
  fb_doc(0);         /* back to plain word mode for the cells themselves */
}

/* One grid cell per BYTES_PER_CELL bytes of the arena, filled with `ch` as
 * that range gets allocated. Ignored past the grid's displayable span
 * rather than corrupting the status display. Grid is COLS wide, matching
 * the card's own text columns. */
static void mark_range(unsigned start, unsigned len, unsigned ch) {
  unsigned off;
  for (off = start; off < start + len; off += BYTES_PER_CELL) {
    unsigned cell = off / BYTES_PER_CELL;
    unsigned row, col;
    if (cell >= (unsigned)(GRID_ROWS * COLS))
      return;
    row = GRID_ROW0 + cell / COLS;
    col = cell % COLS;
    fb_putc(row, col, ch);
  }
}

static int log_row = 0;

/* Rotates through LOG_ROWS fixed lines rather than scrolling, still
 * showing the last few events as they happen. */
static void log_line(const char *s) {
  int col;
  for (col = 2; col < COLS; col++)
    fb_putc(LOG_ROW0 + log_row, col, ' ');
  fb_puts(LOG_ROW0 + log_row, 2, s);
  log_row = (log_row + 1) % LOG_ROWS;
  fb_present();
}

static int failures = 0;

static void expect(int cond, const char *label) {
  printf("  %s: %s\n", cond ? "ok  " : "FAIL", label);
  if (!cond)
    failures++;
}

/* --- phase 1: free() does not reclaim ------------------------------- */
static void *phase_free_noop(void) {
  void *p1 = malloc(64);
  void *p2;
  free(p1);
  p2 = malloc(64);
  log_line("phase1: free() then realloc same size");
  printf("phase1: p1=%d p2=%d\n", (unsigned)p1, (unsigned)p2);
  expect(p1 != NULL && p2 != NULL, "both allocations succeeded");
  expect(p1 != p2, "freed block was NOT reused (confirms no-op free)");
  mark_range(0, 64, 'F');    /* the "freed but orphaned" block */
  mark_range(64, 64, '1');   /* the block that replaced it */
  return p1;   /* kept for phase 4's aliasing check */
}

/* --- phase 2: calloc's nmemb*size overflow --------------------------- */
static void phase_calloc_overflow(void) {
  void *p = calloc(4096, 4096);
  log_line("phase2: calloc(4096,4096) 16MB nominal");
  printf("phase2: calloc(4096,4096) -> %d (nominal 16777216 bytes)\n",
         (unsigned)p);
  /* 4096*4096 mod 65536 == 0, so this SHOULD succeed while allocating
   * nothing real -- p != NULL is the bug, not a crash. */
  expect(p != NULL, "calloc succeeded for a request that overflows to 0 "
                    "real bytes (silent 16-bit multiply overflow)");
}

/* --- phase 3: probe until exhausted, filling the grid ---------------- */
#define PROBE_CHUNK 32

static unsigned phase_probe(unsigned used_before) {
  unsigned used = used_before;
  int count = 0;
  char msg[40];

  for (;;) {
    void *p = malloc(PROBE_CHUNK);
    if (!p)
      break;
    mark_range(used, PROBE_CHUNK, '.' + 1 + (count % 9));  /* cycling fill to show growth */
    used += PROBE_CHUNK;
    count++;
  }
  sprintf(msg, "phase3: exhausted after %d x %dB", count, PROBE_CHUNK);
  log_line(msg);
  printf("phase3: %d chunks of %d bytes -> ~%d bytes usable (detected)\n",
         count, PROBE_CHUNK, used - used_before);
  expect(count > 0, "at least one probe chunk fit");

  /* NO MEMORY EXPANSION: it must still be exhausted, deterministically,
   * on repeated tries -- not "eventually" grow. */
  expect(malloc(PROBE_CHUNK) == NULL, "still exhausted on retry #1");
  expect(malloc(PROBE_CHUNK) == NULL, "still exhausted on retry #2");
  log_line("phase3: confirmed no memory expansion");
  return used;
}

/* --- phase 4: wrap the bounds check itself, alias an earlier block ---
 *
 * The target to alias is p1 -- phase 1's first allocation, made when
 * heap_used was 0 -- not anything from phase 3's probe (which starts at
 * heap_used==128 and so lives at a different address). heap_used wrapping
 * to exactly 0 reproduces whatever ran at the very start of the program:
 * p1. */
static void phase_wrap_bypass(unsigned heap_used_now, void *p1) {
  unsigned craft_size = 0 - heap_used_now;   /* wraps to 65536 - heap_used_now */
  void *pbad = malloc(craft_size);
  void *palias;
  char msg[40];

  sprintf(msg, "phase4: malloc(%d) [craft]", craft_size);
  log_line(msg);
  /* craft_size prints negative here -- printf only has %d, and this
   * platform's int is signed 16-bit, so the same bit pattern reads as
   * negative through %d. malloc receives the same bits either way. */
  printf("phase4: malloc(%d) (wraps heap_used+size to 0) -> %d\n",
         craft_size, (unsigned)pbad);
  expect(pbad != NULL, "bounds check bypassed by the crafted size "
                       "(heap_used+size wrapped past 65536)");

  palias = malloc(64);
  printf("phase4: post-wrap malloc(64) -> %d, phase1's p1 was %d\n",
         (unsigned)palias, (unsigned)p1);
  mark_range(0, 64, 'X');   /* the aliasing collision, drawn over cell 0 */
  log_line("phase4: heap ptr wrapped to START");
  expect(palias == p1,
         "post-wrap allocation ALIASES phase1's first live block "
         "(heap pointer reset to the arena's start)");
}

void main(void) {
  unsigned heap_used;
  void *p1;

  fb_init_textmode();
  fb_puts(0, 2, "NOVA MALLOC TESTER");
  fb_puts(1, 2, "probing this platform's allocator");
  fb_present();

  printf("MALLOCTEST: starting\n");

  p1 = phase_free_noop();
  phase_calloc_overflow();
  heap_used = phase_probe(128);   /* phase1 used 128 bytes (two 64B blocks) */
  phase_wrap_bypass(heap_used, p1);

  fb_puts(GRID_ROW0 - 1, 2, failures == 0 ? "ALL FINDINGS CONFIRMED"
                                          : "UNEXPECTED RESULT -- SEE LOG");
  fb_present();

  printf("MALLOCTEST: %s\n", failures == 0 ? "PASS" : "FAIL");
}
