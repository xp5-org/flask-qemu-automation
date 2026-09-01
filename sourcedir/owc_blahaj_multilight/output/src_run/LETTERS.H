/*
 * LETTERS.H -- blocky extruded 3D letterforms for the word "ALLEGRO".
 *
 * Each glyph is a handful of axis-aligned rectangles ("strokes") in a local
 * 3-wide by 5-tall grid, each extruded into a box. Building letters out of
 * independent boxes rather than one outline per glyph means the non-convex
 * shapes (E, G, R) need no polygon-with-holes triangulation at all -- every
 * piece is just the cube from the sibling demo, parameterised.
 *
 * Strokes are extruded once at startup into the shared vertex/triangle
 * buffers; nothing here is rebuilt per frame.
 */

#ifndef LETTERS_H
#define LETTERS_H

#define GLYPH_A 0
#define GLYPH_L 1
#define GLYPH_E 2
#define GLYPH_G 3
#define GLYPH_R 4
#define GLYPH_O 5
#define NGLYPHS 6

#define MAX_STROKES 6

/* Grid: x 0..3, y 0..5, origin bottom-left. T is the stroke thickness. */
#define T 0.8f

/* {x0, y0, x1, y1} per stroke; unused slots are all-zero and skipped. */
static const float g_glyph_strokes[NGLYPHS][MAX_STROKES][4] = {
    /* A: two legs, a top bar and a crossbar (blocky, straight-sided). */
    {{0.0f, 0.0f, T, 5.0f},
     {3.0f - T, 0.0f, 3.0f, 5.0f},
     {0.0f, 5.0f - T, 3.0f, 5.0f},
     {0.0f, 2.4f, 3.0f, 2.4f + T},
     {0}, {0}},

    /* L: spine + foot. */
    {{0.0f, 0.0f, T, 5.0f},
     {0.0f, 0.0f, 3.0f, T},
     {0}, {0}, {0}, {0}},

    /* E: spine + three bars. */
    {{0.0f, 0.0f, T, 5.0f},
     {0.0f, 5.0f - T, 3.0f, 5.0f},
     {0.0f, 2.4f, 2.6f, 2.4f + T},
     {0.0f, 0.0f, 3.0f, T},
     {0}, {0}},

    /* G: a C-ring plus the inward tab that distinguishes it from a C. */
    {{0.0f, 0.0f, T, 5.0f},
     {0.0f, 5.0f - T, 3.0f, 5.0f},
     {0.0f, 0.0f, 3.0f, T},
     {3.0f - T, 0.0f, 3.0f, 2.2f},
     {1.6f, 2.2f, 3.0f, 2.2f + T},
     {0}},

    /* R: spine, closed upper bowl, and a diagonal-ish kicked-out leg. */
    {{0.0f, 0.0f, T, 5.0f},
     {0.0f, 5.0f - T, 3.0f, 5.0f},
     {3.0f - T, 2.6f, 3.0f, 5.0f},
     {0.0f, 2.6f, 3.0f, 2.6f + T},
     {3.0f - T, 0.0f, 3.0f, 2.6f},
     {0}},

    /* O: square annulus. */
    {{0.0f, 0.0f, T, 5.0f},
     {3.0f - T, 0.0f, 3.0f, 5.0f},
     {0.0f, 5.0f - T, 3.0f, 5.0f},
     {0.0f, 0.0f, 3.0f, T},
     {0}, {0}},
};

/* "ALLEGRO" -- 7 glyphs, L drawn twice. */
#define WORD_LEN 7
static const int g_word[WORD_LEN] = {
    GLYPH_A, GLYPH_L, GLYPH_L, GLYPH_E, GLYPH_G, GLYPH_R, GLYPH_O
};

#undef T

#endif  /* LETTERS_H */
